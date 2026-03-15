from datetime import datetime, timedelta
from pathlib import Path
import re
import types

import main
import httpx
import openai
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agents.base_agent import ConversationTurn
from agents.openai_agent import EmptyModelResponseError
from utils import diagnostics
from utils.client_identity import CLIENT_ID_COOKIE_MAX_AGE_SECONDS, CLIENT_ID_COOKIE_NAME
from utils.diagnostics import StartupDiagnosticsError
from utils.settings import RuntimeSettings


def _extract_chat_session_id(response_text: str) -> int:
    match = re.search(r'id="chat-session-id"[^>]*value="(\d+)"', response_text)
    if match is None:
        raise AssertionError("Expected response to include an out-of-band chat session ID input.")
    return int(match.group(1))


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
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
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
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
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
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
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
    assert "Ask the first question" in response.text


def test_home_redirects_to_most_recent_visible_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    first_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    second_chat = repository.create_chat(client_id="client-a", title="Chat 2")

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].endswith(f"/chats/{second_chat.id}")
    assert first_chat.id != second_chat.id


def test_home_sets_anonymous_client_cookie_on_first_visit(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.cookies.get(CLIENT_ID_COOKIE_NAME)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert f"Max-Age={CLIENT_ID_COOKIE_MAX_AGE_SECONDS}" in response.headers["set-cookie"]


def test_home_reuses_existing_anonymous_client_cookie(client):
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "existing-client-id")

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("set-cookie") is None
    assert client.cookies.get(CLIENT_ID_COOKIE_NAME) == "existing-client-id"


def test_home_renders_reviewed_external_frontend_asset_references(client):
    response = client.get("/")

    assert response.status_code == 200
    assert '<script src="https://unpkg.com/htmx.org@1.9.5"></script>' in response.text
    assert '<script src="https://cdn.tailwindcss.com"></script>' in response.text


def test_format_chat_list_timestamp_shows_time_for_today():
    timestamp = datetime.now().replace(second=0, microsecond=0).isoformat()

    formatted = main._format_chat_list_timestamp(timestamp)

    assert ":" in formatted
    assert "AM" in formatted or "PM" in formatted


def test_format_chat_list_timestamp_shows_month_and_day_for_older_dates():
    timestamp = (datetime.now() - timedelta(days=1)).replace(second=0, microsecond=0).isoformat()

    formatted = main._format_chat_list_timestamp(timestamp)

    assert ":" not in formatted
    assert "AM" not in formatted
    assert "PM" not in formatted


def test_home_renders_unavailable_shell_when_agent_is_missing(client):
    del client.app.state.agent

    response = client.get("/")

    assert response.status_code == 503
    assert "Chat unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert 'data-chat-available="false"' in response.text
    assert 'id="message-input"' in response.text
    assert 'id="send-button"' in response.text


def test_home_renders_unavailable_shell_when_storage_is_missing(client):
    del client.app.state.chat_repository

    response = client.get("/")

    assert response.status_code == 503
    assert "Chat unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert 'data-chat-available="false"' in response.text


def test_send_message_returns_bot_message_html(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg, _history=None: "Hello from test")

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    assert "bot-message" in response.text
    assert "Hello from test" in response.text
    assert 'class="message-body"' in response.text


def test_send_message_sets_anonymous_client_cookie_when_missing(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg, _history=None: "Hello from test")

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    assert response.cookies.get(CLIENT_ID_COOKIE_NAME)
    assert "HttpOnly" in response.headers["set-cookie"]


def test_send_message_creates_chat_and_persists_first_turn(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg, _history=None: "Hello from test")

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 200
    created_chat_session_id = _extract_chat_session_id(response.text)
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{created_chat_session_id}")
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)

    assert len(chats) == 1
    assert chats[0].id == created_chat_session_id
    assert chats[0].title == "Chat 1"
    assert [message.role for message in repository.list_messages_for_chat(chat_session_id=created_chat_session_id, client_id=client_id)] == [
        "user",
        "assistant",
    ]


