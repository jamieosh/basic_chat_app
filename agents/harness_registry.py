from __future__ import annotations

from typing import TYPE_CHECKING

from .anthropic_agent import AnthropicAgent
from .chat_harness import ChatHarness
from .openai_agent import OpenAIAgent

if TYPE_CHECKING:
    from utils.settings import RuntimeSettings


class HarnessResolutionError(LookupError):
    """Raised when a requested harness binding cannot be resolved."""


class HarnessRegistry:
    """Resolve harness instances behind stable registry keys."""

    def __init__(self, harnesses: dict[str, ChatHarness], *, default_key: str):
        if not harnesses:
            raise ValueError("Harness registry requires at least one harness.")
        if default_key not in harnesses:
            raise ValueError(f"Unknown default chat harness key '{default_key}'.")

        self._harnesses = dict(harnesses)
        self._default_key = default_key

    @property
    def default_key(self) -> str:
        return self._default_key

    def get(self, key: str) -> ChatHarness | None:
        return self._harnesses.get(key)

    def require(self, key: str) -> ChatHarness:
        harness = self.get(key)
        if harness is None:
            raise HarnessResolutionError(f"Unknown chat harness key '{key}'.")
        return harness

    def resolve_binding(self, key: str, version: str | None = None) -> ChatHarness:
        harness = self.require(key)
        if version is not None and harness.identity.version != version:
            raise HarnessResolutionError(
                f"Chat harness '{key}' does not match version '{version}'."
            )
        return harness

    def default(self) -> ChatHarness:
        return self.require(self._default_key)


def build_chat_harness_registry(settings: RuntimeSettings) -> HarnessRegistry:
    openai_harness = OpenAIAgent(
        api_key=settings.openai_api_key or "",
        model=settings.openai_model,
        prompt_name=settings.openai_prompt_name,
        temperature=settings.openai_temperature,
        timeout=settings.openai_timeout_seconds,
    )
    anthropic_harness = AnthropicAgent(
        api_key=settings.anthropic_api_key or "",
        model=settings.anthropic_model,
        prompt_name=settings.anthropic_prompt_name,
        temperature=settings.anthropic_temperature,
        timeout=settings.anthropic_timeout_seconds,
        max_tokens=settings.anthropic_max_tokens,
    )
    return HarnessRegistry(
        {
            openai_harness.identity.key: openai_harness,
            anthropic_harness.identity.key: anthropic_harness,
        },
        default_key=settings.default_harness_key,
    )
