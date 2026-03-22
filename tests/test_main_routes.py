from datetime import datetime, timedelta
import itertools
from pathlib import Path
import re
import types

import main
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agents.base_agent import (
    ChatHarnessEvent,
    ChatHarnessExecutionError,
    ChatHarnessFailure,
    ChatHarnessIdentity,
    ChatHarnessRequest,
    ChatHarnessToolCall,
    ChatHarnessToolResult,
    ConversationTurn,
)
from agents.harness_registry import HarnessRegistry
from services import ChatTurnService
from utils import diagnostics
from utils.client_identity import CLIENT_ID_COOKIE_MAX_AGE_SECONDS, CLIENT_ID_COOKIE_NAME
from utils.diagnostics import StartupDiagnosticsError
from utils.settings import RuntimeSettings


def _extract_chat_session_id(response_text: str) -> int:
    match = re.search(r'id="chat-session-id"[^>]*value="(\d+)"', response_text)
    if match is None:
        raise AssertionError("Expected response to include an out-of-band chat session ID input.")
    return int(match.group(1))


_REQUEST_ID_COUNTER = itertools.count(1)


def _send_message(client, data: dict[str, str] | None = None):
    payload = dict(data or {})
    payload.setdefault("request_id", f"request-{next(_REQUEST_ID_COUNTER)}")
    return client.post("/send-message-htmx", data=payload)


def _patch_harness_reply(monkeypatch, harness, reply_factory):
    def run_events(request):
        reply = reply_factory(request)
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=reply,
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            sequence=1,
        )

    monkeypatch.setattr(harness, "run_events", run_events)


def _patch_harness_failure(monkeypatch, harness, failure_factory):
    def run_events(request):
        raise failure_factory(request)

    monkeypatch.setattr(harness, "run_events", run_events)


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
                "name": "harness_initialized",
                "status": "ok",
                "detail": "Chat harness is initialized.",
                "metadata": {
                    "harness_key": "openai",
                    "provider_name": "openai",
                    "model": "gpt-5-mini",
                },
            },
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
            },
        ],
    }


def test_readiness_check_returns_503_when_harness_is_missing(client):
    del client.app.state.chat_harness_registry
    del client.app.state.chat_harness

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
                "name": "harness_initialized",
                "status": "failed",
                "detail": "Chat harness is not available to process messages.",
            },
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
            },
        ],
        "failed_checks": [
            {
                "name": "harness_initialized",
                "status": "failed",
                "detail": "Chat harness is not available to process messages.",
            }
        ],
    }


def test_readiness_check_reports_partial_startup_when_harness_exists_but_startup_is_incomplete(
    client,
):
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
                "name": "harness_initialized",
                "status": "ok",
                "detail": "Chat harness is initialized.",
                "metadata": {
                    "harness_key": "openai",
                    "provider_name": "openai",
                    "model": "gpt-5-mini",
                },
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
    assert client.app.state.chat_harness.identity.display_name in response.text
    assert client.app.state.chat_harness.identity.model_display_name in response.text
    assert "Ask the first question" in response.text


def test_home_renders_hidden_request_id_input(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="chat-request-id"' in response.text
    assert 'name="request_id"' in response.text


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


def test_home_renders_unavailable_shell_when_harness_is_missing(client):
    del client.app.state.chat_harness_registry
    del client.app.state.chat_harness

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
    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, lambda _request: "Hello from test")

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert "bot-message" in response.text
    assert "Hello from test" in response.text
    assert 'class="message-body"' in response.text


def test_send_message_sets_anonymous_client_cookie_when_missing(client, monkeypatch):
    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, lambda _request: "Hello from test")

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert response.cookies.get(CLIENT_ID_COOKIE_NAME)
    assert "HttpOnly" in response.headers["set-cookie"]


def test_send_message_creates_chat_and_persists_first_turn(client, monkeypatch):
    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, lambda _request: "Hello from test")

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    created_chat_session_id = _extract_chat_session_id(response.text)
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{created_chat_session_id}")
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)

    assert len(chats) == 1
    assert chats[0].id == created_chat_session_id
    assert chats[0].title == "Chat 1"
    assert [
        message.role
        for message in repository.list_messages_for_chat(
            chat_session_id=created_chat_session_id, client_id=client_id
        )
    ] == [
        "user",
        "assistant",
    ]


