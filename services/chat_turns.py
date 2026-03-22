from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agents.harness_registry import HarnessRegistry, HarnessResolutionError
from agents.chat_harness import (
    ChatHarness,
    ChatHarnessExecutionError,
    ChatHarnessObservability,
    ChatHarnessRequest,
    ChatHarnessResult,
    collect_harness_events,
)
from persistence.db import DEFAULT_CHAT_HARNESS_KEY
from persistence.repository import (
    ChatRepository,
    ChatSession,
    ChatTurnRequestState,
    StartTurnRequestResult,
    conversation_turns_from_messages,
)


@dataclass(frozen=True)
class FailurePresentation:
    title: str
    body: str
    status_code: int
    log_event: str


@dataclass(frozen=True)
class ChatTurnObservability:
    harness_key: str | None = None
    harness_version: str | None = None
    provider_name: str | None = None
    model: str | None = None
    request_id: str | None = None
    failure_code: str | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", dict(self.tags))

    @classmethod
    def from_harness(
        cls,
        harness: ChatHarness,
        *,
        request_id: str | None = None,
        failure_code: str | None = None,
        model: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> ChatTurnObservability:
        return cls(
            harness_key=harness.identity.key,
            harness_version=harness.identity.version,
            provider_name=harness.identity.provider_name,
            model=model,
            request_id=request_id,
            failure_code=failure_code,
            tags={} if tags is None else tags,
        )

    def identity_metadata(self) -> dict[str, str]:
        metadata: dict[str, str] = {}
        if self.harness_key is not None:
            metadata["harness_key"] = self.harness_key
        if self.harness_version is not None:
            metadata["harness_version"] = self.harness_version
        if self.provider_name is not None:
            metadata["provider_name"] = self.provider_name
        if self.model is not None:
            metadata["model"] = self.model
        return metadata


@dataclass(frozen=True)
class ChatTurnExecutionResult:
    outcome: Literal["succeeded", "failed"]
    response_harness: ChatHarness
    turn_request_state: ChatTurnRequestState
    observability: ChatTurnObservability
    output_text: str | None = None
    failure_presentation: FailurePresentation | None = None

    def __post_init__(self) -> None:
        if self.outcome == "succeeded":
            if self.output_text is None:
                raise ValueError("Successful execution results require output_text.")
            if self.failure_presentation is not None:
                raise ValueError("Successful execution results cannot include failure_presentation.")
            return

        if self.failure_presentation is None:
            raise ValueError("Failed execution results require failure_presentation.")
        if self.output_text is not None:
            raise ValueError("Failed execution results cannot include output_text.")


FAILURE_PRESENTATIONS = {
    "rate_limited": FailurePresentation(
        title="Rate Limit Exceeded",
        body="The AI service is currently busy. Please try again in a few moments.",
        status_code=429,
        log_event="chat.rate_limited",
    ),
    "authentication_failed": FailurePresentation(
        title="Authentication Error",
        body="There's an issue with the AI service authentication. Please contact support.",
        status_code=401,
        log_event="chat.authentication_failed",
    ),
    "timeout": FailurePresentation(
        title="Request Timeout",
        body="The AI service took too long to respond. Please try again.",
        status_code=504,
        log_event="chat.timeout",
    ),
    "connection_error": FailurePresentation(
        title="Connection Error",
        body=(
            "Could not connect to the AI service. Please check your internet connection and "
            "try again."
        ),
        status_code=503,
        log_event="chat.connection_error",
    ),
    "invalid_request": FailurePresentation(
        title="AI Service Error",
        body="The AI service rejected the request. Please try again later.",
        status_code=502,
        log_event="chat.invalid_request",
    ),
    "provider_error": FailurePresentation(
        title="AI Service Error",
        body="The AI service encountered an error. Please try again later.",
        status_code=500,
        log_event="chat.provider_error",
    ),
    "empty_response": FailurePresentation(
        title="AI Service Error",
        body="The AI service returned an empty response. Please try again later.",
        status_code=502,
        log_event="chat.empty_response",
    ),
    "unexpected_error": FailurePresentation(
        title="Unexpected Error",
        body="Sorry, something went wrong. Please try again.",
        status_code=500,
        log_event="chat.unexpected_error",
    ),
    "chat_unavailable": FailurePresentation(
        title="Chat No Longer Available",
        body="This chat changed while the message was being processed. Start a new chat or pick another chat to continue.",
        status_code=409,
        log_event="chat.lifecycle_conflict",
    ),
    "harness_unavailable": FailurePresentation(
        title="Service Unavailable",
        body="The configured chat harness is not available. Please try again later.",
        status_code=503,
        log_event="chat.harness_unavailable",
    ),
}

LEGACY_FAILURE_CODE_ALIASES = {
    "bad_request": "invalid_request",
    "api_error": "provider_error",
    "empty_model_response": "empty_response",
}


def failure_presentation(code: str) -> FailurePresentation:
    normalized_code = LEGACY_FAILURE_CODE_ALIASES.get(code, code)
    if normalized_code not in FAILURE_PRESENTATIONS:
        return FAILURE_PRESENTATIONS["unexpected_error"]
    return FAILURE_PRESENTATIONS[normalized_code]


class ChatTurnService:
    """Own the idempotent chat send lifecycle and its 404/409 persistence policy."""

    def __init__(
        self,
        repository: ChatRepository,
        harness_registry: HarnessRegistry | None = None,
        *,
        default_harness_key: str = DEFAULT_CHAT_HARNESS_KEY,
    ):
        self._repository = repository
        self._harness_registry = harness_registry
        self._default_harness_key = default_harness_key

    def default_harness(self) -> ChatHarness:
        if self._harness_registry is None:
            raise HarnessResolutionError("Chat harness registry is not configured.")
        return self._harness_registry.default()

    def resolve_harness_for_chat_session(self, chat_session: ChatSession) -> ChatHarness:
        if self._harness_registry is None:
            raise HarnessResolutionError("Chat harness registry is not configured.")
        return self._harness_registry.resolve_binding(
            chat_session.harness_key,
            version=chat_session.harness_version,
        )

    def resolve_harness_for_turn_state(self, turn_state: ChatTurnRequestState) -> ChatHarness:
        if turn_state.chat_session is None:
            raise HarnessResolutionError(
                f"Turn request {turn_state.turn_request.request_id} is missing its chat session."
            )
        return self.resolve_harness_for_chat_session(turn_state.chat_session)

    def response_harness_for_turn_state(self, turn_state: ChatTurnRequestState) -> ChatHarness:
        try:
            return self.resolve_harness_for_turn_state(turn_state)
        except HarnessResolutionError:
            return self.default_harness()

    def start_turn(
        self,
        *,
        client_id: str,
        request_id: str,
        chat_session_id: int | None,
        message: str,
    ) -> StartTurnRequestResult:
        harness = self._harness_registry.default() if self._harness_registry is not None else None
        return self._repository.start_turn_request(
            client_id=client_id,
            request_id=request_id,
            chat_session_id=chat_session_id,
            message=message,
            harness_key=(
                harness.identity.key if harness is not None else self._default_harness_key
            ),
            harness_version=(harness.identity.version if harness is not None else None),
        )

    def get_turn_state(self, *, client_id: str, request_id: str) -> ChatTurnRequestState | None:
        return self._repository.get_turn_request_state(client_id=client_id, request_id=request_id)

    def build_harness_request(
        self,
        *,
        client_id: str,
        request_id: str,
        start_result: StartTurnRequestResult,
        message: str,
    ) -> ChatHarnessRequest:
        chat_session_id = None if start_result.chat_session is None else start_result.chat_session.id
        return ChatHarnessRequest(
            message=message,
            conversation_history=conversation_turns_from_messages(start_result.prior_messages),
            request_id=request_id,
            chat_session_id=chat_session_id,
            client_id=client_id,
        )

    def complete_turn(
        self,
        *,
        client_id: str,
        request_id: str,
        assistant_content: str,
    ) -> ChatTurnRequestState:
        return self._repository.finalize_turn_success(
            client_id=client_id,
            request_id=request_id,
            assistant_content=assistant_content,
        )

    def execute_harness_request(
        self,
        *,
        harness: ChatHarness,
        harness_request: ChatHarnessRequest,
    ) -> ChatHarnessResult:
        return collect_harness_events(harness.run_events(harness_request))

    def fail_turn(
        self,
        *,
        client_id: str,
        request_id: str,
        failure_code: str,
    ) -> ChatTurnRequestState:
        return self._repository.finalize_turn_failure(
            client_id=client_id,
            request_id=request_id,
            failure_code=failure_code,
        )

    def execute_started_turn(
        self,
        *,
        client_id: str,
        request_id: str,
        start_result: StartTurnRequestResult,
        message: str,
    ) -> ChatTurnExecutionResult:
        turn_request_state = start_result.turn_request_state
        if turn_request_state is None:  # pragma: no cover - defensive against repository contract
            raise RuntimeError("Turn request start result is missing its state.")

        try:
            harness = self.resolve_harness_for_turn_state(turn_request_state)
        except HarnessResolutionError:
            failed_state = self.fail_turn(
                client_id=client_id,
                request_id=request_id,
                failure_code="harness_unavailable",
            )
            return ChatTurnExecutionResult(
                outcome="failed",
                response_harness=self.default_harness(),
                turn_request_state=failed_state,
                observability=self._build_turn_observability(
                    request_id=request_id,
                    chat_session=turn_request_state.chat_session,
                    failure_code="harness_unavailable",
                ),
                failure_presentation=failure_presentation("harness_unavailable"),
            )

        harness_request = self.build_harness_request(
            client_id=client_id,
            request_id=request_id,
            start_result=start_result,
            message=message,
        )

        try:
            harness_result = self.execute_harness_request(
                harness=harness,
                harness_request=harness_request,
            )
        except ValueError:
            raise
        except ChatHarnessExecutionError as exc:
            failed_state = self.fail_turn(
                client_id=client_id,
                request_id=request_id,
                failure_code=exc.failure.code,
            )
            return ChatTurnExecutionResult(
                outcome="failed",
                response_harness=harness,
                turn_request_state=failed_state,
                observability=self._build_turn_observability(
                    request_id=request_id,
                    chat_session=turn_request_state.chat_session,
                    harness=harness,
                    harness_observability=None,
                    failure_code=exc.failure.code,
                ),
                failure_presentation=failure_presentation(exc.failure.code),
            )
        except Exception:
            failed_state = self.fail_turn(
                client_id=client_id,
                request_id=request_id,
                failure_code="unexpected_error",
            )
            return ChatTurnExecutionResult(
                outcome="failed",
                response_harness=harness,
                turn_request_state=failed_state,
                observability=self._build_turn_observability(
                    request_id=request_id,
                    chat_session=turn_request_state.chat_session,
                    harness=harness,
                    harness_observability=None,
                    failure_code="unexpected_error",
                ),
                failure_presentation=failure_presentation("unexpected_error"),
            )

        output_text = harness_result.output_text
        if output_text is None:  # pragma: no cover - enforced by ChatHarnessResult invariants
            raise RuntimeError("Harness result is missing its output text.")

        completed_state = self.complete_turn(
            client_id=client_id,
            request_id=request_id,
            assistant_content=output_text,
        )
        return ChatTurnExecutionResult(
            outcome="succeeded",
            response_harness=harness,
            turn_request_state=completed_state,
            observability=self._build_turn_observability(
                request_id=request_id,
                chat_session=turn_request_state.chat_session,
                harness=harness,
                harness_observability=harness_result.observability,
            ),
            output_text=output_text,
        )

    def _build_turn_observability(
        self,
        *,
        request_id: str,
        chat_session: ChatSession | None,
        harness: ChatHarness | None = None,
        harness_observability: ChatHarnessObservability | None = None,
        failure_code: str | None = None,
    ) -> ChatTurnObservability:
        harness_identity = None if harness is None else harness.identity
        observability = ChatTurnObservability(
            harness_key=(
                harness_identity.key
                if harness_identity is not None
                else (None if chat_session is None else chat_session.harness_key)
            ),
            harness_version=(
                harness_identity.version
                if harness_identity is not None
                else (None if chat_session is None else chat_session.harness_version)
            ),
            provider_name=(
                harness_identity.provider_name
                if harness_identity is not None
                else (None if harness_observability is None else harness_observability.provider)
            ),
            model=None if harness_observability is None else harness_observability.model,
            request_id=(
                request_id
                if harness_observability is None or harness_observability.request_id is None
                else harness_observability.request_id
            ),
            failure_code=failure_code,
            tags={} if harness_observability is None else harness_observability.tags,
        )
        return observability
