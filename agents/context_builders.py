from __future__ import annotations

from typing import Protocol, runtime_checkable

from .chat_harness import ChatHarnessContext, ChatHarnessRequest


@runtime_checkable
class ChatContextBuilder(Protocol):
    """Harness-owned builder that turns a request into model-facing context."""

    def build(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        """Build model-facing context from the normalized harness request."""
