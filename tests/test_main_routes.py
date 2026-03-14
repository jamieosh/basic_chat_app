from pathlib import Path
import types

import main
import httpx
import openai
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agents.openai_agent import EmptyModelResponseError
from utils import diagnostics
from utils.diagnostics import StartupDiagnosticsError
from utils.settings import RuntimeSettings


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check_reports_ready_state(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": [
            {
                "name": "startup_completed",
                "status": "ok",
                "detail": "Application startup completed.",
            },
            {
                "name": "agent_initialized",
                "status": "ok",
                "detail": "Chat agent is initialized.",
            },
        ],
    }


def test_readiness_check_returns_503_when_agent_is_missing(client):
    del client.app.state.agent

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": [
            {
                "name": "startup_completed",
                "status": "ok",
                "detail": "Application startup completed.",
            },
            {
                "name": "agent_initialized",
                "status": "failed",
                "detail": "Chat agent is not available to process messages.",
            },
        ],
        "failed_checks": [
            {
                "name": "agent_initialized",
                "status": "failed",
                "detail": "Chat agent is not available to process messages.",
            }
        ],
    }


def test_readiness_check_reports_partial_startup_when_agent_exists_but_startup_is_incomplete(client):
    client.app.state.startup_complete = False

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": [
            {
                "name": "startup_completed",
                "status": "failed",
                "detail": "Application startup has not completed successfully.",
            },
            {
                "name": "agent_initialized",
                "status": "ok",
                "detail": "Chat agent is initialized.",
            },
        ],
        "failed_checks": [
            {
                "name": "startup_completed",
                "status": "failed",
                "detail": "Application startup has not completed successfully.",
            }
        ],
    }


def test_home_renders_chat_header(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Chat with AI Chat" in response.text
    assert client.app.state.agent.display_name in response.text
    assert client.app.state.agent.model_display_name in response.text


def test_send_message_returns_bot_message_html(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg: "Hello from test")

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    assert "bot-message" in response.text
    assert "Hello from test" in response.text
    assert 'class="message-body"' in response.text


def test_send_message_offloads_blocking_agent_call_from_event_loop(client, monkeypatch):
    captured = {}

    def fake_process_message(raw_message):
        captured["processed_message"] = raw_message
        return "Hello from thread"

    async def fake_to_thread(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(client.app.state.agent, "process_message", fake_process_message)
    monkeypatch.setattr(main.asyncio, "to_thread", fake_to_thread)

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    assert captured["func"] is fake_process_message
    assert captured["args"] == ("Hi",)
    assert captured["kwargs"] == {}
    assert captured["processed_message"] == "Hi"
    assert "Hello from thread" in response.text


def test_send_message_rejects_blank_messages(client):
    response = client.post("/send-message-htmx", data={"message": "   "})

    assert response.status_code == 400
    assert "Invalid Input" in response.text
    assert "Message cannot be empty" in response.text


def test_send_message_requires_message_field(client):
    response = client.post("/send-message-htmx", data={})

    assert response.status_code == 400
    assert "Invalid Input" in response.text
    assert "Message cannot be empty" in response.text


def test_send_message_validation_error_escapes_html(client, monkeypatch):
    def raise_value_error(_msg):
        raise ValueError("<b>bad input</b>")

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_value_error)
    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 400
    assert "&lt;b&gt;bad input&lt;/b&gt;" in response.text
    assert "<b>bad input</b>" not in response.text


def test_send_message_handles_rate_limit_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)

    def raise_rate_limit(_msg):
        raise openai.RateLimitError("rate limit", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_rate_limit)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 429
    assert "Rate Limit Exceeded" in result.text
    assert 'class="message-body"' in result.text


