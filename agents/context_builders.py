from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .chat_harness import ChatHarnessContext, ChatHarnessRequest, ContextMessage


@runtime_checkable
class ChatContextBuilder(Protocol):
    """Harness-owned builder that turns a request into model-facing context."""

    def build(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        """Build model-facing context from the normalized harness request."""


@dataclass(frozen=True)
class DefaultContextBuilder:
    """Default transcript-based builder for harnesses that use prompt templates."""

    system_prompt: str
    user_context: str | None = None
    builder_name: str = "default_transcript"

    def build(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        latest_user_message = request.message
        rendered_user_context = (self.user_context or "").strip()
        if rendered_user_context:
            latest_user_message = f"{rendered_user_context}\n\n{latest_user_message}"

        messages = [ContextMessage(role="system", content=self.system_prompt)]
        for turn in request.transcript:
            messages.append(ContextMessage(role=turn.role, content=turn.content))
        messages.append(ContextMessage(role="user", content=latest_user_message))
        return ChatHarnessContext(messages=tuple(messages), metadata={"builder": self.builder_name})
