from __future__ import annotations

from dataclasses import dataclass

from persistence.repository import ChatRepository, ChatTurnRequestState, StartTurnRequestResult


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
}


def failure_presentation(code: str) -> FailurePresentation:
    if code not in FAILURE_PRESENTATIONS:
        return FAILURE_PRESENTATIONS["unexpected_error"]
    return FAILURE_PRESENTATIONS[code]


class ChatTurnService:
    """Own the idempotent chat send lifecycle and its 404/409 persistence policy."""

    def __init__(self, repository: ChatRepository):
        self._repository = repository

    def start_turn(
        self,
        *,
        client_id: str,
        request_id: str,
        chat_session_id: int | None,
        message: str,
    ) -> StartTurnRequestResult:
        return self._repository.start_turn_request(
            client_id=client_id,
            request_id=request_id,
            chat_session_id=chat_session_id,
            message=message,
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
