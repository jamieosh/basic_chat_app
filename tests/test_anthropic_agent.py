import types

import anthropic
import httpx
import pytest

from agents.base_agent import (
    ChatHarnessContext,
    ChatHarnessExecutionError,
    ChatHarnessRequest,
    ContextMessage,
    ConversationTurn,
)
from agents.anthropic_agent import AnthropicAgent


def test_run_builds_message_request_and_returns_model_text():
    agent = AnthropicAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Mock reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    result = agent.run(ChatHarnessRequest(message="Hello there"))

    assert result.output_text == "Mock reply"
    assert captured["model"] == "claude-sonnet-4-20250514"
    assert captured["max_tokens"] == 1024
    assert captured["temperature"] == 1.0
    assert captured["timeout"] == 30.0
    assert captured["system"]
    assert captured["messages"] == [{"role": "user", "content": "Hello there"}]


def test_run_rejects_blank_input():
    agent = AnthropicAgent(api_key="test-key")

    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.run(ChatHarnessRequest(message="   "))


def test_identity_exposes_anthropic_harness_metadata():
    agent = AnthropicAgent(api_key="test-key")

    assert agent.identity.key == "anthropic"
    assert agent.identity.provider_name == "anthropic"
    assert agent.identity.display_name == "AI Chat"
    assert agent.identity.model_display_name == "Claude Sonnet 4"


def test_capabilities_report_context_builder_support():
    agent = AnthropicAgent(api_key="test-key")

    assert agent.capabilities.supports_context_builders is True
    assert agent.capabilities.supports_tools is False
    assert agent.available_tools == ()


def test_run_uses_builder_generated_context_and_records_builder_metadata():
    agent = AnthropicAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Builder reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )
    agent._build_context = lambda _request: ChatHarnessContext(  # type: ignore[method-assign]
        messages=(
            ContextMessage(role="system", content="System rules"),
            ContextMessage(role="assistant", content="Prior reply"),
            ContextMessage(role="user", content="Built user message"),
        ),
        metadata={"builder": "test-builder"},
    )

    result = agent.run(ChatHarnessRequest(message="Hello there"))

    assert result.output_text == "Builder reply"
    assert result.metadata["context_builder"] == "test-builder"
    assert result.observability.tags["context_builder"] == "test-builder"
    assert captured["system"] == "System rules"
    assert captured["messages"] == [
        {"role": "assistant", "content": "Prior reply"},
        {"role": "user", "content": "Built user message"},
    ]


def test_run_includes_prior_history_before_latest_user_turn():
    agent = AnthropicAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="History reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    result = agent.run(
        ChatHarnessRequest(
            message="What next?",
            conversation_history=[
                ConversationTurn(role="user", content="First question"),
                ConversationTurn(role="assistant", content="First answer"),
            ],
        )
    )

    assert result.output_text == "History reply"
    assert captured["messages"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "What next?"},
    ]


def test_run_returns_chat_harness_result_with_anthropic_observability():
    agent = AnthropicAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Harness reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    result = agent.run(ChatHarnessRequest(message="Hello there", request_id="req-123"))

    assert result.output_text == "Harness reply"
    assert result.observability.provider == "anthropic"
    assert result.observability.model == "claude-sonnet-4-20250514"
    assert result.observability.request_id == "req-123"
    assert result.observability.tags["harness_key"] == "anthropic"
    assert result.observability.tags["provider_name"] == "anthropic"
    assert result.metadata["model_display_name"] == "Claude Sonnet 4"


def test_run_events_expose_output_and_completion_with_anthropic_metadata():
    agent = AnthropicAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Harness reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    events = list(agent.run_events(ChatHarnessRequest(message="Hello there", request_id="req-123")))

    assert [event.event_type for event in events] == ["output_text", "completed"]
    assert events[0].output_text == "Harness reply"
    assert events[0].observability.provider == "anthropic"
    assert events[0].observability.request_id == "req-123"
    assert events[0].observability.tags["provider_name"] == "anthropic"
    assert events[0].metadata["model_display_name"] == "Claude Sonnet 4"
    assert events[1].finish_reason == "completed"


