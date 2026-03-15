import asyncio
import html
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Literal, cast
from uuid import uuid4

import openai
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.base_agent import ConversationTurn
from agents.openai_agent import EmptyModelResponseError, OpenAIAgent
from persistence import (
    ChatMessage,
    ChatRepository,
    ChatSession,
    ChatTurnRequestState,
    StorageInitializationError,
    bootstrap_database,
)
from services import ChatTurnService, failure_presentation
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


def _get_chat_turn_service(request: Request) -> ChatTurnService:
    try:
        return request.app.state.chat_turn_service
    except AttributeError as exc:
        logger.error("Chat turn service is not initialized")
        raise HTTPException(status_code=503, detail="Chat turn service unavailable") from exc


def _render_bot_message(
    body_html: str, timestamp: str, title: str | None = None, *, is_error: bool = False
) -> str:
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


def _render_htmx_response(
    content: str, status_code: int = 200, *, chat_session_id: int | None = None
) -> HTMLResponse:
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


def _chat_start_url_path() -> str:
    return "/chat-start"


def _new_request_id() -> str:
    return str(uuid4())


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


def _validate_request_id_input(request_id: str | None) -> str:
    if request_id is None or not request_id.strip():
        raise ValueError("Request ID is required")
    return request_id.strip()


def _set_startup_state(app: FastAPI, *, startup_complete: bool) -> None:
    app.state.startup_complete = startup_complete


def _is_chat_service_available(app: FastAPI) -> bool:
    return (
        bool(getattr(app.state, "startup_complete", False))
        and hasattr(app.state, "agent")
        and hasattr(app.state, "chat_repository")
        and hasattr(app.state, "chat_turn_service")
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


def _finalize_response_with_client_cookie(
    response: Response, *, client_id: str, should_set_cookie: bool
) -> Response:
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

    now = datetime.now(parsed_timestamp.tzinfo)
    if parsed_timestamp.date() == now.date():
        return parsed_timestamp.strftime("%I:%M %p")

    return parsed_timestamp.strftime("%b %d")


def _is_chat_session_active(chat_session: ChatSession | None) -> bool:
    return chat_session is not None and chat_session.archived_at is None and chat_session.deleted_at is None


def _first_visible_chat_session_id(repository: ChatRepository, *, client_id: str) -> int | None:
    visible_chats = repository.list_visible_chats(client_id=client_id)
    if not visible_chats:
        return None
    return visible_chats[0].id


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
        "chat_request_id": _new_request_id(),
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
    response.headers["HX-Push-Url"] = (
        _chat_url_path(chat_session_id) if chat_session_id is not None else _chat_start_url_path()
    )
    return response


def _render_chat_page_partial_response(
    context: dict[str, object],
    *,
    status_code: int = 200,
    push_url: bool = False,
    chat_session_id: int | None = None,
) -> HTMLResponse:
    response = HTMLResponse(
        content="\n".join(
            [
                _render_transcript_partial(context),
                _render_chat_view_updates(
                    context,
                    chat_session_id=chat_session_id,
                ),
            ]
        ),
        status_code=status_code,
    )
    if push_url:
        response = _response_with_optional_push_url(response, chat_session_id=chat_session_id)
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


def _render_turn_request_state_response(
    request: Request,
    *,
    agent: OpenAIAgent,
    repository: ChatRepository,
    client_id: str,
    turn_request_state: ChatTurnRequestState,
    timestamp: str,
) -> HTMLResponse:
    active_chat_session_id = turn_request_state.turn_request.chat_session_id
    if turn_request_state.turn_request.status == "completed" and _is_chat_session_active(
        turn_request_state.chat_session
    ):
        assistant_message = turn_request_state.assistant_message
        if assistant_message is None:  # pragma: no cover - defensive against required persistence
            raise RuntimeError("Completed turn request is missing its assistant message.")

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
                        _render_bot_message(
                            format_response_as_html(assistant_message.content),
                            timestamp,
                        ),
                        _render_chat_view_updates(
                            page_context,
                            chat_session_id=active_chat_session_id,
                        ),
                    ]
                ),
            ),
            chat_session_id=active_chat_session_id,
        )

    failure_code = turn_request_state.turn_request.failure_code or "unexpected_error"
    presentation = failure_presentation(failure_code)
    response_chat_session_id: int | None = active_chat_session_id
    if turn_request_state.turn_request.status == "conflicted" or not _is_chat_session_active(
        turn_request_state.chat_session
    ):
        response_chat_session_id = _first_visible_chat_session_id(repository, client_id=client_id)
        if response_chat_session_id is None:
            return _response_with_optional_push_url(
                _render_error_response(
                    presentation.title,
                    presentation.body,
                    timestamp,
                    presentation.status_code,
                ),
                chat_session_id=None,
            )

    return _render_chat_error_htmx_response(
        request,
        agent=agent,
        repository=repository,
        client_id=client_id,
        active_chat_session_id=response_chat_session_id,
        title=presentation.title,
        body=presentation.body,
        timestamp=timestamp,
        status_code=presentation.status_code,
    )


