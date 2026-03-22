from __future__ import annotations

from dataclasses import dataclass

from agents.harness_registry import HarnessRegistry, HarnessResolutionError
from agents.chat_harness import ChatHarness
from persistence.db import DEFAULT_CHAT_HARNESS_KEY
from persistence.repository import ChatRepository, ChatSession, ChatTurnRequestState, StartTurnRequestResult


@dataclass(frozen=True)
class FailurePresentation:
    title: str
    body: str
    status_code: int
    log_event: str


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
    "bad_request": FailurePresentation(
        title="AI Service Error",
        body="The AI service rejected the request. Please try again later.",
        status_code=502,
        log_event="chat.invalid_request",
    ),
    "api_error": FailurePresentation(
        title="AI Service Error",
        body="The AI service encountered an error. Please try again later.",
        status_code=500,
        log_event="chat.provider_error",
    ),
    "empty_model_response": FailurePresentation(
        title="AI Service Error",
        body="The AI service returned an empty response. Please try again later.",
        status_code=502,
        log_event="chat.empty_response",
    ),
    "harness_unavailable": FailurePresentation(
        title="Service Unavailable",
        body="The configured chat harness is not available. Please try again later.",
        status_code=503,
        log_event="chat.harness_unavailable",
    ),
}


def failure_presentation(code: str) -> FailurePresentation:
    if code not in FAILURE_PRESENTATIONS:
        return FAILURE_PRESENTATIONS["unexpected_error"]
    return FAILURE_PRESENTATIONS[code]


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