def test_run_collects_same_final_output_as_run_events():
    agent = AnthropicAgent(api_key="test-key")
    call_count = {"count": 0}

    def fake_create(**_kwargs):
        call_count["count"] += 1
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Collected reply")]
        )

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    event_result = "".join(
        event.output_text or ""
        for event in agent.run_events(ChatHarnessRequest(message="Hello there"))
        if event.event_type == "output_text"
    )
    run_result = agent.run(ChatHarnessRequest(message="Hello there"))

    assert event_result == "Collected reply"
    assert run_result.output_text == "Collected reply"
    assert call_count["count"] == 2


def test_context_builder_preserves_default_prompt_and_transcript_order():
    agent = AnthropicAgent(api_key="test-key")

    context = agent.context_builder.build(
        ChatHarnessRequest(
            message="What next?",
            conversation_history=[
                ConversationTurn(role="user", content="First question"),
                ConversationTurn(role="assistant", content="First answer"),
            ],
        )
    )

    assert [message.role for message in context.messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert context.metadata == {"builder": "anthropic_default"}


def test_run_normalizes_missing_text_blocks_as_empty_response_failure():
    agent = AnthropicAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="tool_use", text=None)])

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )

    with pytest.raises(ChatHarnessExecutionError) as exc_info:
        agent.run(ChatHarnessRequest(message="Hello there"))

    assert exc_info.value.failure.code == "empty_response"
    assert "did not include any text content" in exc_info.value.failure.detail


@pytest.mark.parametrize(
    ("error_factory", "expected_code"),
    [
        (
            lambda request: anthropic.APIConnectionError(message="conn", request=request),
            "connection_error",
        ),
        (
            lambda request: anthropic.RateLimitError(
                "rate limit",
                response=httpx.Response(429, request=request),
                body={},
            ),
            "rate_limited",
        ),
        (
            lambda request: anthropic.AuthenticationError(
                "auth failed",
                response=httpx.Response(401, request=request),
                body={},
            ),
            "authentication_failed",
        ),
        (
            lambda request: anthropic.BadRequestError(
                "bad request",
                response=httpx.Response(400, request=request),
                body={},
            ),
            "invalid_request",
        ),
        (
            lambda request: anthropic.InternalServerError(
                "provider failed",
                response=httpx.Response(500, request=request),
                body={},
            ),
            "provider_error",
        ),
        (
            lambda request: anthropic.APITimeoutError(request=request),
            "timeout",
        ),
    ],
)
def test_run_normalizes_provider_errors(error_factory, expected_code):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    agent = _build_agent_that_raises(error_factory(request))

    with pytest.raises(ChatHarnessExecutionError) as exc_info:
        agent.run(ChatHarnessRequest(message="Hello there"))

    assert exc_info.value.failure.code == expected_code


@pytest.mark.parametrize(
    ("error_factory", "expected_type"),
    [
        (
            lambda request: anthropic.APIConnectionError(
                message="connection failed",
                request=request,
            ),
            anthropic.APIConnectionError,
        ),
        (
            lambda request: anthropic.RateLimitError(
                "rate limited",
                response=httpx.Response(429, request=request),
                body={},
            ),
            anthropic.RateLimitError,
        ),
        (
            lambda request: anthropic.AuthenticationError(
                "auth failed",
                response=httpx.Response(401, request=request),
                body={},
            ),
            anthropic.AuthenticationError,
        ),
        (
            lambda request: anthropic.BadRequestError(
                "bad request",
                response=httpx.Response(400, request=request),
                body={},
            ),
            anthropic.BadRequestError,
        ),
        (
            lambda request: anthropic.InternalServerError(
                "provider failed",
                response=httpx.Response(500, request=request),
                body={},
            ),
            anthropic.InternalServerError,
        ),
        (
            lambda request: anthropic.APITimeoutError(request=request),
            anthropic.APITimeoutError,
        ),
    ],
)
def test_process_message_reraises_original_anthropic_errors(error_factory, expected_type):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    expected_error = error_factory(request)
    agent = _build_agent_that_raises(expected_error)

    with pytest.raises(expected_type) as exc_info:
        agent.process_message("Hello there")

    assert exc_info.value is expected_error


def _build_agent_that_raises(error: Exception) -> AnthropicAgent:
    agent = AnthropicAgent(api_key="test-key")

    def fake_create(**_kwargs):
        raise error

    agent.client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=fake_create)
    )
    return agent
