from persistence import ChatRepository, bootstrap_database


def test_chat_repository_round_trips_chats_and_messages(tmp_path):
    client_id = "client-a"
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    chat = repository.create_chat(client_id=client_id, title="Chat 1")
    first_message = repository.create_message(
        chat_session_id=chat.id,
        client_id=client_id,
        role="user",
        content="Hello",
    )
    second_message = repository.create_message(
        chat_session_id=chat.id,
        client_id=client_id,
        role="assistant",
        content="Hi there",
    )

    loaded_chat = repository.get_chat(
        chat_session_id=chat.id,
        client_id=client_id,
    )
    messages = repository.list_messages_for_chat(
        chat_session_id=chat.id,
        client_id=client_id,
    )

    assert loaded_chat is not None
    assert loaded_chat.title == "Chat 1"
    assert [message.id for message in messages] == [first_message.id, second_message.id]
    assert [message.position for message in messages] == [0, 1]
    assert [message.role for message in messages] == ["user", "assistant"]


def test_chat_repository_scopes_visibility_and_soft_delete(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    visible_chat = repository.create_chat(client_id="client-a", title="Visible")
    repository.create_chat(client_id="client-b", title="Other client")

    assert (
        repository.soft_delete_chat(chat_session_id=visible_chat.id, client_id="client-a") is True
    )
    assert (
        repository.soft_delete_chat(chat_session_id=visible_chat.id, client_id="client-a") is False
    )
    assert repository.get_chat(chat_session_id=visible_chat.id, client_id="client-a") is None
    assert repository.get_chat(chat_session_id=visible_chat.id, client_id="client-b") is None
    assert repository.list_visible_chats(client_id="client-a") == []
    assert [chat.title for chat in repository.list_visible_chats(client_id="client-b")] == [
        "Other client"
    ]


def test_chat_repository_persists_data_across_instances(tmp_path):
    client_id = "client-a"
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)

    first_repository = ChatRepository(db_path)
    chat = first_repository.create_chat(client_id=client_id, title="Chat 1")
    first_repository.create_message(
        chat_session_id=chat.id,
        client_id=client_id,
        role="user",
        content="Persist me",
    )

    second_repository = ChatRepository(db_path)
    chats = second_repository.list_visible_chats(client_id=client_id)
    messages = second_repository.list_messages_for_chat(
        chat_session_id=chat.id,
        client_id=client_id,
    )

    assert [item.title for item in chats] == ["Chat 1"]
    assert [message.content for message in messages] == ["Persist me"]


