from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

from agents.chat_harness import ConversationTurn

from persistence.db import DEFAULT_CHAT_HARNESS_KEY, connect_database


@dataclass(frozen=True)
class ChatSession:
    id: int
    client_id: str
    title: str
    harness_key: str
    harness_version: str | None
    created_at: str
    updated_at: str
    archived_at: str | None
    deleted_at: str | None


@dataclass(frozen=True)
class ChatMessage:
    id: int
    chat_session_id: int
    position: int
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class ChatTurnRequest:
    id: int
    client_id: str
    request_id: str
    chat_session_id: int
    status: Literal["processing", "completed", "failed", "conflicted"]
    user_message_id: int
    assistant_message_id: int | None
    failure_code: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChatTurnRequestState:
    turn_request: ChatTurnRequest
    chat_session: ChatSession | None
    user_message: ChatMessage
    assistant_message: ChatMessage | None


@dataclass(frozen=True)
class StartTurnRequestResult:
    outcome: Literal["started", "duplicate", "missing"]
    turn_request_state: ChatTurnRequestState | None = None
    chat_session: ChatSession | None = None
    prior_messages: list[ChatMessage] = field(default_factory=list)


class ChatRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def next_default_chat_title(self, *, client_id: str) -> str:
        with closing(connect_database(self._db_path)) as connection:
            return self._next_default_chat_title(connection, client_id=client_id)

    def create_chat(
        self,
        *,
        client_id: str,
        title: str,
        harness_key: str = DEFAULT_CHAT_HARNESS_KEY,
        harness_version: str | None = None,
    ) -> ChatSession:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO chat_sessions (
                        client_id,
                        title,
                        harness_key,
                        harness_version,
                        created_at,
                        updated_at,
                        archived_at,
                        deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (client_id, title, harness_key, harness_version, timestamp, timestamp),
                )
                row = connection.execute(
                    "SELECT * FROM chat_sessions WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
                    raise RuntimeError("Newly created chat session could not be reloaded.")
                return _row_to_chat_session(row)

    def create_message(
        self, *, chat_session_id: int, client_id: str, role: str, content: str
    ) -> ChatMessage:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            with connection:
                chat_row = connection.execute(
                    """
                    SELECT id
                    FROM chat_sessions
                    WHERE id = ? AND client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
                    """,
                    (chat_session_id, client_id),
                ).fetchone()
                if chat_row is None:
                    raise LookupError(
                        f"Chat {chat_session_id} was not found for client {client_id}."
                    )

                next_position = connection.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1
                    FROM chat_messages
                    WHERE chat_session_id = ?
                    """,
                    (chat_session_id,),
                ).fetchone()[0]

                cursor = connection.execute(
                    """
                    INSERT INTO chat_messages (
                        chat_session_id,
                        position,
                        role,
                        content,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (chat_session_id, next_position, role, content, timestamp),
                )
                connection.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                    (timestamp, chat_session_id),
                )
                row = connection.execute(
                    "SELECT * FROM chat_messages WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
                    raise RuntimeError("Newly created chat message could not be reloaded.")
                return _row_to_chat_message(row)

    def get_chat(self, *, chat_session_id: int, client_id: str) -> ChatSession | None:
        with closing(connect_database(self._db_path)) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM chat_sessions
                WHERE id = ? AND client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
                """,
                (chat_session_id, client_id),
            ).fetchone()
            return None if row is None else _row_to_chat_session(row)

    def list_visible_chats(self, *, client_id: str) -> list[ChatSession]:
        with closing(connect_database(self._db_path)) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM chat_sessions
                WHERE client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
                ORDER BY updated_at DESC, id DESC
                """,
                (client_id,),
            ).fetchall()
            return [_row_to_chat_session(row) for row in rows]

    def list_messages_for_chat(self, *, chat_session_id: int, client_id: str) -> list[ChatMessage]:
        with closing(connect_database(self._db_path)) as connection:
            rows = connection.execute(
                """
                SELECT m.*
                FROM chat_messages AS m
                INNER JOIN chat_sessions AS s ON s.id = m.chat_session_id
                WHERE s.id = ? AND s.client_id = ? AND s.archived_at IS NULL AND s.deleted_at IS NULL
                ORDER BY m.position ASC, m.id ASC
                """,
                (chat_session_id, client_id),
            ).fetchall()
            return [_row_to_chat_message(row) for row in rows]

    def soft_delete_chat(self, *, chat_session_id: int, client_id: str) -> bool:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE chat_sessions
                    SET deleted_at = ?, updated_at = ?
                    WHERE id = ? AND client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
                    """,
                    (timestamp, timestamp, chat_session_id, client_id),
                )
                return cursor.rowcount > 0

    def archive_chat(self, *, chat_session_id: int, client_id: str) -> bool:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE chat_sessions
                    SET archived_at = ?, updated_at = ?
                    WHERE id = ? AND client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
                    """,
                    (timestamp, timestamp, chat_session_id, client_id),
                )
                return cursor.rowcount > 0

    def start_turn_request(
        self,
        *,
        client_id: str,
        request_id: str,
        chat_session_id: int | None,
        message: str,
        harness_key: str = DEFAULT_CHAT_HARNESS_KEY,
        harness_version: str | None = None,
    ) -> StartTurnRequestResult:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            _begin_immediate_transaction(connection)
            try:
                existing_request = _load_turn_request_row(
                    connection,
                    client_id=client_id,
                    request_id=request_id,
                )
                if existing_request is not None:
                    result = StartTurnRequestResult(
                        outcome="duplicate",
                        turn_request_state=_hydrate_turn_request_state(connection, existing_request),
                    )
                    connection.commit()
                    return result

                chat_row: sqlite3.Row | None
                if chat_session_id is None:
                    chat_row = _insert_chat_row(
                        connection,
                        client_id=client_id,
                        title=self._next_default_chat_title(connection, client_id=client_id),
                        harness_key=harness_key,
                        harness_version=harness_version,
                        timestamp=timestamp,
                    )
                    prior_messages: list[ChatMessage] = []
                else:
                    chat_row = _load_active_chat_row(
                        connection,
                        chat_session_id=chat_session_id,
                        client_id=client_id,
                    )
                    if chat_row is None:
                        connection.rollback()
                        return StartTurnRequestResult(outcome="missing")
                    prior_messages = _load_messages_for_chat_rows(
                        connection,
                        chat_session_id=chat_session_id,
                    )

                resolved_chat_session = _row_to_chat_session(chat_row)
                user_message = _insert_message_row(
                    connection,
                    chat_session_id=resolved_chat_session.id,
                    role="user",
                    content=message,
                    timestamp=timestamp,
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
                    ) VALUES (?, ?, ?, 'processing', ?, NULL, NULL, ?, ?)
                    """,
                    (client_id, request_id, resolved_chat_session.id, user_message.id, timestamp, timestamp),
                )
                connection.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                    (timestamp, resolved_chat_session.id),
                )
                turn_request = _load_turn_request_row(
                    connection,
                    client_id=client_id,
                    request_id=request_id,
                )
                if turn_request is None:  # pragma: no cover - defensive against unexpected SQLite behavior
                    raise RuntimeError("Newly created turn request could not be reloaded.")

                result = StartTurnRequestResult(
                    outcome="started",
                    turn_request_state=_hydrate_turn_request_state(connection, turn_request),
                    chat_session=resolved_chat_session,
                    prior_messages=prior_messages,
                )
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise

    def _next_default_chat_title(
        self,
        connection: sqlite3.Connection,
        *,
        client_id: str,
    ) -> str:
        return f"Chat {_count_chats_for_client(connection, client_id=client_id) + 1}"

    def get_turn_request_state(
        self,
        *,
        client_id: str,
        request_id: str,
    ) -> ChatTurnRequestState | None:
        with closing(connect_database(self._db_path)) as connection:
            row = _load_turn_request_row(connection, client_id=client_id, request_id=request_id)
            if row is None:
                return None
            return _hydrate_turn_request_state(connection, row)

    def finalize_turn_success(
        self,
        *,
        client_id: str,
        request_id: str,
        assistant_content: str,
    ) -> ChatTurnRequestState:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            _begin_immediate_transaction(connection)
            try:
                turn_request_row = _require_turn_request_row(
                    connection,
                    client_id=client_id,
                    request_id=request_id,
                )
                if turn_request_row["status"] != "processing":
                    state = _hydrate_turn_request_state(connection, turn_request_row)
                    connection.commit()
                    return state

                chat_row = _load_chat_row(
                    connection,
                    chat_session_id=int(turn_request_row["chat_session_id"]),
                    client_id=client_id,
                )
                if chat_row is None or chat_row["archived_at"] is not None or chat_row["deleted_at"] is not None:
                    state = self._mark_turn_request_conflicted(
                        connection,
                        turn_request_row=turn_request_row,
                        timestamp=timestamp,
                    )
                    connection.commit()
                    return state

                assistant_message = _insert_message_row(
                    connection,
                    chat_session_id=int(turn_request_row["chat_session_id"]),
                    role="assistant",
                    content=assistant_content,
                    timestamp=timestamp,
                )
                connection.execute(
                    """
                    UPDATE chat_turn_requests
                    SET status = 'completed',
                        assistant_message_id = ?,
                        failure_code = NULL,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (assistant_message.id, timestamp, int(turn_request_row["id"])),
                )
                connection.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                    (timestamp, int(turn_request_row["chat_session_id"])),
                )
                state = _hydrate_turn_request_state(
                    connection,
                    _require_turn_request_row(connection, client_id=client_id, request_id=request_id),
                )
                connection.commit()
                return state
            except Exception:
                connection.rollback()
                raise

    def finalize_turn_failure(
        self,
        *,
        client_id: str,
        request_id: str,
        failure_code: str,
    ) -> ChatTurnRequestState:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            _begin_immediate_transaction(connection)
            try:
                turn_request_row = _require_turn_request_row(
                    connection,
                    client_id=client_id,
                    request_id=request_id,
                )
                if turn_request_row["status"] != "processing":
                    state = _hydrate_turn_request_state(connection, turn_request_row)
                    connection.commit()
                    return state

                chat_row = _load_chat_row(
                    connection,
                    chat_session_id=int(turn_request_row["chat_session_id"]),
                    client_id=client_id,
                )
                if chat_row is None or chat_row["archived_at"] is not None or chat_row["deleted_at"] is not None:
                    state = self._mark_turn_request_conflicted(
                        connection,
                        turn_request_row=turn_request_row,
                        timestamp=timestamp,
                    )
                    connection.commit()
                    return state

                connection.execute(
                    """
                    UPDATE chat_turn_requests
                    SET status = 'failed',
                        failure_code = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (failure_code, timestamp, int(turn_request_row["id"])),
                )
                state = _hydrate_turn_request_state(
                    connection,
                    _require_turn_request_row(connection, client_id=client_id, request_id=request_id),
                )
                connection.commit()
                return state
            except Exception:
                connection.rollback()
                raise

    def _mark_turn_request_conflicted(
        self,
        connection: sqlite3.Connection,
        *,
        turn_request_row: sqlite3.Row,
        timestamp: str,
    ) -> ChatTurnRequestState:
        connection.execute(
            """
            UPDATE chat_turn_requests
            SET status = 'conflicted',
                failure_code = 'chat_unavailable',
                updated_at = ?
            WHERE id = ?
            """,
            (timestamp, int(turn_request_row["id"])),
        )
        return _hydrate_turn_request_state(
            connection,
            _require_turn_request_row(
                connection,
                client_id=str(turn_request_row["client_id"]),
                request_id=str(turn_request_row["request_id"]),
            ),
        )


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _begin_immediate_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")


def _count_chats_for_client(connection: sqlite3.Connection, *, client_id: str) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS chat_count
        FROM chat_sessions
        WHERE client_id = ?
        """,
        (client_id,),
    ).fetchone()
    return int(row["chat_count"]) if row is not None else 0


