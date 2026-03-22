from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from collections.abc import Iterator, Sequence

if TYPE_CHECKING:
    from .context_builders import ChatContextBuilder


FailureCode = Literal[
    "rate_limited",
    "authentication_failed",
    "timeout",
    "connection_error",
    "invalid_request",
    "provider_error",
    "empty_response",
    "unexpected_error",
]

EventType = Literal["output_text", "completed", "failed"]
ContextMessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ConversationTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class ContextMessage:
    role: ContextMessageRole
    content: str


@dataclass(frozen=True)
class ChatHarnessContext:
    messages: tuple[ContextMessage, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class ChatHarnessIdentity:
    key: str
    display_name: str
    model_display_name: str
    provider_name: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class ChatHarnessCapabilities:
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_context_builders: bool = False


@dataclass(frozen=True)
class ChatHarnessObservability:
    model: str | None = None
    provider: str | None = None
    request_id: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatHarnessFailure:
    code: FailureCode
    message: str
    retryable: bool
    detail: str | None = None


@dataclass(frozen=True)
class ChatHarnessRequest:
    message: str
    conversation_history: tuple[ConversationTurn, ...] = ()
    request_id: str | None = None
    chat_session_id: int | None = None
    client_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "conversation_history", tuple(self.conversation_history))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def transcript(self) -> tuple[ConversationTurn, ...]:
        return self.conversation_history


@dataclass(frozen=True)
class ChatHarnessResult:
    output_text: str | None = None
    finish_reason: str = "completed"
    failure: ChatHarnessFailure | None = None
    observability: ChatHarnessObservability = field(default_factory=ChatHarnessObservability)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.failure is None and not self.output_text:
            raise ValueError("Successful harness results require output_text.")
        if self.failure is not None and self.output_text is not None:
            raise ValueError("Failed harness results cannot include output_text.")


@dataclass(frozen=True)
class ChatHarnessEvent:
    event_type: EventType
    output_text: str | None = None
    failure: ChatHarnessFailure | None = None
    observability: ChatHarnessObservability = field(default_factory=ChatHarnessObservability)
    sequence: int = 0
    finish_reason: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.event_type == "output_text":
            if self.output_text is None:
                raise ValueError("Output events require output_text.")
            if self.failure is not None:
                raise ValueError("Output events cannot include failures.")
            if self.finish_reason is not None:
                raise ValueError("Output events cannot include finish_reason.")
        elif self.event_type == "completed":
            if self.failure is not None:
                raise ValueError("Completed events cannot include failures.")
            if self.finish_reason is None:
                object.__setattr__(self, "finish_reason", "completed")
        elif self.event_type == "failed":
            if self.failure is None:
                raise ValueError("Failed events require a failure.")
            if self.output_text is not None:
                raise ValueError("Failed events cannot include output_text.")
            if self.finish_reason is not None:
                raise ValueError("Failed events cannot include finish_reason.")


class ChatHarnessExecutionError(RuntimeError):
    """Raised when a harness fails with a normalized failure."""

    def __init__(self, failure: ChatHarnessFailure):
        self.failure = failure
        super().__init__(failure.message)


def collect_harness_events(events: Iterator[ChatHarnessEvent]) -> ChatHarnessResult:
    output_parts: list[str] = []
    terminal_result: ChatHarnessResult | None = None
    seen_terminal_event = False
    last_sequence = -1

    for event in events:
        if event.sequence <= last_sequence:
            raise ValueError("Harness events must use strictly increasing sequence numbers.")
        if seen_terminal_event:
            raise ValueError("Harness events cannot continue after a terminal event.")

        last_sequence = event.sequence
        if event.event_type == "output_text":
            output_parts.append(event.output_text or "")
            continue

        if event.event_type == "failed":
            seen_terminal_event = True
            failure = event.failure
            if failure is None:  # pragma: no cover - enforced by ChatHarnessEvent invariants
                raise ValueError("Failed events require a failure payload.")
            raise ChatHarnessExecutionError(failure)

        seen_terminal_event = True
        terminal_output = event.output_text if event.output_text is not None else "".join(output_parts)
        terminal_result = ChatHarnessResult(
            output_text=terminal_output,
            finish_reason=event.finish_reason or "completed",
            observability=event.observability,
            metadata=event.metadata,
        )

    if terminal_result is None:
        raise ValueError("Harness event streams must end with a completed or failed event.")

    return terminal_result


class ChatHarness(ABC):
    """App-facing contract for harness implementations."""

    @property
    @abstractmethod
    def identity(self) -> ChatHarnessIdentity:
        """Return stable harness identity and display metadata."""

    @property
    def capabilities(self) -> ChatHarnessCapabilities:
        return ChatHarnessCapabilities()

    @property
    def context_builder(self) -> "ChatContextBuilder | None":
        return None

    def run(self, request: ChatHarnessRequest) -> ChatHarnessResult:
        """Collect normalized events into the final non-streaming result."""
        return collect_harness_events(self.run_events(request))

    @abstractmethod
    def run_events(self, request: ChatHarnessRequest) -> Iterator[ChatHarnessEvent]:
        """Execute one harness request and yield normalized execution events."""


class BaseAgent(ChatHarness, ABC):
    """Compatibility layer for legacy process_message()-style agents.

    App-layer code should call the normalized ChatHarness methods. This shim
    exists so older agent implementations can continue to adapt into that
    contract while provider-backed harnesses migrate to native run() methods.
    """

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the display name for the agent to be shown in the header."""

    @property
    @abstractmethod
    def model_display_name(self) -> str:
        """Return a user-friendly display name for the model."""

    @property
    def identity(self) -> ChatHarnessIdentity:
        return ChatHarnessIdentity(
            key=self.__class__.__name__.lower(),
            display_name=self.display_name,
            model_display_name=self.model_display_name,
        )

    def run_events(self, request: ChatHarnessRequest) -> Iterator[ChatHarnessEvent]:
        try:
            response_text = self.process_message(
                request.message,
                request.conversation_history,
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ChatHarnessExecutionError(self.normalize_exception(exc)) from exc
        observability = ChatHarnessObservability(
            model=self.model_display_name,
            request_id=request.request_id,
        )
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=response_text,
            observability=observability,
            sequence=0,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            observability=observability,
            sequence=1,
        )

    def normalize_exception(self, exc: Exception) -> ChatHarnessFailure:
        return ChatHarnessFailure(
            code="unexpected_error",
            message="Harness execution failed.",
            retryable=False,
            detail=str(exc),
        )

    @abstractmethod
    def process_message(
        self,
        message: str,
        conversation_history: Sequence[ConversationTurn] | None = None,
    ) -> str:
        """Process a user message and return a response."""