def test_chat_repository_generates_next_default_title_per_client(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    assert repository.next_default_chat_title(client_id="client-a") == "Chat 1"
    repository.create_chat(
        client_id="client-a", title=repository.next_default_chat_title(client_id="client-a")
    )
    repository.create_chat(
        client_id="client-b", title=repository.next_default_chat_title(client_id="client-b")
    )

    assert repository.next_default_chat_title(client_id="client-a") == "Chat 2"
    assert repository.next_default_chat_title(client_id="client-b") == "Chat 2"


def test_chat_repository_start_turn_uses_default_title_helper(monkeypatch, tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    monkeypatch.setattr(
        repository,
        "_next_default_chat_title",
        lambda _connection, *, client_id: f"Seeded title for {client_id}",
    )

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-title-seam",
        chat_session_id=None,
        message="Hello",
    )

    assert start_result.outcome == "started"
    assert start_result.chat_session is not None
    assert start_result.chat_session.title == "Seeded title for client-a"


def test_chat_repository_keeps_default_title_sequence_after_delete_and_archive(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    first_chat = repository.create_chat(
        client_id="client-a", title=repository.next_default_chat_title(client_id="client-a")
    )
    second_chat = repository.create_chat(
        client_id="client-a", title=repository.next_default_chat_title(client_id="client-a")
    )

    assert repository.soft_delete_chat(chat_session_id=first_chat.id, client_id="client-a") is True
    assert repository.archive_chat(chat_session_id=second_chat.id, client_id="client-a") is True
    assert repository.next_default_chat_title(client_id="client-a") == "Chat 3"


def test_chat_repository_hides_archived_chats_from_visible_queries(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    archived_chat = repository.create_chat(client_id="client-a", title="Archive me")
    visible_chat = repository.create_chat(client_id="client-a", title="Keep me")

    assert repository.archive_chat(chat_session_id=archived_chat.id, client_id="client-a") is True
    assert repository.archive_chat(chat_session_id=archived_chat.id, client_id="client-a") is False
    assert repository.get_chat(chat_session_id=archived_chat.id, client_id="client-a") is None
    assert [chat.title for chat in repository.list_visible_chats(client_id="client-a")] == [
        "Keep me"
    ]
    assert (
        repository.list_messages_for_chat(chat_session_id=archived_chat.id, client_id="client-a")
        == []
    )
    assert repository.get_chat(chat_session_id=visible_chat.id, client_id="client-a") is not None


def test_chat_repository_rejects_messages_for_missing_or_hidden_chat(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.soft_delete_chat(chat_session_id=chat.id, client_id="client-a")

    try:
        repository.create_message(
            chat_session_id=chat.id,
            client_id="client-a",
            role="user",
            content="Should fail",
        )
    except LookupError as exc:
        assert str(chat.id) in str(exc)
    else:  # pragma: no cover - defensive for a required error path
        raise AssertionError("Expected LookupError when appending to a deleted chat.")


def test_chat_repository_replays_duplicate_processing_turn_request_without_new_writes(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-1",
        chat_session_id=None,
        message="Hello",
    )
    duplicate_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-1",
        chat_session_id=None,
        message="Hello again",
    )

    assert start_result.outcome == "started"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "processing"
    assert duplicate_result.turn_request_state.user_message.content == "Hello"
    assert duplicate_result.turn_request_state.assistant_message is None
    assert [chat.title for chat in repository.list_visible_chats(client_id="client-a")] == ["Chat 1"]
    assert [
        message.content
        for message in repository.list_messages_for_chat(
            chat_session_id=start_result.chat_session.id,
            client_id="client-a",
        )
    ] == ["Hello"]


def test_chat_repository_replays_duplicate_failed_turn_request_state(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-2",
        chat_session_id=None,
        message="Hello",
    )
    failed_state = repository.finalize_turn_failure(
        client_id="client-a",
        request_id="request-2",
        failure_code="rate_limited",
    )
    duplicate_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-2",
        chat_session_id=None,
        message="Should replay failure",
    )

    assert start_result.outcome == "started"
    assert failed_state.turn_request.status == "failed"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.turn_request_state is not None
    assert duplicate_result.turn_request_state.turn_request.status == "failed"
    assert duplicate_result.turn_request_state.turn_request.failure_code == "rate_limited"
    assert duplicate_result.turn_request_state.user_message.content == "Hello"
    assert duplicate_result.turn_request_state.assistant_message is None


def test_chat_repository_replays_duplicate_conflicted_turn_request_state(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-3",
        chat_session_id=chat.id,
        message="Archive me",
    )
    assert repository.archive_chat(chat_session_id=chat.id, client_id="client-a") is True
    conflicted_state = repository.finalize_turn_success(
        client_id="client-a",
        request_id="request-3",
        assistant_content="This should not persist",
    )
    duplicate_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-3",
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
    assert duplicate_result.turn_request_state.user_message.content == "Archive me"
    assert duplicate_result.turn_request_state.assistant_message is None


def test_chat_repository_marks_failed_turn_conflicted_when_chat_is_archived_mid_flight(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-4",
        chat_session_id=chat.id,
        message="Keep the user turn",
    )
    assert repository.archive_chat(chat_session_id=chat.id, client_id="client-a") is True
    conflicted_state = repository.finalize_turn_failure(
        client_id="client-a",
        request_id="request-4",
        failure_code="rate_limited",
    )

    assert start_result.outcome == "started"
    assert conflicted_state.turn_request.status == "conflicted"
    assert conflicted_state.turn_request.failure_code == "chat_unavailable"
    assert conflicted_state.user_message.content == "Keep the user turn"
    assert conflicted_state.assistant_message is None
