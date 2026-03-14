import types

import httpx
import openai
import pytest

from agents.openai_agent import OpenAIAgent


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
    assert captured["model"] == "gpt-4o-mini"
    assert captured["timeout"] == 30
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["role"] == "user"
    assert "Lucky is a cockapoo dog." in captured["messages"][1]["content"]
    assert captured["messages"][1]["content"].endswith("Hello there")


def test_process_message_rejects_blank_input():
    agent = OpenAIAgent(api_key="test-key")

    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.process_message("   ")


def test_display_name_and_known_model_display_name():
    agent = OpenAIAgent(api_key="test-key", model="gpt-4o")

    assert agent.display_name == "PodcastBot"
    assert agent.model_display_name == "GPT-4o"


def test_unknown_model_display_name_falls_back_to_model():
    agent = OpenAIAgent(api_key="test-key", model="my-custom-model")

    assert agent.model_display_name == "my-custom-model"


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