def _load_active_chat_row(
    connection: sqlite3.Connection,
    *,
    chat_session_id: int,
    client_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE id = ? AND client_id = ? AND archived_at IS NULL AND deleted_at IS NULL
        """,
        (chat_session_id, client_id),
    ).fetchone()


def _load_chat_row(
    connection: sqlite3.Connection,
    *,
    chat_session_id: int,
    client_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE id = ? AND client_id = ?
        """,
        (chat_session_id, client_id),
    ).fetchone()


def _load_messages_for_chat_rows(
    connection: sqlite3.Connection,
    *,
    chat_session_id: int,
) -> list[ChatMessage]:
    rows = connection.execute(
        """
        SELECT *
        FROM chat_messages
        WHERE chat_session_id = ?
        ORDER BY position ASC, id ASC
        """,
        (chat_session_id,),
    ).fetchall()
    return [_row_to_chat_message(row) for row in rows]


def conversation_turns_from_messages(messages: list[ChatMessage]) -> tuple[ConversationTurn, ...]:
    history: list[ConversationTurn] = []
    for message in messages:
        if message.role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported persisted role for conversation history: {message.role}")
        history.append(
            ConversationTurn(
                role=cast(Literal["user", "assistant"], message.role),
                content=message.content,
            )
        )
    return tuple(history)