def test_send_message_appends_to_existing_chat_instead_of_creating_another(client, monkeypatch):
    call_count = {"count": 0}

    def fake_process_message(_msg, _history=None):
        call_count["count"] += 1
        return f"Reply {call_count['count']}"

    monkeypatch.setattr(client.app.state.agent, "process_message", fake_process_message)

    first_response = client.post("/send-message-htmx", data={"message": "Hi"})
    chat_session_id = _extract_chat_session_id(first_response.text)

    second_response = client.post(
        "/send-message-htmx",
        data={"message": "Follow-up", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 200
    assert _extract_chat_session_id(second_response.text) == chat_session_id
    assert second_response.headers["HX-Push-Url"].endswith(f"/chats/{chat_session_id}")

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)
    messages = repository.list_messages_for_chat(chat_session_id=chat_session_id, client_id=client_id)

    assert len(chats) == 1
    assert [message.content for message in messages] == ["Hi", "Reply 1", "Follow-up", "Reply 2"]


def test_send_message_passes_prior_transcript_to_agent_in_order(client, monkeypatch):
    captured_histories = []

    def fake_process_message(_msg, conversation_history=None):
        captured_histories.append(list(conversation_history or []))
        return "Reply"

    monkeypatch.setattr(client.app.state.agent, "process_message", fake_process_message)

    first_response = client.post("/send-message-htmx", data={"message": "First"})
    chat_session_id = _extract_chat_session_id(first_response.text)

    second_response = client.post(
        "/send-message-htmx",
        data={"message": "Second", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 200
    assert captured_histories[0] == []
    assert captured_histories[1] == [
        ConversationTurn(role="user", content="First"),
        ConversationTurn(role="assistant", content="Reply"),
    ]


def test_send_message_returns_generic_not_found_for_missing_or_foreign_chat(client, monkeypatch):
    monkeypatch.setattr(client.app.state.agent, "process_message", lambda _msg, _history=None: "unused")
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    repository = client.app.state.chat_repository
    foreign_chat = repository.create_chat(client_id="client-b", title="Other chat")

    foreign_response = client.post(
        "/send-message-htmx",
        data={"message": "Hi", "chat_session_id": str(foreign_chat.id)},
    )
    missing_response = client.post(
        "/send-message-htmx",
        data={"message": "Hi", "chat_session_id": "999999"},
    )

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.text == missing_response.text
    assert "The requested chat could not be found." in foreign_response.text


def test_chat_page_renders_full_stored_transcript(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.create_message(chat_session_id=chat.id, client_id="client-a", role="user", content="First")
    repository.create_message(chat_session_id=chat.id, client_id="client-a", role="assistant", content="Reply one")
    repository.create_message(chat_session_id=chat.id, client_id="client-a", role="user", content="Second")
    repository.create_message(chat_session_id=chat.id, client_id="client-a", role="assistant", content="Reply two")

    response = client.get(f"/chats/{chat.id}")

    assert response.status_code == 200
    assert "Chat 1" in response.text
    assert "First" in response.text
    assert "Reply one" in response.text
    assert "Second" in response.text
    assert "Reply two" in response.text
    assert f'value="{chat.id}"' in response.text


def test_chat_page_returns_generic_not_found_for_missing_or_foreign_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    foreign_chat = repository.create_chat(client_id="client-b", title="Foreign")

    foreign_response = client.get(f"/chats/{foreign_chat.id}")
    missing_response = client.get("/chats/999999")

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.text == missing_response.text
    assert "Chat not found" in foreign_response.text


def test_chat_list_partial_renders_visible_chats(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    first_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    second_chat = repository.create_chat(client_id="client-a", title="Chat 2")

    response = client.get("/chat-list")

    assert response.status_code == 200
    assert 'id="chat-list-panel"' in response.text
    assert "Chat 1" in response.text
    assert "Chat 2" in response.text
    assert response.text.index("Chat 2") < response.text.index("Chat 1")
    assert str(first_chat.id) in response.text
    assert str(second_chat.id) in response.text


def test_chat_start_page_renders_start_screen_even_when_visible_chats_exist(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    repository.create_chat(client_id="client-a", title="Chat 1")

    response = client.get("/chat-start")

    assert response.status_code == 200
    assert "Start a new chat" in response.text
    assert 'value=""' in response.text
    assert "Chat 1" in response.text


def test_chat_start_transcript_partial_renders_start_screen_and_pushes_chat_start_url(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    first_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.create_chat(client_id="client-a", title="Chat 2")

    response = client.get("/chat-start/transcript")

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == "/chat-start"
    assert "Ask the first question" in response.text
    assert 'id="chat-view-header"' in response.text
    assert 'id="chat-list-panel"' in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert f'data-chat-id="{first_chat.id}"' in response.text
    assert 'id="chat-session-id"' in response.text
    assert 'value=""' in response.text


def test_chat_transcript_partial_renders_transcript_and_oob_updates(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    first_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    second_chat = repository.create_chat(client_id="client-a", title="Chat 2")
    repository.create_message(chat_session_id=first_chat.id, client_id="client-a", role="user", content="First")
    repository.create_message(chat_session_id=first_chat.id, client_id="client-a", role="assistant", content="Reply")

    response = client.get(f"/chats/{first_chat.id}/transcript")

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{first_chat.id}")
    assert "First" in response.text
    assert "Reply" in response.text
    assert 'id="chat-view-header"' in response.text
    assert 'id="chat-list-panel"' in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert f'data-chat-id="{first_chat.id}"' in response.text
    assert f'data-chat-id="{second_chat.id}"' in response.text
    assert f'value="{first_chat.id}"' in response.text


def test_send_message_persists_user_turn_without_assistant_reply_when_follow_up_fails(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error_response = httpx.Response(429, request=request)
    call_count = {"count": 0}

    def fake_process_message(_msg, _history=None):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return "Reply 1"
        raise openai.RateLimitError("rate limit", response=error_response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", fake_process_message)

    first_response = client.post("/send-message-htmx", data={"message": "First"})
    chat_session_id = _extract_chat_session_id(first_response.text)
    second_response = client.post(
        "/send-message-htmx",
        data={"message": "Second", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 429
    assert _extract_chat_session_id(second_response.text) == chat_session_id

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    messages = repository.list_messages_for_chat(chat_session_id=chat_session_id, client_id=client_id)

    assert [message.content for message in messages] == ["First", "Reply 1", "Second"]
    assert [message.role for message in messages] == ["user", "assistant", "user"]


def test_send_message_first_message_failure_still_returns_created_chat_session_id(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error_response = httpx.Response(429, request=request)

    def raise_rate_limit(_msg, _history=None):
        raise openai.RateLimitError("rate limit", response=error_response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_rate_limit)

    response = client.post("/send-message-htmx", data={"message": "First"})

    assert response.status_code == 429
    chat_session_id = _extract_chat_session_id(response.text)

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)
    messages = repository.list_messages_for_chat(chat_session_id=chat_session_id, client_id=client_id)

    assert len(chats) == 1
    assert chats[0].id == chat_session_id
    assert [message.role for message in messages] == ["user"]
    assert [message.content for message in messages] == ["First"]


def test_send_message_returns_service_unavailable_html_when_agent_is_missing(client):
    del client.app.state.agent

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_returns_service_unavailable_html_when_storage_is_missing(client):
    del client.app.state.chat_repository

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_returns_startup_message_when_startup_is_incomplete(client):
    client.app.state.startup_complete = False

    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is still starting up. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_offloads_blocking_agent_call_from_event_loop(client, monkeypatch):
    captured = {}

    def fake_process_message(raw_message, conversation_history=None):
        captured["processed_message"] = raw_message
        captured["conversation_history"] = conversation_history
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
    assert captured["args"] == ("Hi", [])
    assert captured["kwargs"] == {}
    assert captured["processed_message"] == "Hi"
    assert captured["conversation_history"] == []
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
    def raise_value_error(_msg, _history=None):
        raise ValueError("<b>bad input</b>")

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_value_error)
    response = client.post("/send-message-htmx", data={"message": "Hi"})

    assert response.status_code == 400
    assert "&lt;b&gt;bad input&lt;/b&gt;" in response.text
    assert "<b>bad input</b>" not in response.text


def test_send_message_handles_rate_limit_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)

    def raise_rate_limit(_msg, _history=None):
        raise openai.RateLimitError("rate limit", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_rate_limit)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 429
    assert "Rate Limit Exceeded" in result.text
    assert 'class="message-body"' in result.text


def test_send_message_handles_authentication_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(401, request=request)

    def raise_auth_error(_msg, _history=None):
        raise openai.AuthenticationError("auth failed", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_auth_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 401
    assert "Authentication Error" in result.text


def test_send_message_handles_api_connection_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_connection_error(_msg, _history=None):
        raise openai.APIConnectionError(message="conn", request=request)

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_connection_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 503
    assert "Connection Error" in result.text


def test_send_message_handles_api_timeout_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_timeout_error(_msg, _history=None):
        raise openai.APITimeoutError(request=request)

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_timeout_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 504
    assert "Request Timeout" in result.text


def test_send_message_handles_bad_request_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)

    def raise_bad_request_error(_msg, _history=None):
        raise openai.BadRequestError("bad request", response=response, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_bad_request_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 502
    assert "AI Service Error" in result.text


def test_send_message_handles_generic_openai_api_error(client, monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_api_error(_msg, _history=None):
        raise openai.APIError("api failed", request=request, body={})

    monkeypatch.setattr(client.app.state.agent, "process_message", raise_api_error)
    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 500
    assert "AI Service Error" in result.text


def test_send_message_handles_empty_model_response(client, monkeypatch):
    def raise_empty_model_response(_msg, _history=None):
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
        lambda _msg, _history=None: "Example:\n```python\nprint('ok')\n```\nDone.",
    )

    result = client.post("/send-message-htmx", data={"message": "Hi"})

    assert result.status_code == 200
    assert "<pre" in result.text
    assert "language-python" in result.text
    assert "<p><pre" not in result.text
    assert "Example:" in result.text
    assert "Done." in result.text


def test_send_message_handles_runtime_error_without_except_typeerror(client, monkeypatch):
    def raise_runtime_error(_msg, _history=None):
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

        def process_message(self, _msg, _history=None):
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
        chat_database_path=Path("data/chat.db"),
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


def test_create_app_fails_with_clear_message_when_database_bootstrap_fails(monkeypatch, tmp_path):
    def fake_init_logging():
        return None

    broken_parent = tmp_path / "not-a-directory"
    broken_parent.write_text("file blocks nested db path")

    monkeypatch.setattr(main, "load_project_env", lambda: False)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)

    settings = RuntimeSettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_prompt_name="default",
        openai_temperature=1.0,
        openai_timeout_seconds=30.0,
        chat_database_path=broken_parent / "chat.db",
        cors_allowed_origins=["*"],
        cors_allow_credentials=False,
        cors_allowed_methods=["*"],
        cors_allowed_headers=["*"],
    )

    app = main.create_app(settings=settings)

    with pytest.raises(StartupDiagnosticsError, match="storage_initialization"):
        with TestClient(app):
            pass
