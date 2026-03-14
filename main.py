import asyncio
import html
import os
from contextlib import asynccontextmanager
from datetime import datetime

import openai
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.openai_agent import EmptyModelResponseError, OpenAIAgent
from utils.html_formatter import format_response_as_html
from utils.logging_config import get_logger, init_logging, truncate_message

logger = get_logger("api")
templates = Jinja2Templates(directory="templates")


def _require_env_var(name: str) -> str:
    """Return a required env var value or raise a deterministic startup error."""
    value = os.getenv(name)
    if value and value.strip():
        return value

    message = (
        f"Missing required environment variable: {name}. "
        "Set it in .env or the process environment before startup."
    )
    logger.critical(message)
    raise RuntimeError(message)


def _get_agent(request: Request) -> OpenAIAgent:
    """Read the request-scoped agent initialized at startup."""
    try:
        return request.app.state.agent
    except AttributeError as exc:
        logger.error("OpenAI agent is not initialized")
        raise HTTPException(status_code=503, detail="AI agent unavailable") from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize dependencies at startup instead of import time."""
    load_dotenv()
    init_logging()
    app.state.agent = OpenAIAgent(api_key=_require_env_var("OPENAI_API_KEY"))
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Render the home page."""
        logger.info("Rendering home page")
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
    async def chat_htmx(request: Request, message: str = Form(...)):
        """Process a chat message and return the response as HTML."""
        timestamp = datetime.now().strftime("%I:%M %p")
        logger.debug("Generated timestamp: %s", timestamp)
        agent = _get_agent(request)

        try:
            logger.info(
                "Received request at /send-message-htmx: %s",
                truncate_message(message),
            )
            logger.debug("Request details: %s", request.headers)

            response = await asyncio.to_thread(agent.process_message, message)
            formatted_content = await format_response_as_html(response)

            html_response = f"""
            <div class="message bot-message">
                <div class="message-content">
                    <p>{formatted_content}</p>
                    <div class="message-timestamp">{timestamp}</div>
                </div>
            </div>
            """

            logger.info("Sending response: %s", truncate_message(response))
            return HTMLResponse(content=html_response)

        except ValueError as e:
            logger.warning("Validation error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Invalid Input</div>
                    <div>{html.escape(str(e))}</div>
                    <div class="message-timestamp">{timestamp}</div>
                </div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=400)

        except openai.RateLimitError as e:
            logger.error("Rate limit error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Rate Limit Exceeded</div>
                    <div>The AI service is currently busy. Please try again in a few moments.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=429)

        except openai.AuthenticationError as e:
            logger.error("Authentication error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Authentication Error</div>
                    <div>There's an issue with the AI service authentication. Please contact support.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=401)

        except openai.APITimeoutError as e:
            logger.error("Timeout error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Request Timeout</div>
                    <div>The AI service took too long to respond. Please try again.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=504)

        except openai.APIConnectionError as e:
            logger.error("API connection error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Connection Error</div>
                    <div>Could not connect to the AI service. Please check your internet connection and try again.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=503)

        except openai.APIError as e:
            logger.error("OpenAI API error: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">AI Service Error</div>
                    <div>The AI service encountered an error. Please try again later.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=500)

        except EmptyModelResponseError as e:
            logger.error("OpenAI returned an empty message response: %s", str(e))
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">AI Service Error</div>
                    <div>The AI service returned an empty response. Please try again later.</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=502)

        except Exception as e:
            logger.error("Error processing message: %s", str(e), exc_info=True)
            error_html = f"""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="font-bold">Unexpected Error</div>
                    <div>Sorry, something went wrong: {html.escape(str(e))}</div>
                </div>
                <div class="message-timestamp">{timestamp}</div>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=500)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        logger.debug("Health check requested")
        return {"status": "ok"}

    return app


app = create_app()
