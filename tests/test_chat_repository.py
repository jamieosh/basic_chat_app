from persistence import DEFAULT_PLACEHOLDER_CLIENT_ID, ChatRepository, bootstrap_database


def test_chat_repository_round_trips_chats_and_messages(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    chat = repository.create_chat(client_id=DEFAULT_PLACEHOLDER_CLIENT_ID, title="Chat 1")
    first_message = repository.create_message(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
        role="user",
        content="Hello",
    )
    second_message = repository.create_message(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
        role="assistant",
        content="Hi there",
    )

    loaded_chat = repository.get_chat(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
    )
    messages = repository.list_messages_for_chat(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
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

    assert repository.soft_delete_chat(chat_session_id=visible_chat.id, client_id="client-a") is True
    assert repository.soft_delete_chat(chat_session_id=visible_chat.id, client_id="client-a") is False
    assert repository.get_chat(chat_session_id=visible_chat.id, client_id="client-a") is None
    assert repository.get_chat(chat_session_id=visible_chat.id, client_id="client-b") is None
    assert repository.list_visible_chats(client_id="client-a") == []
    assert [chat.title for chat in repository.list_visible_chats(client_id="client-b")] == ["Other client"]


def test_chat_repository_persists_data_across_instances(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)

    first_repository = ChatRepository(db_path)
    chat = first_repository.create_chat(client_id=DEFAULT_PLACEHOLDER_CLIENT_ID, title="Chat 1")
    first_repository.create_message(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
        role="user",
        content="Persist me",
    )

    second_repository = ChatRepository(db_path)
    chats = second_repository.list_visible_chats(client_id=DEFAULT_PLACEHOLDER_CLIENT_ID)
    messages = second_repository.list_messages_for_chat(
        chat_session_id=chat.id,
        client_id=DEFAULT_PLACEHOLDER_CLIENT_ID,
    )

    assert [item.title for item in chats] == ["Chat 1"]
    assert [message.content for message in messages] == ["Persist me"]


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
