from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from persistence.db import connect_database


@dataclass(frozen=True)
class ChatSession:
    id: int
    client_id: str
    title: str
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


class ChatRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def next_default_chat_title(self, *, client_id: str) -> str:
        with closing(connect_database(self._db_path)) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS chat_count
                FROM chat_sessions
                WHERE client_id = ?
                """,
                (client_id,),
            ).fetchone()
            chat_count = int(row["chat_count"]) if row is not None else 0
            return f"Chat {chat_count + 1}"

    def create_chat(self, *, client_id: str, title: str) -> ChatSession:
        timestamp = _utcnow()
        with closing(connect_database(self._db_path)) as connection:
            with connection:
                cursor = connection.execute(
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
                    (client_id, title, timestamp, timestamp),
                )
                row = connection.execute(
                    "SELECT * FROM chat_sessions WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                if row is None:  # pragma: no cover - defensive against unexpected SQLite behavior
                    raise RuntimeError("Newly created chat session could not be reloaded.")
                return _row_to_chat_session(row)

    def create_message(self, *, chat_session_id: int, client_id: str, role: str, content: str) -> ChatMessage:
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
                    raise LookupError(f"Chat {chat_session_id} was not found for client {client_id}.")

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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _row_to_chat_session(row: sqlite3.Row) -> ChatSession:
    return ChatSession(
        id=int(row["id"]),
        client_id=str(row["client_id"]),
        title=str(row["title"]),
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
