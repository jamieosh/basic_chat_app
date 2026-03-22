import json
from dataclasses import asdict

import pytest

from agents.base_agent import (
    BaseAgent,
    ChatContextBuilder,
    ChatHarness,
    ChatHarnessContext,
    ChatHarnessCapabilities,
    ChatHarnessEvent,
    ChatHarnessExecutionError,
    ChatHarnessFailure,
    ChatHarnessIdentity,
    ChatHarnessObservability,
    ChatHarnessRequest,
    ChatHarnessResult,
    ContextMessage,
    ConversationTurn,
)


class FakeHarness(BaseAgent):
    @property
    def display_name(self) -> str:
        return "Fake Harness"

    @property
    def model_display_name(self) -> str:
        return "Fake Model"

    @property
    def capabilities(self) -> ChatHarnessCapabilities:
        return ChatHarnessCapabilities(supports_streaming=True)

    def process_message(self, message: str, conversation_history=None) -> str:
        history_size = len(conversation_history or ())
        return f"{message} ({history_size})"


class EventHarness(ChatHarness):
    @property
    def identity(self) -> ChatHarnessIdentity:
        return ChatHarnessIdentity(
            key="event-harness",
            display_name="Event Harness",
            model_display_name="Event Model",
        )

    def run_events(self, request: ChatHarnessRequest):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=request.message,
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=f" ({len(request.conversation_history)})",
            sequence=1,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            observability=ChatHarnessObservability(
                model="event-model",
                request_id=request.request_id,
                tags={"surface": "events"},
            ),
            sequence=2,
            finish_reason="stop",
            metadata={"collector": "canonical"},
        )


class FailingEventHarness(ChatHarness):
    @property
    def identity(self) -> ChatHarnessIdentity:
        return ChatHarnessIdentity(
            key="failing-event-harness",
            display_name="Failing Event Harness",
            model_display_name="Event Model",
        )

    def run_events(self, request: ChatHarnessRequest):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=request.message,
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="failed",
            failure=ChatHarnessFailure(
                code="provider_error",
                message="provider failed",
                retryable=True,
                detail=f"request={request.request_id}",
            ),
            observability=ChatHarnessObservability(
                model="event-model",
                request_id=request.request_id,
            ),
            sequence=1,
            metadata={"collector": "canonical"},
        )


class FakeContextBuilder:
    def build(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        return ChatHarnessContext(
            messages=(
                ContextMessage(role="system", content="Follow the house style."),
                ContextMessage(role="user", content=request.message),
            ),
            metadata={"builder": "fake"},
        )


def test_chat_harness_models_are_json_serializable():
    failure = ChatHarnessFailure(
        code="provider_error",
        message="provider failed",
        retryable=True,
        detail="upstream 500",
    )
    result = ChatHarnessResult(
        failure=failure,
        finish_reason="failed",
        observability=ChatHarnessObservability(
            model="fake-model",
            provider="fake-provider",
            request_id="req-123",
            tags={"phase": "3"},
        ),
        metadata={"chat_id": "42"},
    )
    request = ChatHarnessRequest(
        message="Hello",
        conversation_history=[
            ConversationTurn(role="user", content="Hi"),
            ConversationTurn(role="assistant", content="Hello"),
        ],
        request_id="req-123",
        chat_session_id=42,
        client_id="client-1",
        metadata={"source": "test"},
    )

    payload = {
        "identity": asdict(
            ChatHarnessIdentity(
                key="fake",
                display_name="Fake Harness",
                model_display_name="Fake Model",
                provider_name="fake-provider",
                version="v1",
            )
        ),
        "request": asdict(request),
        "context": asdict(
            ChatHarnessContext(
                messages=[
                    ContextMessage(role="system", content="Rules"),
                    ContextMessage(role="user", content="Hello"),
                ],
                metadata={"builder": "default"},
            )
        ),
        "result": asdict(result),
        "event": asdict(
            ChatHarnessEvent(
                event_type="completed",
                output_text="Hello",
                observability=ChatHarnessObservability(
                    model="fake-model",
                    provider="fake-provider",
                    request_id="req-123",
                ),
                sequence=3,
                finish_reason="stop",
                metadata={"chat_id": "42"},
            )
        ),
    }

    encoded = json.dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["identity"]["key"] == "fake"
    assert decoded["request"]["conversation_history"][0]["role"] == "user"
    assert decoded["context"]["messages"][0]["role"] == "system"
    assert decoded["result"]["failure"]["code"] == "provider_error"
    assert decoded["result"]["observability"]["request_id"] == "req-123"
    assert decoded["event"]["finish_reason"] == "stop"


def test_chat_harness_request_exposes_transcript_alias_for_conversation_history():
    request = ChatHarnessRequest(
        message="Hello",
        conversation_history=[ConversationTurn(role="user", content="Hi")],
    )

    assert request.transcript == request.conversation_history
    assert request.transcript == (ConversationTurn(role="user", content="Hi"),)


def test_context_builder_protocol_builds_model_facing_context():
    builder: ChatContextBuilder = FakeContextBuilder()

    context = builder.build(ChatHarnessRequest(message="Hello"))

    assert context.messages == (
        ContextMessage(role="system", content="Follow the house style."),
        ContextMessage(role="user", content="Hello"),
    )
    assert context.metadata == {"builder": "fake"}


def test_base_agent_run_adapts_legacy_process_message_to_harness_result():
    harness = FakeHarness()

    result = harness.run(
        ChatHarnessRequest(
            message="Next",
            conversation_history=(ConversationTurn(role="user", content="First"),),
            request_id="req-456",
        )
    )

    assert result.output_text == "Next (1)"
    assert result.failure is None
    assert result.observability.model == "Fake Model"
    assert result.observability.request_id == "req-456"
    assert result.finish_reason == "completed"


def test_chat_harness_run_collects_final_result_from_event_stream():
    harness = EventHarness()

    result = harness.run(
        ChatHarnessRequest(
            message="Next",
            conversation_history=(ConversationTurn(role="user", content="First"),),
            request_id="req-456",
        )
    )

    assert result.output_text == "Next (1)"
    assert result.finish_reason == "stop"
    assert result.observability.model == "event-model"
    assert result.observability.request_id == "req-456"
    assert result.observability.tags == {"surface": "events"}
    assert result.metadata == {"collector": "canonical"}


def test_chat_harness_run_raises_normalized_failure_from_event_stream():
    harness = FailingEventHarness()

    with pytest.raises(ChatHarnessExecutionError) as exc_info:
        harness.run(ChatHarnessRequest(message="Next", request_id="req-456"))

    assert exc_info.value.failure.code == "provider_error"
    assert exc_info.value.failure.detail == "request=req-456"


def test_base_agent_run_events_exposes_output_and_completion_events():
    harness = FakeHarness()

    events = list(harness.run_events(ChatHarnessRequest(message="Next")))

    assert [event.event_type for event in events] == ["output_text", "completed"]
    assert events[0].output_text == "Next (0)"
    assert events[1].output_text is None
    assert events[1].finish_reason == "completed"
