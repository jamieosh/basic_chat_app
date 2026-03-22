from agents.chat_harness import ChatHarnessIdentity, ChatHarnessRequest, ChatHarnessResult
from agents.harness_registry import HarnessRegistry, HarnessResolutionError
from persistence import ChatRepository, bootstrap_database
from services import ChatTurnService


class FakeHarness:
    def __init__(self, key: str, *, version: str | None = None):
        self._identity = ChatHarnessIdentity(
            key=key,
            display_name=f"{key} display",
            model_display_name=f"{key} model",
            version=version,
        )

    @property
    def identity(self):
        return self._identity

    def run(self, request: ChatHarnessRequest) -> ChatHarnessResult:
        return ChatHarnessResult(output_text=f"{self.identity.key}:{request.message}")


def test_chat_turn_service_replays_duplicate_request_without_creating_extra_turns(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-1",
        chat_session_id=None,
        message="Hello",
    )
    completed_state = service.complete_turn(
        client_id="client-a",
        request_id="request-1",
        assistant_content="Hi there",
    )
    duplicate_result = service.start_turn(
        client_id="client-a",
        request_id="request-1",
        chat_session_id=None,
        message="Hello",
    )

    assert start_result.outcome == "started"
    assert completed_state.turn_request.status == "completed"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "completed"
    assert duplicate_result.turn_request_state.assistant_message is not None
    assert duplicate_result.turn_request_state.assistant_message.content == "Hi there"


def test_chat_turn_service_uses_registry_default_binding_for_new_chat(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    registry = HarnessRegistry({"fake-default": FakeHarness("fake-default")}, default_key="fake-default")
    service = ChatTurnService(repository, registry)

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-default-binding",
        chat_session_id=None,
        message="Hello",
    )

    assert start_result.outcome == "started"
    assert start_result.chat_session is not None
    assert start_result.chat_session.harness_key == "fake-default"
    assert service.resolve_harness_for_turn_state(start_result.turn_request_state).identity.key == "fake-default"


def test_chat_turn_service_finalize_failure_keeps_user_turn_and_marks_request_failed(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-2",
        chat_session_id=None,
        message="Hello",
    )
    failed_state = service.fail_turn(
        client_id="client-a",
        request_id="request-2",
        failure_code="rate_limited",
    )

    assert start_result.outcome == "started"
    assert failed_state.turn_request.status == "failed"
    assert failed_state.turn_request.failure_code == "rate_limited"
    assert failed_state.assistant_message is None
    assert failed_state.user_message.content == "Hello"


def test_chat_turn_service_replays_duplicate_processing_request_state(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-processing",
        chat_session_id=None,
        message="Hello",
    )
    duplicate_result = service.start_turn(
        client_id="client-a",
        request_id="request-processing",
        chat_session_id=None,
        message="Should not create a second turn",
    )

    assert start_result.outcome == "started"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "processing"
    assert duplicate_result.turn_request_state.user_message.content == "Hello"
    assert duplicate_result.turn_request_state.assistant_message is None


def test_chat_turn_service_replays_duplicate_failed_request_state(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-failed",
        chat_session_id=None,
        message="Hello",
    )
    failed_state = service.fail_turn(
        client_id="client-a",
        request_id="request-failed",
        failure_code="rate_limited",
    )
    duplicate_result = service.start_turn(
        client_id="client-a",
        request_id="request-failed",
        chat_session_id=None,
        message="Should replay failure",
    )

    assert start_result.outcome == "started"
    assert failed_state.turn_request.status == "failed"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "failed"
    assert duplicate_result.turn_request_state.turn_request.failure_code == "rate_limited"
    assert duplicate_result.turn_request_state.assistant_message is None


def test_chat_turn_service_marks_request_conflicted_when_chat_is_deleted_mid_flight(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-3",
        chat_session_id=chat.id,
        message="Delete me",
    )
    repository.soft_delete_chat(chat_session_id=chat.id, client_id="client-a")
    conflicted_state = service.complete_turn(
        client_id="client-a",
        request_id="request-3",
        assistant_content="This should not persist",
    )

    assert start_result.outcome == "started"
    assert conflicted_state.turn_request.status == "conflicted"
    assert conflicted_state.turn_request.failure_code == "chat_unavailable"
    assert conflicted_state.assistant_message is None
    assert conflicted_state.user_message.content == "Delete me"