def test_send_message_replays_duplicate_first_submit_without_duplicate_turns(client, monkeypatch):
    call_count = {"count": 0}

    def fake_reply(_request):
        call_count["count"] += 1
        return "Hello from test"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, fake_reply)

    first_response = _send_message(
        client,
        {"message": "Hi", "request_id": "duplicate-first-request"},
    )
    second_response = _send_message(
        client,
        {"message": "Hi", "request_id": "duplicate-first-request"},
    )

    first_chat_session_id = _extract_chat_session_id(first_response.text)
    second_chat_session_id = _extract_chat_session_id(second_response.text)
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_chat_session_id == second_chat_session_id
    assert call_count["count"] == 1
    assert len(repository.list_visible_chats(client_id=client_id)) == 1
    assert [
        message.content
        for message in repository.list_messages_for_chat(
            chat_session_id=first_chat_session_id,
            client_id=client_id,
        )
    ] == ["Hi", "Hello from test"]


def test_send_message_appends_to_existing_chat_instead_of_creating_another(client, monkeypatch):
    call_count = {"count": 0}

    def fake_reply(_request):
        call_count["count"] += 1
        return f"Reply {call_count['count']}"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, fake_reply)

    first_response = _send_message(client, {"message": "Hi"})
    chat_session_id = _extract_chat_session_id(first_response.text)

    second_response = _send_message(
        client,
        {"message": "Follow-up", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 200
    assert _extract_chat_session_id(second_response.text) == chat_session_id
    assert second_response.headers["HX-Push-Url"].endswith(f"/chats/{chat_session_id}")

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id, client_id=client_id
    )

    assert len(chats) == 1
    assert [message.content for message in messages] == ["Hi", "Reply 1", "Follow-up", "Reply 2"]


def test_send_message_replays_duplicate_existing_chat_submit_without_duplicate_turns(
    client, monkeypatch
):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    call_count = {"count": 0}

    def fake_reply(_request):
        call_count["count"] += 1
        return "Reply 1"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, fake_reply)

    first_response = _send_message(
        client,
        {
            "message": "Follow-up",
            "chat_session_id": str(chat.id),
            "request_id": "duplicate-existing-request",
        },
    )
    second_response = _send_message(
        client,
        {
            "message": "Follow-up",
            "chat_session_id": str(chat.id),
            "request_id": "duplicate-existing-request",
        },
    )

    messages = repository.list_messages_for_chat(chat_session_id=chat.id, client_id="client-a")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert _extract_chat_session_id(first_response.text) == chat.id
    assert _extract_chat_session_id(second_response.text) == chat.id
    assert call_count["count"] == 1
    assert [message.content for message in messages] == ["Follow-up", "Reply 1"]


def test_send_message_passes_prior_transcript_to_agent_in_order(client, monkeypatch):
    captured_histories = []

    def fake_reply(request):
        captured_histories.append(list(request.conversation_history or []))
        return "Reply"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, fake_reply)

    first_response = _send_message(client, {"message": "First"})
    chat_session_id = _extract_chat_session_id(first_response.text)

    second_response = _send_message(
        client,
        {"message": "Second", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 200
    assert captured_histories[0] == []
    assert captured_histories[1] == [
        ConversationTurn(role="user", content="First"),
        ConversationTurn(role="assistant", content="Reply"),
    ]


def test_send_message_collects_multiple_output_events_into_one_persisted_reply(client, monkeypatch):
    def multi_event_reply(_request):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text="Hello",
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=" from test",
            sequence=1,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            sequence=2,
        )

    monkeypatch.setattr(client.app.state.chat_harness, "run_events", multi_event_reply)

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert "Hello from test" in response.text
    chat_session_id = _extract_chat_session_id(response.text)
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id,
        client_id=client_id,
    )
    assert [message.content for message in messages] == ["Hi", "Hello from test"]


def test_send_message_ignores_tool_events_and_persists_only_text_output(client, monkeypatch):
    def tool_event_reply(_request):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text="Hello",
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="tool_call",
            tool_call=ChatHarnessToolCall(
                call_id="call-1",
                tool_name="lookup_weather",
                arguments='{"city":"London"}',
            ),
            sequence=1,
        )
        yield ChatHarnessEvent(
            event_type="tool_result",
            tool_result=ChatHarnessToolResult(
                call_id="call-1",
                tool_name="lookup_weather",
                output='{"forecast":"Rain"}',
            ),
            sequence=2,
        )
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=" from test",
            sequence=3,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            sequence=4,
        )

    monkeypatch.setattr(client.app.state.chat_harness, "run_events", tool_event_reply)

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert "Hello from test" in response.text
    assert "lookup_weather" not in response.text
    chat_session_id = _extract_chat_session_id(response.text)
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id,
        client_id=client_id,
    )
    assert [message.content for message in messages] == ["Hi", "Hello from test"]


