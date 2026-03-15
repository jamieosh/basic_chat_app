import types

import httpx
import openai
import pytest

from agents.base_agent import ChatHarnessExecutionError, ChatHarnessRequest, ConversationTurn
from agents.openai_agent import EmptyModelResponseError, OpenAIAgent


def test_process_message_builds_prompt_and_returns_model_text():
    agent = OpenAIAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Mock reply"))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message("Hello there")

    assert reply == "Mock reply"
    assert captured["model"] == "gpt-5-mini"
    assert captured["timeout"] == 30
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["role"] == "user"
    assert captured["messages"][1]["content"] == "Hello there"
    assert "temperature" not in captured


def test_process_message_rejects_blank_input():
    agent = OpenAIAgent(api_key="test-key")

    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.process_message("   ")


def test_display_name_and_known_model_display_name():
    agent = OpenAIAgent(api_key="test-key", model="gpt-5-mini")

    assert agent.display_name == "AI Chat"
    assert agent.model_display_name == "GPT-5 Mini"


def test_unknown_model_display_name_falls_back_to_model():
    agent = OpenAIAgent(api_key="test-key", model="my-custom-model")

    assert agent.model_display_name == "my-custom-model"


def test_identity_exposes_openai_harness_metadata():
    agent = OpenAIAgent(api_key="test-key", model="gpt-5-mini")

    assert agent.identity.key == "openai"
    assert agent.identity.provider_name == "openai"
    assert agent.identity.display_name == "AI Chat"
    assert agent.identity.model_display_name == "GPT-5 Mini"


def test_process_message_uses_configured_prompt_name_temperature_and_timeout(tmp_path):
    templates_dir = tmp_path / "templates" / "prompts" / "openai"
    templates_dir.mkdir(parents=True)
    (templates_dir / "system_portable.j2").write_text("System prompt", encoding="utf-8")
    (templates_dir / "user_portable.j2").write_text("", encoding="utf-8")

    agent = OpenAIAgent(
        api_key="test-key",
        model="gpt-4o",
        prompt_name="portable",
        temperature=0.7,
        timeout=12.5,
        templates_dir=tmp_path / "templates" / "prompts",
    )
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Configured reply"))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message("Hello there")

    assert reply == "Configured reply"
    assert captured["model"] == "gpt-4o"
    assert captured["temperature"] == 0.7
    assert captured["timeout"] == 12.5
    assert captured["messages"][0]["content"] == "System prompt"


def test_run_returns_chat_harness_result_with_openai_observability():
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Harness reply"))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    result = agent.run(ChatHarnessRequest(message="Hello there", request_id="req-123"))

    assert result.output_text == "Harness reply"
    assert result.observability.provider == "openai"
    assert result.observability.model == "gpt-5-mini"
    assert result.observability.request_id == "req-123"
    assert result.observability.tags["harness_key"] == "openai"
    assert result.metadata["model_display_name"] == "GPT-5 Mini"


def test_process_message_omits_custom_temperature_for_gpt5_models():
    agent = OpenAIAgent(api_key="test-key", model="gpt-5-mini", temperature=0.2)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Mock reply"))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message("Hello there")

    assert reply == "Mock reply"
    assert captured["model"] == "gpt-5-mini"
    assert "temperature" not in captured


def test_process_message_without_context_prompt_uses_raw_user_message():
    agent = OpenAIAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="No context reply"))]
        )

    def missing_context(*_args, **_kwargs):
        raise FileNotFoundError("context missing")

    agent.prompt_manager.get_context_prompt = missing_context
    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message("Just this message")

    assert reply == "No context reply"
    assert captured["messages"][1]["content"] == "Just this message"


def test_process_message_prepends_rendered_context_when_present():
    agent = OpenAIAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Context reply"))]
        )

    agent.prompt_manager.get_context_prompt = lambda *_args, **_kwargs: "Use metric units."
    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message("How far is it?")

    assert reply == "Context reply"
    assert captured["messages"][1]["content"] == "Use metric units.\n\nHow far is it?"


def test_process_message_includes_prior_history_before_latest_user_turn():
    agent = OpenAIAgent(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="History reply"))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    reply = agent.process_message(
        "What next?",
        conversation_history=[
            ConversationTurn(role="user", content="First question"),
            ConversationTurn(role="assistant", content="First answer"),
        ],
    )

    assert reply == "History reply"
    assert [message["role"] for message in captured["messages"]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert [message["content"] for message in captured["messages"][1:]] == [
        "First question",
        "First answer",
        "What next?",
    ]


def test_default_context_prompt_is_empty_for_neutral_baseline():
    agent = OpenAIAgent(api_key="test-key")

    context = agent.prompt_manager.get_context_prompt(
        agent.prompt_name, **agent.context_template_vars
    )

    assert context.strip() == ""


def test_context_prompt_renders_only_explicit_context_sections():
    agent = OpenAIAgent(api_key="test-key")

    context = agent.prompt_manager.get_context_prompt(
        agent.prompt_name,
        domain_knowledge="Use metric units.",
        user_preferences="Prefer short replies.",
    )

    assert "Domain knowledge:" in context
    assert "Use metric units." in context
    assert "User preferences: Prefer short replies." in context


def test_process_message_raises_when_model_content_is_missing():
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=None))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    with pytest.raises(EmptyModelResponseError, match="did not include any text content"):
        agent.process_message("Hello there")


