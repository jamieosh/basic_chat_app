import sqlite3

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
    assert loaded_chat.harness_key == "openai"
    assert loaded_chat.harness_version is None
    assert [message.id for message in messages] == [first_message.id, second_message.id]
    assert [message.position for message in messages] == [0, 1]
    assert [message.role for message in messages] == ["user", "assistant"]


def test_chat_repository_round_trips_explicit_harness_binding(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    chat = repository.create_chat(
        client_id="client-a",
        title="Bound chat",
        harness_key="fake-harness",
        harness_version="2026-03-22",
    )

    loaded_chat = repository.get_chat(chat_session_id=chat.id, client_id="client-a")

    assert loaded_chat is not None
    assert loaded_chat.harness_key == "fake-harness"
    assert loaded_chat.harness_version == "2026-03-22"


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
    assert start_result.chat_session.harness_key == "openai"
    assert start_result.chat_session.harness_version is None


def test_chat_repository_start_turn_persists_requested_harness_binding(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-harness-binding",
        chat_session_id=None,
        message="Hello",
        harness_key="fake-harness",
        harness_version="2026-03-22",
    )

    assert start_result.outcome == "started"
    assert start_result.chat_session is not None
    assert start_result.chat_session.harness_key == "fake-harness"
    assert start_result.chat_session.harness_version == "2026-03-22"


def test_bootstrap_database_backfills_harness_binding_for_existing_chat_sessions(tmp_path):
    db_path = tmp_path / "chat.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL CHECK(title <> ''),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                deleted_at TEXT
            );

            CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id INTEGER NOT NULL,
                position INTEGER NOT NULL CHECK(position >= 0),
                role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                UNIQUE (chat_session_id, position)
            );

            CREATE INDEX idx_chat_sessions_visible_by_client
            ON chat_sessions (client_id, archived_at, deleted_at, updated_at DESC, id DESC);

            CREATE INDEX idx_chat_messages_by_chat_position
            ON chat_messages (chat_session_id, position ASC, id ASC);

            CREATE TABLE chat_turn_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                chat_session_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('processing', 'completed', 'failed', 'conflicted')),
                user_message_id INTEGER NOT NULL,
                assistant_message_id INTEGER,
                failure_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                FOREIGN KEY (assistant_message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                UNIQUE (client_id, request_id)
            );

            CREATE INDEX idx_chat_turn_requests_by_client_status
            ON chat_turn_requests (client_id, status, updated_at DESC, id DESC);
            """
        )
        connection.execute(
            """
            INSERT INTO chat_sessions (
                client_id,
                title,
                created_at,
                updated_at,
                archived_at,
                deleted_at
            ) VALUES (?, ?, ?, ?, NULL, NULL)
            """,
            ("client-a", "Legacy chat", "2026-03-22T10:00:00+00:00", "2026-03-22T10:00:00+00:00"),
        )

    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    loaded_chat = repository.get_chat(chat_session_id=1, client_id="client-a")

    assert loaded_chat is not None
    assert loaded_chat.harness_key == "openai"
    assert loaded_chat.harness_version is None


def test_bootstrap_database_backfills_phase4_run_identity_for_legacy_rows(tmp_path):
    db_path = tmp_path / "chat.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL CHECK(title <> ''),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                deleted_at TEXT
            );

            CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id INTEGER NOT NULL,
                position INTEGER NOT NULL CHECK(position >= 0),
                role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                UNIQUE (chat_session_id, position)
            );

            CREATE TABLE chat_turn_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                chat_session_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('processing', 'completed', 'failed', 'conflicted')),
                user_message_id INTEGER NOT NULL,
                assistant_message_id INTEGER,
                failure_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                FOREIGN KEY (assistant_message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                UNIQUE (client_id, request_id)
            );
            """
        )
        connection.execute(
            """
            INSERT INTO chat_sessions (
                client_id,
                title,
                created_at,
                updated_at,
                archived_at,
                deleted_at
            ) VALUES (?, ?, ?, ?, NULL, NULL)
            """,
            ("client-a", "Legacy chat", "2026-03-22T10:00:00+00:00", "2026-03-22T10:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO chat_messages (
                chat_session_id,
                position,
                role,
                content,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (1, 0, "user", "Hello", "2026-03-22T10:00:01+00:00"),
        )
        connection.execute(
            """
            INSERT INTO chat_turn_requests (
                client_id,
                request_id,
                chat_session_id,
                status,
                user_message_id,
                assistant_message_id,
                failure_code,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "client-a",
                "legacy-request-1",
                1,
                "failed",
                1,
                None,
                "provider_error",
                "2026-03-22T10:00:01+00:00",
                "2026-03-22T10:00:02+00:00",
            ),
        )

    bootstrap_database(db_path)
    with sqlite3.connect(db_path) as connection:
        run_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'chat_session_runs'"
        ).fetchone()
        assert run_table is not None

        turn_request_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(chat_turn_requests)").fetchall()
        }
        assert "run_id" in turn_request_columns

        turn_request_row = connection.execute(
            "SELECT run_id FROM chat_turn_requests WHERE client_id = ? AND request_id = ?",
            ("client-a", "legacy-request-1"),
        ).fetchone()
        assert turn_request_row is not None
        assert turn_request_row[0] is not None

        run_row = connection.execute(
            """
            SELECT client_id, request_id, chat_session_id, run_kind, status
            FROM chat_session_runs
            WHERE id = ?
            """,
            (turn_request_row[0],),
        ).fetchone()
        assert run_row is not None
        assert run_row == (
            "client-a",
            "legacy-request-1",
            1,
            "chat_send",
            "failed",
        )


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


def test_chat_repository_start_turn_persists_run_identity_link(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-run-link",
        chat_session_id=None,
        message="Hello",
    )
    assert start_result.turn_request_state is not None
    assert start_result.turn_request_state.turn_request.run_id is not None
    assert start_result.turn_request_state.run is not None
    assert start_result.turn_request_state.run.id == start_result.turn_request_state.turn_request.run_id
    assert start_result.turn_request_state.run.status == "processing"

    completed_state = repository.finalize_turn_success(
        client_id="client-a",
        request_id="request-run-link",
        assistant_content="Hi there",
    )
    assert completed_state.run is not None
    assert completed_state.run.status == "completed"
    assert completed_state.turn_request.run_id == completed_state.run.id


def test_chat_repository_get_latest_run_for_chat_session_returns_none_when_no_runs_exist(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    latest_run = repository.get_latest_run_for_chat_session(
        chat_session_id=chat.id,
        client_id="client-a",
    )

    assert latest_run is None


def test_chat_repository_get_chat_session_inspectability_returns_latest_run(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")

    first_turn = repository.start_turn_request(
        client_id="client-a",
        request_id="request-inspect-1",
        chat_session_id=chat.id,
        message="First",
    )
    assert first_turn.turn_request_state is not None
    repository.finalize_turn_success(
        client_id="client-a",
        request_id="request-inspect-1",
        assistant_content="Reply",
    )
    second_turn = repository.start_turn_request(
        client_id="client-a",
        request_id="request-inspect-2",
        chat_session_id=chat.id,
        message="Second",
    )
    assert second_turn.turn_request_state is not None
    assert second_turn.turn_request_state.run is not None

    inspectability = repository.get_chat_session_inspectability(
        chat_session_id=chat.id,
        client_id="client-a",
    )

    assert inspectability is not None
    assert inspectability.chat_session.id == chat.id
    assert inspectability.chat_session.harness_key == "openai"
    assert inspectability.latest_run is not None
    assert inspectability.latest_run.id == second_turn.turn_request_state.run.id
    assert inspectability.latest_run.status == "processing"
    assert inspectability.latest_run.run_kind == "chat_send"


def test_chat_repository_get_chat_session_inspectability_hides_archived_chats(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)
    chat = repository.create_chat(client_id="client-a", title="Chat 1")
    repository.start_turn_request(
        client_id="client-a",
        request_id="request-inspect-archived",
        chat_session_id=chat.id,
        message="Hidden",
    )
    assert repository.archive_chat(chat_session_id=chat.id, client_id="client-a") is True

    inspectability = repository.get_chat_session_inspectability(
        chat_session_id=chat.id,
        client_id="client-a",
    )
    latest_run = repository.get_latest_run_for_chat_session(
        chat_session_id=chat.id,
        client_id="client-a",
    )

    assert inspectability is None
    assert latest_run is not None


def test_chat_repository_duplicate_turn_replay_does_not_create_extra_runs(tmp_path):
    db_path = tmp_path / "chat.db"
    bootstrap_database(db_path)
    repository = ChatRepository(db_path)

    start_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-duplicate-run",
        chat_session_id=None,
        message="Hello",
    )
    duplicate_result = repository.start_turn_request(
        client_id="client-a",
        request_id="request-duplicate-run",
        chat_session_id=None,
        message="Hello again",
    )

    assert start_result.turn_request_state is not None
    assert duplicate_result.turn_request_state is not None
    assert start_result.turn_request_state.turn_request.run_id is not None
    assert duplicate_result.turn_request_state.turn_request.run_id is not None
    assert (
        start_result.turn_request_state.turn_request.run_id
        == duplicate_result.turn_request_state.turn_request.run_id
    )

    with sqlite3.connect(db_path) as connection:
        run_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM chat_session_runs
            WHERE client_id = ? AND request_id = ?
            """,
            ("client-a", "request-duplicate-run"),
        ).fetchone()
    assert run_count is not None
    assert run_count[0] == 1


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
