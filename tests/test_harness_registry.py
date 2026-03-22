from pathlib import Path

import pytest

from agents.chat_harness import ChatHarness, ChatHarnessEvent, ChatHarnessIdentity, ChatHarnessRequest
from agents.harness_registry import HarnessRegistry, HarnessResolutionError, build_chat_harness_registry
from utils.settings import RuntimeSettings


class FakeHarness(ChatHarness):
    def __init__(
        self,
        key: str,
        *,
        provider_name: str | None = None,
        version: str | None = None,
    ) -> None:
        self._identity = ChatHarnessIdentity(
            key=key,
            display_name=f"{key} display",
            model_display_name=f"{key} model",
            provider_name=provider_name,
            version=version,
        )

    @property
    def identity(self) -> ChatHarnessIdentity:
        return self._identity

    def run_events(self, request: ChatHarnessRequest):
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=f"{self.identity.key}:{request.message}",
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            sequence=1,
        )


def _settings(*, default_harness_key: str = "openai") -> RuntimeSettings:
    return RuntimeSettings(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        openai_prompt_name="default",
        openai_temperature=1.0,
        openai_timeout_seconds=30.0,
        chat_database_path=Path("data/chat.db"),
        cors_allowed_origins=["*"],
        cors_allow_credentials=False,
        cors_allowed_methods=["*"],
        cors_allowed_headers=["*"],
        default_harness_key=default_harness_key,
    )


def test_harness_registry_requires_at_least_one_harness():
    with pytest.raises(ValueError, match="requires at least one harness"):
        HarnessRegistry({}, default_key="openai")


def test_harness_registry_rejects_unknown_default_key():
    with pytest.raises(ValueError, match="Unknown default chat harness key 'missing'"):
        HarnessRegistry({"openai": FakeHarness("openai")}, default_key="missing")


def test_harness_registry_returns_default_and_required_harness():
    default_harness = FakeHarness("openai", provider_name="openai")
    alt_harness = FakeHarness("fake-alt", provider_name="fake-provider")
    registry = HarnessRegistry(
        {"openai": default_harness, "fake-alt": alt_harness},
        default_key="openai",
    )

    assert registry.default() is default_harness
    assert registry.get("fake-alt") is alt_harness
    assert registry.require("fake-alt") is alt_harness
    assert registry.get("missing") is None


def test_harness_registry_require_raises_for_unknown_key():
    registry = HarnessRegistry({"openai": FakeHarness("openai")}, default_key="openai")

    with pytest.raises(HarnessResolutionError, match="Unknown chat harness key 'missing'"):
        registry.require("missing")


def test_harness_registry_resolve_binding_rejects_version_mismatch():
    registry = HarnessRegistry(
        {"fake-alt": FakeHarness("fake-alt", version="v2")},
        default_key="fake-alt",
    )

    with pytest.raises(HarnessResolutionError, match="does not match version 'v1'"):
        registry.resolve_binding("fake-alt", version="v1")


def test_build_chat_harness_registry_uses_settings_default_key(monkeypatch):
    captured = {}

    class StubOpenAIHarness(FakeHarness):
        def __init__(self, **kwargs):
            captured.update(kwargs)
            super().__init__("openai", provider_name="openai")
            self.model = kwargs["model"]
            self.prompt_name = kwargs["prompt_name"]

    monkeypatch.setattr("agents.harness_registry.OpenAIAgent", StubOpenAIHarness)

    registry = build_chat_harness_registry(_settings(default_harness_key="openai"))
    default_harness = registry.default()

    assert registry.default_key == "openai"
    assert default_harness.identity.key == "openai"
    assert default_harness.identity.provider_name == "openai"
    assert captured == {
        "api_key": "test-key",
        "model": "gpt-5-mini",
        "prompt_name": "default",
        "temperature": 1.0,
        "timeout": 30.0,
    }