def _insert_chat_row(
    connection: sqlite3.Connection,
    *,
    client_id: str,
    title: str,
    harness_key: str,
    harness_version: str | None,
    timestamp: str,
) -> sqlite3.Row:
    cursor = connection.execute(
        """
        INSERT INTO chat_sessions (
            client_id,
            title,
            harness_key,
            harness_version,
            created_at,
            updated_at,
            archived_at,
            deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
        """,
        (client_id, title, harness_key, harness_version, timestamp, timestamp),
    )
    row = connection.execute(
        "SELECT * FROM chat_sessions WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
        raise RuntimeError("Newly created chat session could not be reloaded.")
    return row


def _next_message_position(connection: sqlite3.Connection, *, chat_session_id: int) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(position), -1) + 1 AS next_position
        FROM chat_messages
        WHERE chat_session_id = ?
        """,
        (chat_session_id,),
    ).fetchone()
    if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
        raise RuntimeError("Could not calculate the next chat message position.")
    return int(row["next_position"])


def _insert_message_row(
    connection: sqlite3.Connection,
    *,
    chat_session_id: int,
    role: str,
    content: str,
    timestamp: str,
) -> ChatMessage:
    cursor = connection.execute(
        """
        INSERT INTO chat_messages (
            chat_session_id,
            position,
            role,
            content,
            created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (chat_session_id, _next_message_position(connection, chat_session_id=chat_session_id), role, content, timestamp),
    )
    row = connection.execute(
        "SELECT * FROM chat_messages WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
        raise RuntimeError("Newly created chat message could not be reloaded.")
    return _row_to_chat_message(row)


def _load_turn_request_row(
    connection: sqlite3.Connection,
    *,
    client_id: str,
    request_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM chat_turn_requests
        WHERE client_id = ? AND request_id = ?
        """,
        (client_id, request_id),
    ).fetchone()


def _require_turn_request_row(
    connection: sqlite3.Connection,
    *,
    client_id: str,
    request_id: str,
) -> sqlite3.Row:
    row = _load_turn_request_row(connection, client_id=client_id, request_id=request_id)
    if row is None:
        raise LookupError(f"Turn request {request_id} was not found for client {client_id}.")
    return row


def _load_message_row(connection: sqlite3.Connection, *, message_id: int | None) -> ChatMessage | None:
    if message_id is None:
        return None
    row = connection.execute(
        "SELECT * FROM chat_messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
        raise RuntimeError(f"Chat message {message_id} could not be reloaded.")
    return _row_to_chat_message(row)


def _hydrate_turn_request_state(
    connection: sqlite3.Connection,
    turn_request_row: sqlite3.Row,
) -> ChatTurnRequestState:
    turn_request = _row_to_chat_turn_request(turn_request_row)
    user_message = _load_message_row(connection, message_id=turn_request.user_message_id)
    if user_message is None:  # pragma: no cover - defensive against required foreign key integrity
        raise RuntimeError(
            f"Turn request {turn_request.request_id} is missing its required user message."
        )

    chat_session = None
    chat_row = _load_chat_row(
        connection,
        chat_session_id=turn_request.chat_session_id,
        client_id=turn_request.client_id,
    )
    if chat_row is not None:
        chat_session = _row_to_chat_session(chat_row)

    return ChatTurnRequestState(
        turn_request=turn_request,
        chat_session=chat_session,
        user_message=user_message,
        assistant_message=_load_message_row(
            connection,
            message_id=turn_request.assistant_message_id,
        ),
    )


def _row_to_chat_session(row: sqlite3.Row) -> ChatSession:
    return ChatSession(
        id=int(row["id"]),
        client_id=str(row["client_id"]),
        title=str(row["title"]),
        harness_key=str(row["harness_key"]),
        harness_version=(
            None if row["harness_version"] is None else str(row["harness_version"])
        ),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        archived_at=None if row["archived_at"] is None else str(row["archived_at"]),
        deleted_at=None if row["deleted_at"] is None else str(row["deleted_at"]),
    )


def _row_to_chat_message(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=int(row["id"]),
        chat_session_id=int(row["chat_session_id"]),
        position=int(row["position"]),
        role=str(row["role"]),
        content=str(row["content"]),
        created_at=str(row["created_at"]),
    )


def _row_to_chat_turn_request(row: sqlite3.Row) -> ChatTurnRequest:
    return ChatTurnRequest(
        id=int(row["id"]),
        client_id=str(row["client_id"]),
        request_id=str(row["request_id"]),
        chat_session_id=int(row["chat_session_id"]),
        status=row["status"],
        user_message_id=int(row["user_message_id"]),
        assistant_message_id=(
            None if row["assistant_message_id"] is None else int(row["assistant_message_id"])
        ),
        failure_code=None if row["failure_code"] is None else str(row["failure_code"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