def test_send_message_handles_authentication_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(401, request=request)

    def raise_auth_error(_msg):
        raise openai.AuthenticationError("auth failed", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_auth_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 401
    assert "Authentication Error" in result.text


def test_send_message_handles_api_connection_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_connection_error(_msg):
        raise openai.APIConnectionError(message="conn", request=request)

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_connection_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 503
    assert "Connection Error" in result.text


def test_send_message_handles_api_timeout_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_timeout_error(_msg):
        raise openai.APITimeoutError(request=request)

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_timeout_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 504
    assert "Request Timeout" in result.text


def test_send_message_handles_bad_request_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)

    def raise_bad_request_error(_msg):
        raise openai.BadRequestError("bad request", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_bad_request_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 502
    assert "AI Service Error" in result.text


def test_send_message_handles_generic_openai_api_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_api_error(_msg):
        raise openai.APIError("api failed", request=request, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_api_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 500
    assert "AI Service Error" in result.text


def test_send_message_handles_empty_model_response(client, monkeypatch):
    def raise_empty_model_response(_msg):
        raise EmptyModelResponseError("AI response did not include any text content")

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_empty_model_response)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 502
    assert "AI Service Error" in result.text
    assert "empty response" in result.text


def test_send_message_renders_mixed_text_and_code_without_paragraph_wrapping(client, monkeypatch):
    monkeypatch.setattr(
        client.app.state.agent,
        "process_message",
        lambda _msg: "Example:\n```python\nprint('ok')\n```\nDone.",
    )

    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 200
    assert "<pre" in result.text
    assert "language-python" in result.text
    assert "<p><pre" not in result.text
    assert "Example:" in result.text
    assert "Done." in result.text


def test_send_message_handles_runtime_error_without_except_typeerror(client, monkeypatch):
    def raise_runtime_error(_msg):
        raise RuntimeError("boom")

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_runtime_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 500
    assert "Unexpected Error" in result.text
    assert "Sorry, something went wrong. Please try again." in result.text
    assert "boom" not in result.text
    assert "do not inherit from BaseException" not in result.text


def test_get_agent_raises_503_when_agent_is_unavailable(client):
    del client.app.state.agent

    with pytest.raises(HTTPException) as exc_info:
        main._get_agent(types.SimpleNamespace(app=client.app))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "AI agent unavailable"


def test_render_bot_message_escapes_title_and_applies_error_style():
    rendered = main._render_bot_message(
        "<strong>safe body</strong>",
        "10:00 AM",
        "<script>alert('x')</script>",
        is_error=True,
    )

    assert "bot-message" in rendered
    assert "error-message" in rendered
    assert "&lt;script&gt;alert" in rendered
    assert "<script>" not in rendered
    assert "<strong>safe body</strong>" in rendered


def test_render_error_message_escapes_body_and_sets_status_code():
    response = main._render_error_message("Invalid Input", "<b>bad</b>", "10:00 AM", 400)

    assert response.status_code == 400
    assert "error-message" in response.body.decode()
    assert "&lt;b&gt;bad&lt;/b&gt;" in response.body.decode()
    assert "<b>bad</b>" not in response.body.decode()


def test_create_app_defers_logging_and_agent_init_until_startup(monkeypatch):
    calls = {"init_logging": 0, "agent_ctor": 0}

    class FakeAgent:
        display_name = "Fake Bot"
        model_display_name = "Fake Model"

        def __init__(self, api_key, model, prompt_name, temperature, timeout):
            calls["agent_ctor"] += 1
            self.api_key = api_key
            self.model = model
            self.prompt_name = prompt_name
            self.temperature = temperature
            self.timeout = timeout

        def process_message(self, _msg):
            return "unused"

    def fake_init_logging():
        calls["init_logging"] += 1

    monkeypatch.setattr(main, "OpenAIAgent", FakeAgent)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    app = main.create_app()
    assert calls == {"init_logging": 0, "agent_ctor": 0}

    with TestClient(app) as startup_client:
        assert calls == {"init_logging": 1, "agent_ctor": 1}
        assert startup_client.app.state.agent.display_name == "Fake Bot"
        assert startup_client.app.state.agent.model == "gpt-5-mini"


def test_create_app_fails_with_clear_message_when_openai_key_missing(monkeypatch):
    def fake_init_logging():
        return None

    class NeverCalledAgent:
        def __init__(self, api_key):
            raise AssertionError("OpenAIAgent should not be constructed without OPENAI_API_KEY")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(main, "load_project_env", lambda: False)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setattr(main, "OpenAIAgent", NeverCalledAgent)

    app = main.create_app()
    expected = (
        "Startup diagnostics failed: OPENAI_API_KEY: "
        "Missing required environment variable OPENAI_API_KEY"
    )
    with pytest.raises(StartupDiagnosticsError, match=expected):
        with TestClient(app):
            pass


def test_create_app_fails_with_clear_message_when_system_prompt_template_missing(monkeypatch):
    def fake_init_logging():
        return None

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "load_project_env", lambda: False)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setattr(
        diagnostics,
        "get_required_startup_paths",
        lambda _prompt_name: [
            (
                "system_prompt_template",
                Path("templates/prompts/openai/missing_system.j2"),
                "Restore templates/prompts/openai/system_default.j2 or update the configured prompt name.",
            )
        ],
    )

    app = main.create_app()
    expected = (
        "Startup diagnostics failed: system_prompt_template: "
        "Missing required path: templates/prompts/openai/missing_system.j2"
    )
    with pytest.raises(StartupDiagnosticsError, match=expected):
        with TestClient(app):
            pass


def test_create_app_uses_env_driven_cors_configuration():
    settings = RuntimeSettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_prompt_name="default",
        openai_temperature=1.0,
        openai_timeout_seconds=30.0,
        cors_allowed_origins=["https://example.com", "https://internal.example"],
        cors_allow_credentials=True,
        cors_allowed_methods=["GET", "POST"],
        cors_allowed_headers=["HX-Request", "Content-Type"],
    )

    app = main.create_app(settings=settings)

    cors_middleware = app.user_middleware[0]
    assert cors_middleware.kwargs == {
        "allow_origins": ["https://example.com", "https://internal.example"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["HX-Request", "Content-Type"],
    }
