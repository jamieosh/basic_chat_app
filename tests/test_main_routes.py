import main
import httpx
import openai
from fastapi.testclient import TestClient


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_renders_chat_header(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Chat with" in response.text
    assert client.app.state.agent.display_name in response.text
    assert client.app.state.agent.model_display_name in response.text


def test_send_message_returns_bot_message_html(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg: "Hello from test")

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    assert "bot-message" in response.text
    assert "Hello from test" in response.text


def test_send_message_rejects_blank_messages(client):
    response = client.post("/send-message-htmx", data={"message": "   "})

    assert response.status_code == 400
    assert "Invalid Input" in response.text


def test_send_message_requires_message_field(client):
    response = client.post("/send-message-htmx", data={})

    assert response.status_code == 422


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


def test_send_message_handles_runtime_error_without_except_typeerror(client, monkeypatch):
    def raise_runtime_error(_msg):
        raise RuntimeError("boom")

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_runtime_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 500
    assert "Unexpected Error" in result.text
    assert "boom" in result.text
    assert "do not inherit from BaseException" not in result.text


def test_create_app_defers_logging_and_agent_init_until_startup(monkeypatch):
    calls = {"init_logging": 0, "agent_ctor": 0}

    class FakeAgent:
        display_name = "Fake Bot"
        model_display_name = "Fake Model"

        def __init__(self, api_key):
            calls["agent_ctor"] += 1
            self.api_key = api_key

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