def test_chat_turn_service_replays_duplicate_conflicted_request_state(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-conflicted",
        chat_session_id=chat.id,
        message="Archive me",
    )
    repository.archive_chat(chat_session_id=chat.id, client_id="client-a")
    conflicted_state = service.complete_turn(
        client_id="client-a",
        request_id="request-conflicted",
        assistant_content="This should not persist",
    )
    duplicate_result = service.start_turn(
        client_id="client-a",
        request_id="request-conflicted",
        chat_session_id=chat.id,
        message="Should replay conflict",
    )

    assert start_result.outcome == "started"
    assert conflicted_state.turn_request.status == "conflicted"
    assert conflicted_state.turn_request.failure_code == "chat_unavailable"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "conflicted"
    assert duplicate_result.turn_request_state.turn_request.failure_code == "chat_unavailable"
    assert duplicate_result.turn_request_state.assistant_message is None


def test_chat_turn_service_marks_request_conflicted_when_chat_is_archived_mid_flight_failure(
    tmp_path,
):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-archived-failure",
        chat_session_id=chat.id,
        message="Archive me",
    )
    repository.archive_chat(chat_session_id=chat.id, client_id="client-a")
    conflicted_state = service.fail_turn(
        client_id="client-a",
        request_id="request-archived-failure",
        failure_code="rate_limited",
    )

    assert start_result.outcome == "started"
    assert conflicted_state.turn_request.status == "conflicted"
    assert conflicted_state.turn_request.failure_code == "chat_unavailable"
    assert conflicted_state.assistant_message is None
    assert conflicted_state.user_message.content == "Archive me"


def test_chat_turn_service_rejects_missing_or_hidden_target_chat_at_request_start(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    service = ChatTurnService(repository)
    deleted_chat = repository.create_chat(client_id="client-a", title="Chat 1")
    archived_chat = repository.create_chat(client_id="client-a", title="Chat 2")
    repository.soft_delete_chat(chat_session_id=deleted_chat.id, client_id="client-a")
    repository.archive_chat(chat_session_id=archived_chat.id, client_id="client-a")

    deleted_result = service.start_turn(
        client_id="client-a",
        request_id="request-4",
        chat_session_id=deleted_chat.id,
        message="Hello",
    )
    archived_result = service.start_turn(
        client_id="client-a",
        request_id="request-5",
        chat_session_id=archived_chat.id,
        message="Hello",
    )
    missing_result = service.start_turn(
        client_id="client-a",
        request_id="request-6",
        chat_session_id=999999,
        message="Hello",
    )

    assert deleted_result.outcome == "missing"
    assert archived_result.outcome == "missing"
    assert missing_result.outcome == "missing"


def test_chat_turn_service_resolves_existing_chat_binding_from_persisted_chat(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    registry = HarnessRegistry(
        {"openai": FakeHarness("openai"), "fake-alt": FakeHarness("fake-alt", version="v2")},
        default_key="openai",
    )
    service = ChatTurnService(repository, registry)
    chat = repository.create_chat(
        client_id="client-a",
        title="Chat 1",
        harness_key="fake-alt",
        harness_version="v2",
    )

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-existing-binding",
        chat_session_id=chat.id,
        message="Hello",
    )

    assert start_result.outcome == "started"
    assert start_result.turn_request_state is not None
    assert service.resolve_harness_for_turn_state(start_result.turn_request_state).identity.key == "fake-alt"


def test_chat_turn_service_raises_for_unknown_persisted_harness_binding(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    registry = HarnessRegistry({"openai": FakeHarness("openai")}, default_key="openai")
    service = ChatTurnService(repository, registry)
    chat = repository.create_chat(client_id="client-a", title="Chat 1", harness_key="missing")

    start_result = service.start_turn(
        client_id="client-a",
        request_id="request-missing-binding",
        chat_session_id=chat.id,
        message="Hello",
    )

    assert start_result.turn_request_state is not None
    try:
        service.resolve_harness_for_turn_state(start_result.turn_request_state)
    except HarnessResolutionError as exc:
        assert "missing" in str(exc)
    else:  # pragma: no cover - defensive for required error path
        raise AssertionError("Expected HarnessResolutionError for an unknown harness key.")
