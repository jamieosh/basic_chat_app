import asyncio
import html
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Literal, cast

import openai
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.base_agent import ConversationTurn
from agents.openai_agent import EmptyModelResponseError, OpenAIAgent
from persistence import ChatMessage, ChatRepository, ChatSession, StorageInitializationError, bootstrap_database
from utils.diagnostics import (
    DiagnosticCheck,
    StartupDiagnosticsError,
    build_readiness_payload,
    collect_startup_checks,
    raise_for_failed_startup_checks,
)
from utils.client_identity import resolve_client_id, set_client_id_cookie
from utils.html_formatter import format_response_as_html
from utils.logging_config import get_logger, init_logging
from utils.settings import RuntimeSettings, get_settings, load_project_env

APP_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

logger = get_logger("api")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _static_asset_version() -> str:
    asset_paths = [
        STATIC_DIR / "css" / "chat.css",
        STATIC_DIR / "js" / "chat.js",
    ]
    latest_mtime = max(int(path.stat().st_mtime) for path in asset_paths if path.exists())
    return str(latest_mtime)


@dataclass(frozen=True)
class ChatPageState:
    visible_chats: list[ChatSession]
    selected_chat: ChatSession | None
    transcript_messages: list[ChatMessage]
    view_state: str

    @property
    def active_chat_session_id(self) -> int | None:
        if self.selected_chat is None:
            return None
        return self.selected_chat.id


def _get_agent(request: Request) -> OpenAIAgent:
    """Read the request-scoped agent initialized at startup."""
    try:
        return request.app.state.agent
    except AttributeError as exc:
        logger.error("OpenAI agent is not initialized")
        raise HTTPException(status_code=503, detail="AI agent unavailable") from exc


def _render_bot_message(body_html: str, timestamp: str, title: str | None = None, *, is_error: bool = False) -> str:
    message_classes = "message bot-message fade-in"
    if is_error:
        message_classes += " error-message"

    title_html = f'<div class="message-title">{html.escape(title)}</div>' if title else ""
    return dedent(
        f"""
        <div class="{message_classes}">
            <div class="message-content">
                {title_html}
                <div class="message-body">{body_html}</div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
        </div>
        """
    ).strip()


def _render_error_message(title: str, body: str, timestamp: str, status_code: int) -> HTMLResponse:
    return _render_error_response(title, body, timestamp, status_code)


def _render_chat_session_id_input(chat_session_id: int) -> str:
    return (
        f'<input type="hidden" id="chat-session-id" name="chat_session_id" '
        f'value="{chat_session_id}" hx-swap-oob="true">'
    )


def _render_chat_session_id_input_value(chat_session_id: int | None) -> str:
    value = "" if chat_session_id is None else str(chat_session_id)
    return (
        '<input type="hidden" id="chat-session-id" name="chat_session_id" '
        f'value="{value}" hx-swap-oob="true">'
    )


def _render_htmx_response(content: str, status_code: int = 200, *, chat_session_id: int | None = None) -> HTMLResponse:
    response_content = content
    if chat_session_id is not None:
        response_content = f"{response_content}\n{_render_chat_session_id_input(chat_session_id)}"

    return HTMLResponse(
        content=response_content,
        status_code=status_code,
    )


def _render_error_response(
    title: str,
    body: str,
    timestamp: str,
    status_code: int,
    *,
    chat_session_id: int | None = None,
) -> HTMLResponse:
    return _render_htmx_response(
        _render_bot_message(html.escape(body), timestamp, title, is_error=True),
        status_code=status_code,
        chat_session_id=chat_session_id,
    )


def _render_chat_not_found_message(timestamp: str) -> HTMLResponse:
    return _render_error_response(
        "Chat Not Found",
        "The requested chat could not be found.",
        timestamp,
        404,
    )


def _chat_url_path(chat_session_id: int) -> str:
    return f"/chats/{chat_session_id}"


def _validate_message_input(message: str | None) -> str:
    if message is None or not message.strip():
        raise ValueError("Message cannot be empty")
    return message


def _validate_chat_session_input(chat_session_id: str | None) -> int | None:
    if chat_session_id is None or not chat_session_id.strip():
        return None

    try:
        parsed_chat_session_id = int(chat_session_id)
    except ValueError as exc:
        raise ValueError("Chat session ID is invalid") from exc

    if parsed_chat_session_id <= 0:
        raise ValueError("Chat session ID is invalid")

    return parsed_chat_session_id


def _set_startup_state(app: FastAPI, *, startup_complete: bool) -> None:
    app.state.startup_complete = startup_complete