def test_send_message_delegates_harness_request_construction_to_turn_service(client, monkeypatch):
    captured = {}

    def fake_build_harness_request(*, client_id, request_id, start_result, message):
        captured["client_id"] = client_id
        captured["request_id"] = request_id
        captured["message"] = message
        captured["prior_messages"] = list(start_result.prior_messages)
        return ChatHarnessRequest(
            message=message,
            request_id=request_id,
            client_id=client_id,
            chat_session_id=None if start_result.chat_session is None else start_result.chat_session.id,
        )

    monkeypatch.setattr(
        client.app.state.chat_turn_service,
        "build_harness_request",
        fake_build_harness_request,
    )
    _patch_harness_reply(
        monkeypatch,
        client.app.state.chat_harness,
        lambda request: f"reply:{request.message}",
    )

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert captured["message"] == "Hi"
    assert captured["prior_messages"] == []
    assert "reply:Hi" in response.text


def test_send_message_returns_generic_not_found_for_missing_or_foreign_chat(client, monkeypatch):
    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, lambda _request: "unused")
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    repository = client.app.state.chat_repository
    foreign_chat = repository.create_chat(client_id="client-b", title="Other chat")
    archived_chat = repository.create_chat(client_id="client-a", title="Archived")
    repository.archive_chat(chat_session_id=archived_chat.id, client_id="client-a")

    foreign_response = _send_message(
        client,
        {"message": "Hi", "chat_session_id": str(foreign_chat.id)},
    )
    archived_response = _send_message(
        client,
        {"message": "Hi", "chat_session_id": str(archived_chat.id)},
    )
    missing_response = _send_message(
        client,
        {"message": "Hi", "chat_session_id": "999999"},
    )

    assert foreign_response.status_code == 404
    assert archived_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.text == missing_response.text
    assert archived_response.text == missing_response.text
    assert "The requested chat could not be found." in foreign_response.text