@pytest.mark.parametrize(
    ("error_factory", "expected_code"),
    [
        (
            lambda request: openai.APIConnectionError(message="conn", request=request),
            "connection_error",
        ),
        (
            lambda request: openai.RateLimitError(
                "rate limit",
                response=httpx.Response(429, request=request),
                body={},
            ),
            "rate_limited",
        ),
        (
            lambda request: openai.AuthenticationError(
                "auth failed",
                response=httpx.Response(401, request=request),
                body={},
            ),
            "authentication_failed",
        ),
        (
            lambda request: openai.APIError("api failed", request=request, body={}),
            "provider_error",
        ),
        (
            lambda request: openai.BadRequestError(
                "bad request",
                response=httpx.Response(400, request=request),
                body={},
            ),
            "invalid_request",
        ),
        (
            lambda request: openai.APITimeoutError(request=request),
            "timeout",
        ),
    ],
)
def test_run_normalizes_provider_errors(error_factory, expected_code):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    agent = _build_agent_that_raises(error_factory(request))

    with pytest.raises(ChatHarnessExecutionError) as exc_info:
        agent.run(ChatHarnessRequest(message="Hello there"))

    assert exc_info.value.failure.code == expected_code


def test_process_message_reraises_file_not_found_when_system_prompt_lookup_fails():
    agent = OpenAIAgent(api_key="test-key")

    def missing_system_prompt(*_args, **_kwargs):
        raise FileNotFoundError("system prompt missing")

    agent.prompt_manager.get_system_prompt = missing_system_prompt

    with pytest.raises(FileNotFoundError, match="system prompt missing"):
        agent.process_message("Hello there")


@pytest.mark.parametrize(
    "content",
    [
        "",
        "   ",
    ],
    ids=["empty_string", "whitespace_only"],
)
def test_process_message_raises_when_model_content_is_blank(content):
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    with pytest.raises(EmptyModelResponseError, match="empty text response"):
        agent.process_message("Hello there")


def test_process_message_raises_when_response_has_no_choices():
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(choices=[])

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    with pytest.raises(EmptyModelResponseError, match="no choices"):
        agent.process_message("Hello there")


def test_process_message_raises_when_response_has_no_message():
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=None)])

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    with pytest.raises(EmptyModelResponseError, match="missing a message"):
        agent.process_message("Hello there")


def test_process_message_raises_when_model_content_is_not_a_string():
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=["not", "text"]))]
        )

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    with pytest.raises(EmptyModelResponseError, match="non-text content"):
        agent.process_message("Hello there")


def _build_agent_that_raises(error):
    agent = OpenAIAgent(api_key="test-key")

    def fake_create(**_kwargs):
        raise error

    agent.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )
    return agent


@pytest.mark.parametrize(
    ("error_factory", "expected_type"),
    [
        (
            lambda request: openai.APIConnectionError(
                message="connection failed",
                request=request,
            ),
            openai.APIConnectionError,
        ),
        (
            lambda request: openai.RateLimitError(
                "rate limited",
                response=httpx.Response(429, request=request),
                body={},
            ),
            openai.RateLimitError,
        ),
        (
            lambda request: openai.AuthenticationError(
                "auth failed",
                response=httpx.Response(401, request=request),
                body={},
            ),
            openai.AuthenticationError,
        ),
        (
            lambda request: openai.APIError(
                "api failed",
                request=request,
                body={},
            ),
            openai.APIError,
        ),
        (
            lambda request: openai.BadRequestError(
                "bad request",
                response=httpx.Response(400, request=request),
                body={},
            ),
            openai.BadRequestError,
        ),
        (
            lambda request: openai.APITimeoutError(request=request),
            openai.APITimeoutError,
        ),
    ],
    ids=[
        "api_connection_error",
        "rate_limit_error",
        "authentication_error",
        "api_error",
        "bad_request_error",
        "api_timeout_error",
    ],
)
def test_process_message_reraises_original_openai_errors(error_factory, expected_type):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    expected_error = error_factory(request)
    agent = _build_agent_that_raises(expected_error)

    with pytest.raises(expected_type) as exc_info:
        agent.process_message("Hello there")

    assert exc_info.value is expected_error