def _is_chat_service_available(app: FastAPI) -> bool:
    return (
        bool(getattr(app.state, "startup_complete", False))
        and hasattr(app.state, "agent")
        and hasattr(app.state, "chat_repository")
    )


def _chat_service_unavailable_detail(app: FastAPI) -> str:
    if not bool(getattr(app.state, "startup_complete", False)):
        return "The chat service is still starting up. Please try again shortly."
    return "The chat service is temporarily unavailable. Please try again shortly."


def _readiness_status(app: FastAPI) -> tuple[int, dict[str, object]]:
    return build_readiness_payload(
        startup_complete=bool(getattr(app.state, "startup_complete", False)),
        agent_initialized=hasattr(app.state, "agent"),
        storage_initialized=hasattr(app.state, "chat_repository"),
    )


def _log_known_chat_error(event: str, exc: Exception) -> None:
    logger.warning("%s detail=%s", event, str(exc))


def _finalize_response_with_client_cookie(response: Response, *, client_id: str, should_set_cookie: bool) -> Response:
    if should_set_cookie:
        set_client_id_cookie(response, client_id)
    return response


def _conversation_history_from_messages(messages: list[ChatMessage]) -> list[ConversationTurn]:
    history: list[ConversationTurn] = []
    for message in messages:
        if message.role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported persisted role for conversation history: {message.role}")
        history.append(
            ConversationTurn(
                role=cast(Literal["user", "assistant"], message.role),
                content=message.content,
            )
        )
    return history