def test_chat_page_renders_full_stored_transcript(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.create_message(
        chat_session_id=chat.id, client_id="client-a", role="user", content="First"
    )
    repository.create_message(
        chat_session_id=chat.id, client_id="client-a", role="assistant", content="Reply one"
    )
    repository.create_message(
        chat_session_id=chat.id, client_id="client-a", role="user", content="Second"
    )
    repository.create_message(
        chat_session_id=chat.id, client_id="client-a", role="assistant", content="Reply two"
    )

    response = client.get(f"/chats/{chat.id}")

    assert response.status_code == 200
    assert "Chat 1" in response.text
    assert "First" in response.text
    assert "Reply one" in response.text
    assert "Second" in response.text
    assert "Reply two" in response.text
    assert f'value="{chat.id}"' in response.text


def test_chat_page_renders_delete_button_only_for_active_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    active_response = client.get(f"/chats/{chat.id}")
    start_response = client.get("/chat-start")
    missing_response = client.get("/chats/999999")

    assert f"/chats/{chat.id}/delete" in active_response.text
    assert 'hx-confirm="Delete this chat? This cannot be undone."' in active_response.text
    assert "/delete" not in start_response.text
    assert "/delete" not in missing_response.text


def test_chat_page_returns_generic_not_found_for_missing_or_foreign_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    foreign_chat = repository.create_chat(client_id="client-b", title="Foreign")

    foreign_response = client.get(f"/chats/{foreign_chat.id}")
    missing_response = client.get("/chats/999999")

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert "Chat not found" in foreign_response.text
    assert "Chat not found" in missing_response.text
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
    repository.create_message(
        chat_session_id=first_chat.id, client_id="client-a", role="user", content="First"
    )
    repository.create_message(
        chat_session_id=first_chat.id, client_id="client-a", role="assistant", content="Reply"
    )

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


def test_delete_chat_routes_to_next_visible_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    first_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    second_chat = repository.create_chat(client_id="client-a", title="Chat 2")
    repository.create_message(
        chat_session_id=second_chat.id, client_id="client-a", role="user", content="Keep this"
    )

    response = client.post(f"/chats/{first_chat.id}/delete")

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{second_chat.id}")
    assert "Keep this" in response.text
    assert "Chat 2" in response.text
    assert "Chat 1" not in response.text
    assert repository.get_chat(chat_session_id=first_chat.id, client_id="client-a") is None


def test_delete_chat_routes_to_start_screen_when_no_visible_chats_remain(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.create_message(
        chat_session_id=chat.id, client_id="client-a", role="user", content="Soon gone"
    )

    response = client.post(f"/chats/{chat.id}/delete")

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == "/chat-start"
    assert "Ask the first question" in response.text
    assert "No chats yet. Your first message will create one." in response.text
    assert 'value=""' in response.text
    assert repository.list_visible_chats(client_id="client-a") == []


def test_delete_chat_returns_not_found_for_missing_or_foreign_chat(client):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    repository.create_chat(client_id="client-a", title="Chat 1")
    foreign_chat = repository.create_chat(client_id="client-b", title="Foreign")

    foreign_response = client.post(f"/chats/{foreign_chat.id}/delete")
    missing_response = client.post("/chats/999999/delete")

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.text == missing_response.text
    assert "Chat not found" in foreign_response.text
    assert "Use the composer below to start a new chat." in foreign_response.text
    assert foreign_response.headers.get("HX-Push-Url") is None
    assert missing_response.headers.get("HX-Push-Url") is None


def test_send_message_persists_user_turn_without_assistant_reply_when_follow_up_fails(
    client, monkeypatch
):
    call_count = {"count": 0}

    def fake_run_events(_request):
        call_count["count"] += 1
        if call_count["count"] == 1:
            yield ChatHarnessEvent(
                event_type="output_text",
                output_text="Reply 1",
                sequence=0,
            )
            yield ChatHarnessEvent(
                event_type="completed",
                sequence=1,
            )
            return
        raise ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic follow-up failure",
            )
        )

    monkeypatch.setattr(client.app.state.chat_harness, "run_events", fake_run_events)

    first_response = _send_message(client, {"message": "First"})
    chat_session_id = _extract_chat_session_id(first_response.text)
    second_response = _send_message(
        client,
        {"message": "Second", "chat_session_id": str(chat_session_id)},
    )

    assert second_response.status_code == 429
    assert _extract_chat_session_id(second_response.text) == chat_session_id

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id, client_id=client_id
    )

    assert [message.content for message in messages] == ["First", "Reply 1", "Second"]
    assert [message.role for message in messages] == ["user", "assistant", "user"]


def test_send_message_does_not_persist_partial_output_when_event_stream_fails(client, monkeypatch):
    def partial_then_fail(_request):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text="Partial reply",
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="failed",
            failure=ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic partial failure",
            ),
            sequence=1,
        )

    monkeypatch.setattr(client.app.state.chat_harness, "run_events", partial_then_fail)

    response = _send_message(client, {"message": "First"})

    assert response.status_code == 429
    chat_session_id = _extract_chat_session_id(response.text)
    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id,
        client_id=client_id,
    )
    assert [message.role for message in messages] == ["user"]
    assert [message.content for message in messages] == ["First"]


def test_send_message_replays_duplicate_failed_first_submit_without_reprocessing(client, monkeypatch):
    chat_turn_service = client.app.state.chat_turn_service

    start_result = chat_turn_service.start_turn(
        client_id="client-a",
        request_id="duplicate-failed-first-request",
        chat_session_id=None,
        message="First",
    )
    failed_state = chat_turn_service.fail_turn(
        client_id="client-a",
        request_id="duplicate-failed-first-request",
        failure_code="rate_limited",
    )
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")

    def raise_if_reprocessed(*_args, **_kwargs):
        raise AssertionError("Should replay failure")

    _patch_harness_failure(
        monkeypatch,
        client.app.state.chat_harness,
        lambda _request: AssertionError("Should replay failure"),
    )

    response = _send_message(
        client,
        {"message": "First", "request_id": "duplicate-failed-first-request"},
    )

    assert start_result.outcome == "started"
    assert failed_state.turn_request.status == "failed"
    assert response.status_code == 429
    assert _extract_chat_session_id(response.text) == start_result.chat_session.id
    repository = client.app.state.chat_repository
    messages = repository.list_messages_for_chat(
        chat_session_id=start_result.chat_session.id,
        client_id="client-a",
    )
    assert [message.content for message in messages] == ["First"]


