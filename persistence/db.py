from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_CHAT_HARNESS_KEY = "openai"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK(title <> ''),
    harness_key TEXT NOT NULL DEFAULT 'openai' CHECK(harness_key <> ''),
    harness_version TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_session_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    UNIQUE (chat_session_id, position)
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_visible_by_client
ON chat_sessions (client_id, archived_at, deleted_at, updated_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_by_chat_position
ON chat_messages (chat_session_id, position ASC, id ASC);

CREATE TABLE IF NOT EXISTS chat_turn_requests (
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

CREATE INDEX IF NOT EXISTS idx_chat_turn_requests_by_client_status
ON chat_turn_requests (client_id, status, updated_at DESC, id DESC);
"""


class StorageInitializationError(RuntimeError):
    """Raised when the chat persistence layer cannot be initialized."""


def connect_database(db_path: Path) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error as exc:  # pragma: no cover - exercised through bootstrap failures
        raise StorageInitializationError(f"Could not open SQLite database at {db_path}.") from exc

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def bootstrap_database(db_path: Path) -> None:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageInitializationError(
            f"Could not create the database directory for {db_path}."
        ) from exc

    try:
        with closing(connect_database(db_path)) as connection:
            with connection:
                connection.executescript(SCHEMA_SQL)
                _ensure_chat_session_binding_columns(connection)
    except sqlite3.Error as exc:
        raise StorageInitializationError(f"Could not bootstrap SQLite schema at {db_path}.") from exc


def _ensure_chat_session_binding_columns(connection: sqlite3.Connection) -> None:
    column_names = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(chat_sessions)").fetchall()
    }

    if "harness_key" not in column_names:
        connection.execute(
            f"ALTER TABLE chat_sessions ADD COLUMN harness_key TEXT NOT NULL DEFAULT '{DEFAULT_CHAT_HARNESS_KEY}'"
        )
    if "harness_version" not in column_names:
        connection.execute("ALTER TABLE chat_sessions ADD COLUMN harness_version TEXT")

    connection.execute(
        """
        UPDATE chat_sessions
        SET harness_key = ?
        WHERE harness_key IS NULL OR TRIM(harness_key) = ''
        """,
        (DEFAULT_CHAT_HARNESS_KEY,),
    )