def _format_text_as_html(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _format_chat_timestamp(timestamp: str) -> str:
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        return timestamp

    if parsed_timestamp.tzinfo is not None:
        parsed_timestamp = parsed_timestamp.astimezone()

    return parsed_timestamp.strftime("%b %d, %I:%M %p")


def _format_chat_list_timestamp(timestamp: str) -> str:
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        return timestamp

    if parsed_timestamp.tzinfo is not None:
        parsed_timestamp = parsed_timestamp.astimezone()

    return parsed_timestamp.strftime("%b %d · %I:%M %p")


def _load_chat_page_state(
    repository: ChatRepository,
    *,
    client_id: str,
    chat_session_id: int | None,
) -> ChatPageState:
    visible_chats = repository.list_visible_chats(client_id=client_id)
    if chat_session_id is None:
        return ChatPageState(
            visible_chats=visible_chats,
            selected_chat=None,
            transcript_messages=[],
            view_state="start",
        )

    selected_chat = repository.get_chat(chat_session_id=chat_session_id, client_id=client_id)
    if selected_chat is None:
        return ChatPageState(
            visible_chats=visible_chats,
            selected_chat=None,
            transcript_messages=[],
            view_state="not_found",
        )

    return ChatPageState(
        visible_chats=visible_chats,
        selected_chat=selected_chat,
        transcript_messages=repository.list_messages_for_chat(
            chat_session_id=selected_chat.id,
            client_id=client_id,
        ),
        view_state="active",
    )


def _base_template_context(
    request: Request,
    *,
    display_name: str,
    model_display_name: str,
    chat_available: bool,
    service_status_message: str,
) -> dict[str, object]:
    return {
        "request": request,
        "model_display_name": model_display_name,
        "display_name": display_name,
        "chat_available": chat_available,
        "service_status_title": "Chat unavailable",
        "service_status_message": service_status_message,
        "format_chat_timestamp": _format_chat_timestamp,
        "format_chat_list_timestamp": _format_chat_list_timestamp,
        "format_text_as_html": _format_text_as_html,
        "format_response_as_html": format_response_as_html,
        "asset_version": _static_asset_version(),
    }


def _chat_page_context(
    request: Request,
    *,
    display_name: str,
    model_display_name: str,
    chat_available: bool,
    service_status_message: str,
    page_state: ChatPageState,
) -> dict[str, object]:
    context = _base_template_context(
        request,
        display_name=display_name,
        model_display_name=model_display_name,
        chat_available=chat_available,
        service_status_message=service_status_message,
    )
    context.update(
        {
            "visible_chats": page_state.visible_chats,
            "selected_chat": page_state.selected_chat,
            "selected_chat_id": page_state.active_chat_session_id,
            "chat_messages": page_state.transcript_messages,
            "view_state": page_state.view_state,
            "active_chat_session_id": page_state.active_chat_session_id,
            "active_chat_url": (
                _chat_url_path(page_state.active_chat_session_id)
                if page_state.active_chat_session_id is not None
                else "/"
            ),
            "oob_swap": False,
        }
    )
    return context


def _render_template_fragment(template_name: str, context: dict[str, object]) -> str:
    return templates.get_template(template_name).render(context)


def _render_oob_fragment(template_name: str, context: dict[str, object]) -> str:
    oob_context = dict(context)
    oob_context["oob_swap"] = True
    return _render_template_fragment(template_name, oob_context)


def _render_transcript_partial(context: dict[str, object]) -> str:
    return _render_template_fragment("components/chat_box_content.html", context)


def _render_chat_view_updates(
    context: dict[str, object],
    *,
    chat_session_id: int | None,
) -> str:
    return "\n".join(
        [
            _render_oob_fragment("components/chat_view_header.html", context),
            _render_oob_fragment("components/chat_list.html", context),
            _render_chat_session_id_input_value(chat_session_id),
        ]
    )


def _response_with_optional_push_url(
    response: HTMLResponse,
    *,
    chat_session_id: int | None,
) -> HTMLResponse:
    if chat_session_id is not None:
        response.headers["HX-Push-Url"] = _chat_url_path(chat_session_id)
    return response


def _render_chat_error_htmx_response(
    request: Request,
    *,
    agent: OpenAIAgent,
    repository: ChatRepository,
    client_id: str,
    active_chat_session_id: int | None,
    title: str,
    body: str,
    timestamp: str,
    status_code: int,
) -> HTMLResponse:
    if active_chat_session_id is None:
        return _render_error_response(
            title,
            body,
            timestamp,
            status_code,
        )

    page_context = _chat_page_context(
        request,
        display_name=agent.display_name,
        model_display_name=agent.model_display_name,
        chat_available=True,
        service_status_message=_chat_service_unavailable_detail(request.app),
        page_state=_load_chat_page_state(
            repository,
            client_id=client_id,
            chat_session_id=active_chat_session_id,
        ),
    )
    return _response_with_optional_push_url(
        _render_htmx_response(
            "\n".join(
                [
                    _render_bot_message(html.escape(body), timestamp, title, is_error=True),
                    _render_chat_view_updates(
                        page_context,
                        chat_session_id=active_chat_session_id,
                    ),
                ]
            ),
            status_code=status_code,
        ),
        chat_session_id=active_chat_session_id,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize dependencies at startup instead of import time."""
    init_logging()
    _set_startup_state(app, startup_complete=False)
    logger.info("startup.begin")

    settings: RuntimeSettings = app.state.settings
    startup_checks = collect_startup_checks(settings)
    try:
        raise_for_failed_startup_checks(startup_checks)
        bootstrap_database(settings.chat_database_path)
        app.state.chat_repository = ChatRepository(settings.chat_database_path)
        app.state.agent = OpenAIAgent(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model,
            prompt_name=settings.openai_prompt_name,
            temperature=settings.openai_temperature,
            timeout=settings.openai_timeout_seconds,
        )
    except StartupDiagnosticsError as exc:
        for failure in exc.failures:
            logger.critical("startup.failed check=%s detail=%s", failure.name, failure.detail)
        raise
    except StorageInitializationError as exc:
        logger.critical("startup.failed check=storage_initialization detail=%s", str(exc), exc_info=True)
        raise StartupDiagnosticsError(
            [
                DiagnosticCheck(
                    name="storage_initialization",
                    ok=False,
                    detail=(
                        f"Failed to initialize chat storage at {settings.chat_database_path}. {str(exc)}"
                    ),
                )
            ]
        ) from exc
    except Exception as exc:
        logger.critical("startup.failed check=agent_initialization detail=%s", str(exc), exc_info=True)
        raise StartupDiagnosticsError(
            [
                DiagnosticCheck(
                    name="agent_initialization",
                    ok=False,
                    detail=f"Failed to initialize the OpenAI agent. {str(exc)}",
                )
            ]
        ) from exc

    _set_startup_state(app, startup_complete=True)
    logger.info(
        "startup.ready model=%s agent=%s",
        app.state.agent.model_display_name,
        app.state.agent.display_name,
    )
    try:
        yield
    finally:
        _set_startup_state(app, startup_complete=False)
        if hasattr(app.state, "agent"):
            del app.state.agent
        if hasattr(app.state, "chat_repository"):
            del app.state.chat_repository
        logger.info("startup.shutdown")


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    load_project_env()
    settings = settings or get_settings()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), check_dir=False), name="static")

    def _chat_shell_context(
        request: Request,
        *,
        client_id: str,
        chat_session_id: int | None,
    ) -> tuple[dict[str, object], int]:
        chat_available = _is_chat_service_available(request.app)
        service_status_message = _chat_service_unavailable_detail(request.app)
        display_name = "AI Chat"
        model_display_name = "Unavailable"
        page_state = ChatPageState(
            visible_chats=[],
            selected_chat=None,
            transcript_messages=[],
            view_state="start",
        )
        status_code = 200

        if chat_available:
            agent = _get_agent(request)
            display_name = agent.display_name
            model_display_name = agent.model_display_name
            repository = request.app.state.chat_repository
            page_state = _load_chat_page_state(
                repository,
                client_id=client_id,
                chat_session_id=chat_session_id,
            )
            if page_state.view_state == "not_found":
                status_code = 404
        else:
            logger.warning("chat.shell_unavailable detail=%s", service_status_message)
            status_code = 503

        return (
            _chat_page_context(
                request,
                display_name=display_name,
                model_display_name=model_display_name,
                chat_available=chat_available,
                service_status_message=service_status_message,
                page_state=page_state,
            ),
            status_code,
        )

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Render the Phase 2 start screen or redirect to the latest visible chat."""
        logger.debug("home.render")
        client_id, should_set_client_cookie = resolve_client_id(request)
        if _is_chat_service_available(request.app):
            repository = request.app.state.chat_repository
            visible_chats = repository.list_visible_chats(client_id=client_id)
            if visible_chats:
                redirect_response = RedirectResponse(
                    url=request.url_for("chat_page", chat_id=visible_chats[0].id),
                    status_code=307,
                )
                return _finalize_response_with_client_cookie(
                    redirect_response,
                    client_id=client_id,
                    should_set_cookie=should_set_client_cookie,
                )

        context, status_code = _chat_shell_context(
            request,
            client_id=client_id,
            chat_session_id=None,
        )
        response = templates.TemplateResponse(
            request,
            "index.html",
            context,
            status_code=status_code,
        )
        return _finalize_response_with_client_cookie(
            response,
            client_id=client_id,
            should_set_cookie=should_set_client_cookie,
        )

    @app.get("/chats/{chat_id}", response_class=HTMLResponse)
    async def chat_page(request: Request, chat_id: int):
        client_id, should_set_client_cookie = resolve_client_id(request)
        context, status_code = _chat_shell_context(
            request,
            client_id=client_id,
            chat_session_id=chat_id,
        )
        response = templates.TemplateResponse(
            request,
            "index.html",
            context,
            status_code=status_code,
        )
        return _finalize_response_with_client_cookie(
            response,
            client_id=client_id,
            should_set_cookie=should_set_client_cookie,
        )

    @app.get("/chat-list", response_class=HTMLResponse)
    async def chat_list_partial(request: Request):
        client_id, should_set_client_cookie = resolve_client_id(request)
        context, status_code = _chat_shell_context(
            request,
            client_id=client_id,
            chat_session_id=None,
        )
        response = HTMLResponse(
            content=_render_template_fragment("components/chat_list.html", context),
            status_code=status_code,
        )
        return _finalize_response_with_client_cookie(
            response,
            client_id=client_id,
            should_set_cookie=should_set_client_cookie,
        )

    @app.get("/chats/{chat_id}/transcript", response_class=HTMLResponse)
    async def chat_transcript_partial(request: Request, chat_id: int):
        client_id, should_set_client_cookie = resolve_client_id(request)
        context, status_code = _chat_shell_context(
            request,
            client_id=client_id,
            chat_session_id=chat_id,
        )
        response = HTMLResponse(
            content="\n".join(
                [
                    _render_transcript_partial(context),
                    _render_chat_view_updates(
                        context,
                        chat_session_id=cast(int | None, context["active_chat_session_id"]),
                    ),
                ]
            ),
            status_code=status_code,
        )
        if status_code == 200:
            response.headers["HX-Push-Url"] = _chat_url_path(chat_id)
        return _finalize_response_with_client_cookie(
            response,
            client_id=client_id,
            should_set_cookie=should_set_client_cookie,
        )

    @app.post("/send-message-htmx", response_class=HTMLResponse)
    async def chat_htmx(
        request: Request,
        message: str | None = Form(None),
        chat_session_id: str | None = Form(None),
    ):
        """Process a chat message and return the response as HTML."""
        timestamp = datetime.now().strftime("%I:%M %p")
        client_id, should_set_client_cookie = resolve_client_id(request)

        if not _is_chat_service_available(request.app):
            service_status_message = _chat_service_unavailable_detail(request.app)
            logger.warning("chat.service_unavailable detail=%s", service_status_message)
            return _finalize_response_with_client_cookie(
                _render_error_response(
                    "Service Unavailable",
                    service_status_message,
                    timestamp,
                    503,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        agent = _get_agent(request)
        repository = request.app.state.chat_repository
        active_chat_session_id: int | None = None

        try:
            message = _validate_message_input(message)
            requested_chat_session_id = _validate_chat_session_input(chat_session_id)
            logger.info("chat.request_received chars=%s", len(message))

            if requested_chat_session_id is None:
                chat = repository.create_chat(
                    client_id=client_id,
                    title=repository.next_default_chat_title(client_id=client_id),
                )
                prior_messages: list[ChatMessage] = []
            else:
                chat = repository.get_chat(
                    chat_session_id=requested_chat_session_id,
                    client_id=client_id,
                )
                if chat is None:
                    return _finalize_response_with_client_cookie(
                        _render_chat_not_found_message(timestamp),
                        client_id=client_id,
                        should_set_cookie=should_set_client_cookie,
                    )

                prior_messages = repository.list_messages_for_chat(
                    chat_session_id=chat.id,
                    client_id=client_id,
                )

            active_chat_session_id = chat.id
            repository.create_message(
                chat_session_id=chat.id,
                client_id=client_id,
                role="user",
                content=message,
            )

            response = await asyncio.to_thread(
                agent.process_message,
                message,
                _conversation_history_from_messages(prior_messages),
            )
            repository.create_message(
                chat_session_id=chat.id,
                client_id=client_id,
                role="assistant",
                content=response,
            )
            formatted_content = format_response_as_html(response)
            page_context = _chat_page_context(
                request,
                display_name=agent.display_name,
                model_display_name=agent.model_display_name,
                chat_available=True,
                service_status_message=_chat_service_unavailable_detail(request.app),
                page_state=_load_chat_page_state(
                    repository,
                    client_id=client_id,
                    chat_session_id=active_chat_session_id,
                ),
            )
            html_response = _response_with_optional_push_url(
                _render_htmx_response(
                    "\n".join(
                        [
                            _render_bot_message(formatted_content, timestamp),
                            _render_chat_view_updates(
                                page_context,
                                chat_session_id=active_chat_session_id,
                            ),
                        ]
                    ),
                ),
                chat_session_id=active_chat_session_id,
            )

            logger.info(
                "chat.request_succeeded request_chars=%s response_chars=%s chat_session_id=%s",
                len(message),
                len(response),
                active_chat_session_id,
            )
            return _finalize_response_with_client_cookie(
                html_response,
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except ValueError as e:
            _log_known_chat_error("chat.validation_failed", e)
            return _finalize_response_with_client_cookie(
                _render_error_response(
                    "Invalid Input",
                    str(e),
                    timestamp,
                    400,
                    chat_session_id=active_chat_session_id,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.RateLimitError as e:
            _log_known_chat_error("chat.rate_limited", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="Rate Limit Exceeded",
                    body="The AI service is currently busy. Please try again in a few moments.",
                    timestamp=timestamp,
                    status_code=429,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.AuthenticationError as e:
            _log_known_chat_error("chat.authentication_failed", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="Authentication Error",
                    body="There's an issue with the AI service authentication. Please contact support.",
                    timestamp=timestamp,
                    status_code=401,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APITimeoutError as e:
            _log_known_chat_error("chat.timeout", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="Request Timeout",
                    body="The AI service took too long to respond. Please try again.",
                    timestamp=timestamp,
                    status_code=504,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APIConnectionError as e:
            _log_known_chat_error("chat.connection_error", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="Connection Error",
                    body="Could not connect to the AI service. Please check your internet connection and try again.",
                    timestamp=timestamp,
                    status_code=503,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.BadRequestError as e:
            _log_known_chat_error("chat.bad_request", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="AI Service Error",
                    body="The AI service rejected the request. Please try again later.",
                    timestamp=timestamp,
                    status_code=502,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APIError as e:
            _log_known_chat_error("chat.api_error", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="AI Service Error",
                    body="The AI service encountered an error. Please try again later.",
                    timestamp=timestamp,
                    status_code=500,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except EmptyModelResponseError as e:
            _log_known_chat_error("chat.empty_model_response", e)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="AI Service Error",
                    body="The AI service returned an empty response. Please try again later.",
                    timestamp=timestamp,
                    status_code=502,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except Exception as e:
            logger.error("chat.unexpected_error detail=%s", str(e), exc_info=True)
            return _finalize_response_with_client_cookie(
                _render_chat_error_htmx_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    active_chat_session_id=active_chat_session_id,
                    title="Unexpected Error",
                    body="Sorry, something went wrong. Please try again.",
                    timestamp=timestamp,
                    status_code=500,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/health/ready")
    async def readiness_check():
        """Readiness endpoint for startup/runtime diagnostics."""
        status_code, payload = _readiness_status(app)
        return JSONResponse(status_code=status_code, content=payload)

    return app


app = create_app()