def test_send_message_returns_request_in_progress_when_duplicate_request_is_still_processing(
    client, monkeypatch
):
    repository = client.app.state.chat_repository
    chat_turn_service = client.app.state.chat_turn_service
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = chat_turn_service.start_turn(
        client_id="client-a",
        request_id="duplicate-processing-request",
        chat_session_id=chat.id,
        message="Still running",
    )

    async def return_processing_state(*_args, **_kwargs):
        return start_result.turn_request_state

    def raise_if_duplicate_reprocessed(*_args, **_kwargs):
        raise AssertionError("Duplicate request should not invoke the agent.")

    _patch_harness_failure(
        monkeypatch,
        client.app.state.chat_harness,
        lambda _request: AssertionError("Duplicate request should not invoke the agent."),
    )
    monkeypatch.setattr(main, "_await_turn_request_resolution", return_processing_state)

    response = _send_message(
        client,
        {
            "message": "Still running",
            "chat_session_id": str(chat.id),
            "request_id": "duplicate-processing-request",
        },
    )

    assert response.status_code == 409
    assert "Request In Progress" in response.text
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{chat.id}")
    messages = repository.list_messages_for_chat(chat_session_id=chat.id, client_id="client-a")
    assert [message.content for message in messages] == ["Still running"]


def test_send_message_returns_409_when_chat_is_deleted_during_in_flight_send(client, monkeypatch):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    captured_request_id = "delete-during-send"

    def delete_then_reply(_request):
        repository.soft_delete_chat(chat_session_id=chat.id, client_id="client-a")
        return "Reply that should not persist"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, delete_then_reply)

    response = _send_message(
        client,
        {
            "message": "Delete me mid-flight",
            "chat_session_id": str(chat.id),
            "request_id": captured_request_id,
        },
    )
    turn_request_state = repository.get_turn_request_state(
        client_id="client-a",
        request_id=captured_request_id,
    )

    assert response.status_code == 409
    assert "Chat No Longer Available" in response.text
    assert response.headers["HX-Push-Url"] == "/chat-start"
    assert turn_request_state is not None
    assert turn_request_state.turn_request.status == "conflicted"
    assert turn_request_state.user_message.content == "Delete me mid-flight"
    assert turn_request_state.assistant_message is None


def test_send_message_replays_duplicate_conflicted_request_without_reprocessing(client, monkeypatch):
    repository = client.app.state.chat_repository
    chat_turn_service = client.app.state.chat_turn_service
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    fallback_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    target_chat = repository.create_chat(client_id="client-a", title="Chat 2")

    start_result = chat_turn_service.start_turn(
        client_id="client-a",
        request_id="duplicate-conflicted-request",
        chat_session_id=target_chat.id,
        message="Archive me mid-flight",
    )
    repository.archive_chat(chat_session_id=target_chat.id, client_id="client-a")
    conflicted_state = chat_turn_service.complete_turn(
        client_id="client-a",
        request_id="duplicate-conflicted-request",
        assistant_content="This should not persist",
    )

    def raise_if_conflict_reprocessed(*_args, **_kwargs):
        raise AssertionError("Duplicate replay should not invoke the agent.")

    _patch_harness_failure(
        monkeypatch,
        client.app.state.chat_harness,
        lambda _request: AssertionError("Duplicate replay should not invoke the agent."),
    )

    response = _send_message(
        client,
        {
            "message": "Archive me mid-flight",
            "chat_session_id": str(target_chat.id),
            "request_id": "duplicate-conflicted-request",
        },
    )

    assert start_result.outcome == "started"
    assert conflicted_state.turn_request.status == "conflicted"
    assert response.status_code == 409
    assert "Chat No Longer Available" in response.text
    assert response.headers["HX-Push-Url"].endswith(f"/chats/{fallback_chat.id}")
    assert _extract_chat_session_id(response.text) == fallback_chat.id