async def _await_turn_request_resolution(
    chat_turn_service: ChatTurnService,
    *,
    client_id: str,
    request_id: str,
    timeout_seconds: float = 5.0,
) -> ChatTurnRequestState | None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    state = await asyncio.to_thread(
        chat_turn_service.get_turn_state,
        client_id=client_id,
        request_id=request_id,
    )
    while state is not None and state.turn_request.status == "processing":
        if asyncio.get_running_loop().time() >= deadline:
            return state
        await asyncio.sleep(0.05)
        state = await asyncio.to_thread(
            chat_turn_service.get_turn_state,
            client_id=client_id,
            request_id=request_id,
        )
    return state


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
        app.state.chat_turn_service = ChatTurnService(app.state.chat_repository)
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
        logger.critical(
            "startup.failed check=storage_initialization detail=%s", str(exc), exc_info=True
        )
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
        logger.critical(
            "startup.failed check=agent_initialization detail=%s", str(exc), exc_info=True
        )
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
        if hasattr(app.state, "chat_turn_service"):
            del app.state.chat_turn_service
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

    @app.get("/chat-start", response_class=HTMLResponse)
    async def chat_start_page(request: Request):
        client_id, should_set_client_cookie = resolve_client_id(request)
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

    @app.get("/chat-start/transcript", response_class=HTMLResponse)
    async def chat_start_transcript_partial(request: Request):
        client_id, should_set_client_cookie = resolve_client_id(request)
        context, status_code = _chat_shell_context(
            request,
            client_id=client_id,
            chat_session_id=None,
        )
        response = _render_chat_page_partial_response(
            context,
            status_code=status_code,
            push_url=True,
            chat_session_id=None,
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
        response = _render_chat_page_partial_response(
            context,
            status_code=status_code,
            push_url=status_code == 200,
            chat_session_id=cast(int | None, context["active_chat_session_id"]),
        )
        return _finalize_response_with_client_cookie(
            response, client_id=client_id, should_set_cookie=should_set_client_cookie
        )

    @app.post("/chats/{chat_id}/delete", response_class=HTMLResponse)
    async def delete_chat(request: Request, chat_id: int):
        client_id, should_set_client_cookie = resolve_client_id(request)

        if not _is_chat_service_available(request.app):
            service_status_message = _chat_service_unavailable_detail(request.app)
            logger.warning(
                "chat.delete_unavailable chat_session_id=%s client_id=%s detail=%s",
                chat_id,
                client_id,
                service_status_message,
            )
            return _finalize_response_with_client_cookie(
                _render_error_response(
                    "Service Unavailable",
                    service_status_message,
                    datetime.now().strftime("%I:%M %p"),
                    503,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        repository = request.app.state.chat_repository
        deleted = repository.soft_delete_chat(chat_session_id=chat_id, client_id=client_id)
        if not deleted:
            context, status_code = _chat_shell_context(
                request,
                client_id=client_id,
                chat_session_id=chat_id,
            )
            response = _render_chat_page_partial_response(
                context,
                status_code=status_code,
                push_url=False,
                chat_session_id=cast(int | None, context["active_chat_session_id"]),
            )
            return _finalize_response_with_client_cookie(
                response,
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        next_chat_session_id = None
        visible_chats = repository.list_visible_chats(client_id=client_id)
        if visible_chats:
            next_chat_session_id = visible_chats[0].id

        agent = _get_agent(request)
        page_context = _chat_page_context(
            request,
            display_name=agent.display_name,
            model_display_name=agent.model_display_name,
            chat_available=True,
            service_status_message=_chat_service_unavailable_detail(request.app),
            page_state=_load_chat_page_state(
                repository,
                client_id=client_id,
                chat_session_id=next_chat_session_id,
            ),
        )
        response = _render_chat_page_partial_response(
            page_context,
            push_url=True,
            chat_session_id=next_chat_session_id,
        )
        logger.info(
            "chat.deleted chat_session_id=%s client_id=%s next_chat_session_id=%s",
            chat_id,
            client_id,
            next_chat_session_id,
        )
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
        request_id: str | None = Form(None),
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
        chat_turn_service = _get_chat_turn_service(request)
        active_chat_session_id: int | None = None
        resolved_request_id: str | None = None

        try:
            message = _validate_message_input(message)
            requested_chat_session_id = _validate_chat_session_input(chat_session_id)
            resolved_request_id = _validate_request_id_input(request_id)
            logger.info(
                "chat.request_received chars=%s chat_session_id=%s client_id=%s request_id=%s",
                len(message),
                requested_chat_session_id,
                client_id,
                resolved_request_id,
            )

            start_result = await asyncio.to_thread(
                chat_turn_service.start_turn,
                client_id=client_id,
                request_id=resolved_request_id,
                chat_session_id=requested_chat_session_id,
                message=message,
            )
            if start_result.outcome == "missing":
                logger.warning(
                    "chat.request_target_missing chat_session_id=%s client_id=%s request_id=%s",
                    requested_chat_session_id,
                    client_id,
                    resolved_request_id,
                )
                return _finalize_response_with_client_cookie(
                    _render_chat_not_found_message(timestamp),
                    client_id=client_id,
                    should_set_cookie=should_set_client_cookie,
                )

            if start_result.turn_request_state is None:  # pragma: no cover - defensive
                raise RuntimeError("Turn request start result is missing its state.")

            active_chat_session_id = start_result.turn_request_state.turn_request.chat_session_id
            if start_result.outcome == "duplicate":
                logger.info(
                    "chat.request_replayed chat_session_id=%s client_id=%s request_id=%s status=%s",
                    active_chat_session_id,
                    client_id,
                    resolved_request_id,
                    start_result.turn_request_state.turn_request.status,
                )
                turn_request_state: ChatTurnRequestState | None = start_result.turn_request_state
                if (
                    turn_request_state is not None
                    and turn_request_state.turn_request.status == "processing"
                ):
                    turn_request_state = await _await_turn_request_resolution(
                        chat_turn_service,
                        client_id=client_id,
                        request_id=resolved_request_id,
                    )
                if turn_request_state is None or turn_request_state.turn_request.status == "processing":
                    return _finalize_response_with_client_cookie(
                        _render_chat_error_htmx_response(
                            request,
                            agent=agent,
                            repository=repository,
                            client_id=client_id,
                            active_chat_session_id=active_chat_session_id,
                            title="Request In Progress",
                            body="This message is already being processed. Please wait for the current response to finish.",
                            timestamp=timestamp,
                            status_code=409,
                        ),
                        client_id=client_id,
                        should_set_cookie=should_set_client_cookie,
                    )
                replay_response = _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    turn_request_state=turn_request_state,
                    timestamp=timestamp,
                )
                return _finalize_response_with_client_cookie(
                    replay_response,
                    client_id=client_id,
                    should_set_cookie=should_set_client_cookie,
                )

            if start_result.chat_session is None:  # pragma: no cover - defensive
                raise RuntimeError("Started turn request is missing its chat session.")

            logger.info(
                "chat.request_claimed chat_session_id=%s client_id=%s request_id=%s",
                start_result.chat_session.id,
                client_id,
                resolved_request_id,
            )

            response = await asyncio.to_thread(
                agent.process_message,
                message,
                _conversation_history_from_messages(start_result.prior_messages),
            )
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.complete_turn,
                client_id=client_id,
                request_id=resolved_request_id,
                assistant_content=response,
            )
            html_response = _render_turn_request_state_response(
                request,
                agent=agent,
                repository=repository,
                client_id=client_id,
                turn_request_state=turn_request_state,
                timestamp=timestamp,
            )

            logger.info(
                "chat.request_succeeded request_chars=%s response_chars=%s chat_session_id=%s client_id=%s request_id=%s status=%s",
                len(message),
                len(response),
                active_chat_session_id,
                client_id,
                resolved_request_id,
                turn_request_state.turn_request.status,
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
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="rate_limited",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.AuthenticationError as e:
            _log_known_chat_error("chat.authentication_failed", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="authentication_failed",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APITimeoutError as e:
            _log_known_chat_error("chat.timeout", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="timeout",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APIConnectionError as e:
            _log_known_chat_error("chat.connection_error", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="connection_error",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.BadRequestError as e:
            _log_known_chat_error("chat.bad_request", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="bad_request",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except openai.APIError as e:
            _log_known_chat_error("chat.api_error", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="api_error",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except EmptyModelResponseError as e:
            _log_known_chat_error("chat.empty_model_response", e)
            turn_request_state = await asyncio.to_thread(
                chat_turn_service.fail_turn,
                client_id=client_id,
                request_id=resolved_request_id or "",
                failure_code="empty_model_response",
            )
            return _finalize_response_with_client_cookie(
                _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    timestamp=timestamp,
                    turn_request_state=turn_request_state,
                ),
                client_id=client_id,
                should_set_cookie=should_set_client_cookie,
            )

        except Exception as e:
            logger.error("chat.unexpected_error detail=%s", str(e), exc_info=True)
            if resolved_request_id is not None and active_chat_session_id is not None:
                turn_request_state = await asyncio.to_thread(
                    chat_turn_service.fail_turn,
                    client_id=client_id,
                    request_id=resolved_request_id,
                    failure_code="unexpected_error",
                )
                error_response = _render_turn_request_state_response(
                    request,
                    agent=agent,
                    repository=repository,
                    client_id=client_id,
                    turn_request_state=turn_request_state,
                    timestamp=timestamp,
                )
                return _finalize_response_with_client_cookie(
                    error_response,
                    client_id=client_id,
                    should_set_cookie=should_set_client_cookie,
                )
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
