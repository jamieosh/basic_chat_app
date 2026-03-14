import asyncio
import html
import os
from textwrap import dedent
from contextlib import asynccontextmanager
from datetime import datetime

import openai
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.openai_agent import EmptyModelResponseError, OpenAIAgent
from utils.diagnostics import (
    DiagnosticCheck,
    StartupDiagnosticsError,
    build_readiness_payload,
    collect_startup_checks,
    raise_for_failed_startup_checks,
)
from utils.html_formatter import format_response_as_html
from utils.logging_config import get_logger, init_logging

logger = get_logger("api")
templates = Jinja2Templates(directory="templates")


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

    title_html = f'<div class="font-bold">{html.escape(title)}</div>' if title else ""
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
    return HTMLResponse(
        content=_render_bot_message(html.escape(body), timestamp, title, is_error=True),
        status_code=status_code,
    )


def _validate_message_input(message: str | None) -> str:
    if message is None or not message.strip():
        raise ValueError("Message cannot be empty")
    return message


def _set_startup_state(app: FastAPI, *, startup_complete: bool) -> None:
    app.state.startup_complete = startup_complete


def _readiness_status(app: FastAPI) -> tuple[int, dict[str, object]]:
    return build_readiness_payload(
        startup_complete=bool(getattr(app.state, "startup_complete", False)),
        agent_initialized=hasattr(app.state, "agent"),
    )


def _log_known_chat_error(event: str, exc: Exception) -> None:
    logger.warning("%s detail=%s", event, str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize dependencies at startup instead of import time."""
    load_dotenv()
    init_logging()
    _set_startup_state(app, startup_complete=False)
    logger.info("startup.begin")

    startup_checks = collect_startup_checks()
    try:
        raise_for_failed_startup_checks(startup_checks)
        app.state.agent = OpenAIAgent(api_key=os.environ["OPENAI_API_KEY"])
    except StartupDiagnosticsError as exc:
        for failure in exc.failures:
            logger.critical("startup.failed check=%s detail=%s", failure.name, failure.detail)
        raise
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
        logger.info("startup.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Render the home page."""
        logger.debug("home.render")
        agent = _get_agent(request)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "model_display_name": agent.model_display_name,
                "display_name": agent.display_name,
            },
        )

    @app.post("/send-message-htmx", response_class=HTMLResponse)
    async def chat_htmx(request: Request, message: str | None = Form(None)):
        """Process a chat message and return the response as HTML."""
        timestamp = datetime.now().strftime("%I:%M %p")
        agent = _get_agent(request)

        try:
            message = _validate_message_input(message)
            logger.info("chat.request_received chars=%s", len(message))

            response = await asyncio.to_thread(agent.process_message, message)
            formatted_content = format_response_as_html(response)
            html_response = _render_bot_message(formatted_content, timestamp)

            logger.info(
                "chat.request_succeeded request_chars=%s response_chars=%s",
                len(message),
                len(response),
            )
            return HTMLResponse(content=html_response)

        except ValueError as e:
            _log_known_chat_error("chat.validation_failed", e)
            return _render_error_message("Invalid Input", str(e), timestamp, 400)

        except openai.RateLimitError as e:
            _log_known_chat_error("chat.rate_limited", e)
            return _render_error_message(
                "Rate Limit Exceeded",
                "The AI service is currently busy. Please try again in a few moments.",
                timestamp,
                429,
            )

        except openai.AuthenticationError as e:
            _log_known_chat_error("chat.authentication_failed", e)
            return _render_error_message(
                "Authentication Error",
                "There's an issue with the AI service authentication. Please contact support.",
                timestamp,
                401,
            )

        except openai.APITimeoutError as e:
            _log_known_chat_error("chat.timeout", e)
            return _render_error_message(
                "Request Timeout",
                "The AI service took too long to respond. Please try again.",
                timestamp,
                504,
            )

        except openai.APIConnectionError as e:
            _log_known_chat_error("chat.connection_error", e)
            return _render_error_message(
                "Connection Error",
                "Could not connect to the AI service. Please check your internet connection and try again.",
                timestamp,
                503,
            )

        except openai.BadRequestError as e:
            _log_known_chat_error("chat.bad_request", e)
            return _render_error_message(
                "AI Service Error",
                "The AI service rejected the request. Please try again later.",
                timestamp,
                502,
            )

        except openai.APIError as e:
            _log_known_chat_error("chat.api_error", e)
            return _render_error_message(
                "AI Service Error",
                "The AI service encountered an error. Please try again later.",
                timestamp,
                500,
            )

        except EmptyModelResponseError as e:
            _log_known_chat_error("chat.empty_model_response", e)
            return _render_error_message(
                "AI Service Error",
                "The AI service returned an empty response. Please try again later.",
                timestamp,
                502,
            )

        except Exception as e:
            logger.error("chat.unexpected_error detail=%s", str(e), exc_info=True)
            return _render_error_message(
                "Unexpected Error",
                "Sorry, something went wrong. Please try again.",
                timestamp,
                500,
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