def test_send_message_returns_409_when_chat_is_archived_during_in_flight_send(client, monkeypatch):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    captured_request_id = "archive-during-send"

    def archive_then_reply(_request):
        repository.archive_chat(chat_session_id=chat.id, client_id="client-a")
        return "Reply that should not persist"

    _patch_harness_reply(monkeypatch, client.app.state.chat_harness, archive_then_reply)

    response = _send_message(
        client,
        {
            "message": "Archive me mid-flight",
            "chat_session_id": str(chat.id),
            "request_id": captured_request_id,
        },
    )
    turn_request_state = repository.get_turn_request_state(
        client_id="client-a",
        request_id=captured_request_id,
    )

    assert response.status_code == 409
    assert "Chat No Longer Available" in response.text
    assert response.headers["HX-Push-Url"] == "/chat-start"
    assert turn_request_state is not None
    assert turn_request_state.turn_request.status == "conflicted"
    assert turn_request_state.turn_request.failure_code == "chat_unavailable"
    assert turn_request_state.user_message.content == "Archive me mid-flight"
    assert turn_request_state.assistant_message is None


def test_send_message_returns_409_when_chat_is_archived_during_in_flight_failure(
    client, monkeypatch
):
    repository = client.app.state.chat_repository
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    captured_request_id = "archive-during-failure"

    def archive_then_raise(_request):
        repository.archive_chat(chat_session_id=chat.id, client_id="client-a")
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic archive failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, archive_then_raise)

    response = _send_message(
        client,
        {
            "message": "Archive me before failure finalization",
            "chat_session_id": str(chat.id),
            "request_id": captured_request_id,
        },
    )
    turn_request_state = repository.get_turn_request_state(
        client_id="client-a",
        request_id=captured_request_id,
    )

    assert response.status_code == 409
    assert "Chat No Longer Available" in response.text
    assert response.headers["HX-Push-Url"] == "/chat-start"
    assert turn_request_state is not None
    assert turn_request_state.turn_request.status == "conflicted"
    assert turn_request_state.turn_request.failure_code == "chat_unavailable"
    assert turn_request_state.assistant_message is None


def test_send_message_first_message_failure_still_returns_created_chat_session_id(
    client, monkeypatch
):
    def raise_rate_limit(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic first-message failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_rate_limit)

    response = _send_message(client, {"message": "First"})

    assert response.status_code == 429
    chat_session_id = _extract_chat_session_id(response.text)

    repository = client.app.state.chat_repository
    client_id = client.cookies.get(CLIENT_ID_COOKIE_NAME)
    chats = repository.list_visible_chats(client_id=client_id)
    messages = repository.list_messages_for_chat(
        chat_session_id=chat_session_id, client_id=client_id
    )

    assert len(chats) == 1
    assert chats[0].id == chat_session_id
    assert [message.role for message in messages] == ["user"]
    assert [message.content for message in messages] == ["First"]


def test_send_message_returns_service_unavailable_html_when_harness_is_missing(client):
    del client.app.state.chat_harness_registry
    del client.app.state.chat_harness

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_returns_service_unavailable_html_when_storage_is_missing(client):
    del client.app.state.chat_repository

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is temporarily unavailable. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_returns_startup_message_when_startup_is_incomplete(client):
    client.app.state.startup_complete = False

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "The chat service is still starting up. Please try again shortly." in response.text
    assert "error-message" in response.text


def test_send_message_offloads_blocking_harness_call_from_event_loop(client, monkeypatch):
    captured = {"calls": []}

    def fake_run_events(chat_request):
        captured["request"] = chat_request
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text="Hello from thread",
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            sequence=1,
        )

    async def fake_to_thread(func, *args, **kwargs):
        captured["calls"].append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr(client.app.state.chat_harness, "run_events", fake_run_events)
    monkeypatch.setattr(main.asyncio, "to_thread", fake_to_thread)

    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 200
    assert captured["calls"][1][0].__name__ == "execute_started_turn"
    assert captured["calls"][1][2]["start_result"].turn_request_state is not None
    assert captured["calls"][1][2]["message"] == "Hi"
    assert captured["request"].message == "Hi"
    assert captured["request"].conversation_history == ()
    assert "Hello from thread" in response.text


def test_send_message_uses_chat_bound_harness_for_follow_up_send(client, monkeypatch):
    class FakeAltHarness:
        @property
        def identity(self):
            return ChatHarnessIdentity(
                key="fake-alt",
                display_name="Alt Bot",
                model_display_name="Alt Model",
            )

        def run_events(self, request):
            yield ChatHarnessEvent(
                event_type="output_text",
                output_text=f"alt:{request.message}",
                sequence=0,
            )
            yield ChatHarnessEvent(
                event_type="completed",
                sequence=1,
            )

    alt_harness = FakeAltHarness()
    client.app.state.chat_harness_registry = HarnessRegistry(
        {
            "openai": client.app.state.chat_harness,
            "fake-alt": alt_harness,
        },
        default_key="openai",
    )
    client.app.state.chat_turn_service = ChatTurnService(
        client.app.state.chat_repository,
        client.app.state.chat_harness_registry,
    )
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    bound_chat = client.app.state.chat_repository.create_chat(
        client_id="client-a",
        title="Bound chat",
        harness_key="fake-alt",
    )

    def raise_if_default_harness_used(_request):
        raise AssertionError("Follow-up send should resolve the persisted chat binding.")

    _patch_harness_failure(
        monkeypatch,
        client.app.state.chat_harness,
        lambda _request: AssertionError("Follow-up send should resolve the persisted chat binding."),
    )

    response = _send_message(
        client,
        {
            "message": "Hello from alt",
            "chat_session_id": str(bound_chat.id),
        },
    )

    assert response.status_code == 200
    assert "alt:Hello from alt" in response.text


def test_send_message_returns_503_when_chat_binding_cannot_be_resolved(client):
    client.cookies.set(CLIENT_ID_COOKIE_NAME, "client-a")
    broken_chat = client.app.state.chat_repository.create_chat(
        client_id="client-a",
        title="Broken binding",
        harness_key="missing",
    )

    response = _send_message(
        client,
        {
            "message": "Hello from broken binding",
            "chat_session_id": str(broken_chat.id),
            "request_id": "broken-binding-request",
        },
    )
    turn_request_state = client.app.state.chat_repository.get_turn_request_state(
        client_id="client-a",
        request_id="broken-binding-request",
    )

    assert response.status_code == 503
    assert "Service Unavailable" in response.text
    assert "configured chat harness is not available" in response.text
    assert turn_request_state is not None
    assert turn_request_state.turn_request.status == "failed"
    assert turn_request_state.turn_request.failure_code == "harness_unavailable"


def test_send_message_rejects_blank_messages(client):
    response = _send_message(client, {"message": "   "})

    assert response.status_code == 400
    assert "Invalid Input" in response.text
    assert "Message cannot be empty" in response.text


def test_send_message_requires_message_field(client):
    response = _send_message(client, {})

    assert response.status_code == 400
    assert "Invalid Input" in response.text
    assert "Message cannot be empty" in response.text


def test_send_message_validation_error_escapes_html(client, monkeypatch):
    def raise_value_error(_request):
        return ValueError("<b>bad input</b>")

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_value_error)
    response = _send_message(client, {"message": "Hi"})

    assert response.status_code == 400
    assert "&lt;b&gt;bad input&lt;/b&gt;" in response.text
    assert "<b>bad input</b>" not in response.text


def test_send_message_handles_rate_limit_failure(client, monkeypatch):
    def raise_rate_limit(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic rate-limit failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_rate_limit)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 429
    assert "Rate Limit Exceeded" in result.text
    assert 'class="message-body"' in result.text


def test_send_message_handles_normalized_harness_failure(client, monkeypatch):
    def raise_rate_limit_from_harness(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="rate_limited",
                message="busy",
                retryable=True,
                detail="synthetic test failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_rate_limit_from_harness)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 429
    assert "Rate Limit Exceeded" in result.text


def test_send_message_handles_authentication_failure(client, monkeypatch):
    def raise_auth_error(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="authentication_failed",
                message="auth failed",
                retryable=False,
                detail="synthetic authentication failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_auth_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 401
    assert "Authentication Error" in result.text


def test_send_message_handles_connection_failure(client, monkeypatch):
    def raise_connection_error(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="connection_error",
                message="conn",
                retryable=True,
                detail="synthetic connection failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_connection_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 503
    assert "Connection Error" in result.text


def test_send_message_handles_timeout_failure(client, monkeypatch):
    def raise_timeout_error(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="timeout",
                message="timeout",
                retryable=True,
                detail="synthetic timeout failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_timeout_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 504
    assert "Request Timeout" in result.text


def test_send_message_handles_invalid_request_failure(client, monkeypatch):
    def raise_bad_request_error(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="invalid_request",
                message="bad request",
                retryable=False,
                detail="synthetic invalid-request failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_bad_request_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 502
    assert "AI Service Error" in result.text


def test_send_message_handles_provider_error_failure(client, monkeypatch):
    def raise_api_error(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="provider_error",
                message="api failed",
                retryable=True,
                detail="synthetic provider failure",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_api_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 500
    assert "AI Service Error" in result.text


def test_send_message_handles_empty_response_failure(client, monkeypatch):
    def raise_empty_model_response(_request):
        return ChatHarnessExecutionError(
            ChatHarnessFailure(
                code="empty_response",
                message="empty response",
                retryable=False,
                detail="AI response did not include any text content",
            )
        )

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_empty_model_response)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 502
    assert "AI Service Error" in result.text
    assert "empty response" in result.text


def test_send_message_renders_mixed_text_and_code_without_paragraph_wrapping(client, monkeypatch):
    _patch_harness_reply(
        monkeypatch,
        client.app.state.chat_harness,
        lambda _request: "Example:\n```python\nprint('ok')\n```\nDone.",
    )

    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 200
    assert "<pre" in result.text
    assert "language-python" in result.text
    assert "<p><pre" not in result.text
    assert "Example:" in result.text
    assert "Done." in result.text


def test_send_message_handles_runtime_error_without_except_typeerror(client, monkeypatch):
    def raise_runtime_error(_request):
        return RuntimeError("boom")

    _patch_harness_failure(monkeypatch, client.app.state.chat_harness, raise_runtime_error)
    result = _send_message(client, {"message": "Hi"})

    assert result.status_code == 500
    assert "Unexpected Error" in result.text
    assert "Sorry, something went wrong. Please try again." in result.text
    assert "boom" not in result.text
    assert "do not inherit from BaseException" not in result.text


def test_get_chat_harness_raises_503_when_harness_is_unavailable(client):
    del client.app.state.chat_harness_registry
    del client.app.state.chat_harness

    with pytest.raises(HTTPException) as exc_info:
        main._get_chat_harness(types.SimpleNamespace(app=client.app))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Chat harness unavailable"


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


def test_create_app_defers_logging_and_harness_init_until_startup(monkeypatch):
    calls = {"init_logging": 0, "registry_builder": 0}

    class FakeHarness:
        def __init__(self):
            self.model = "gpt-5-mini"

        @property
        def identity(self):
            return ChatHarnessIdentity(
                key="fake-harness",
                display_name="Fake Bot",
                model_display_name="Fake Model",
            )

        def run(self, _request):
            return types.SimpleNamespace(output_text="unused")

    class FakeRegistry:
        def __init__(self):
            self._harness = FakeHarness()

        def default(self):
            return self._harness

    def fake_init_logging():
        calls["init_logging"] += 1

    def fake_build_chat_harness_registry(_settings):
        calls["registry_builder"] += 1
        return FakeRegistry()

    monkeypatch.setattr(main, "build_chat_harness_registry", fake_build_chat_harness_registry)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    app = main.create_app()
    assert calls == {"init_logging": 0, "registry_builder": 0}

    with TestClient(app) as startup_client:
        assert calls == {"init_logging": 1, "registry_builder": 1}
        assert startup_client.app.state.chat_harness.identity.display_name == "Fake Bot"
        assert startup_client.app.state.chat_harness.model == "gpt-5-mini"
        assert startup_client.app.state.chat_harness_registry.default().identity.key == "fake-harness"


def test_create_app_fails_with_clear_message_when_openai_key_missing(monkeypatch):
    def fake_init_logging():
        return None

    class NeverCalledAgent:
        def __init__(self, api_key):
            raise AssertionError("OpenAIAgent should not be constructed without OPENAI_API_KEY")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(main, "load_project_env", lambda: False)
    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setattr(
        main,
        "build_chat_harness_registry",
        lambda _settings: (_ for _ in ()).throw(AssertionError("Registry should not be built")),
    )

    app = main.create_app()
    expected = (
        "Startup diagnostics failed: OPENAI_API_KEY: "
        "Missing required environment variable OPENAI_API_KEY"
    )
    with pytest.raises(StartupDiagnosticsError, match=expected):
        with TestClient(app):
            pass


def test_create_app_fails_with_clear_message_when_default_harness_key_is_unknown(monkeypatch):
    def fake_init_logging():
        return None

    monkeypatch.setattr(main, "init_logging", fake_init_logging)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DEFAULT_CHAT_HARNESS_KEY", "missing")

    app = main.create_app()
    expected = (
        "Startup diagnostics failed: harness_initialization: "
        "Failed to initialize the chat harness. Unknown default chat harness key 'missing'."
    )
    with pytest.raises(StartupDiagnosticsError, match=re.escape(expected)):
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
