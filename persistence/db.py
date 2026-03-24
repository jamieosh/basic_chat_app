from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_CHAT_HARNESS_KEY = "openai"
DEFAULT_CHAT_RUN_KIND = "chat_send"


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

CREATE TABLE IF NOT EXISTS chat_session_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    chat_session_id INTEGER NOT NULL,
    run_kind TEXT NOT NULL DEFAULT 'chat_send' CHECK(run_kind <> ''),
    status TEXT NOT NULL CHECK(status IN ('processing', 'completed', 'failed', 'conflicted')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    UNIQUE (client_id, request_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_session_runs_by_chat
ON chat_session_runs (chat_session_id, updated_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS chat_turn_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    chat_session_id INTEGER NOT NULL,
    run_id INTEGER,
    status TEXT NOT NULL CHECK(status IN ('processing', 'completed', 'failed', 'conflicted')),
    user_message_id INTEGER NOT NULL,
    assistant_message_id INTEGER,
    failure_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES chat_session_runs(id) ON DELETE SET NULL,
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
                _ensure_turn_request_run_identity(connection)
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


def _ensure_turn_request_run_identity(connection: sqlite3.Connection) -> None:
    column_names = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(chat_turn_requests)").fetchall()
    }
    if "run_id" not in column_names:
        connection.execute("ALTER TABLE chat_turn_requests ADD COLUMN run_id INTEGER")

    _backfill_turn_request_run_links(connection)


def _backfill_turn_request_run_links(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, client_id, request_id, chat_session_id, status, created_at, updated_at
        FROM chat_turn_requests
        WHERE run_id IS NULL
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        run_row = connection.execute(
            """
            SELECT id
            FROM chat_session_runs
            WHERE client_id = ? AND request_id = ?
            """,
            (str(row["client_id"]), str(row["request_id"])),
        ).fetchone()
        if run_row is None:
            cursor = connection.execute(
                """
                INSERT INTO chat_session_runs (
                    client_id,
                    request_id,
                    chat_session_id,
                    run_kind,
                    status,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["client_id"]),
                    str(row["request_id"]),
                    int(row["chat_session_id"]),
                    DEFAULT_CHAT_RUN_KIND,
                    str(row["status"]),
                    str(row["created_at"]),
                    str(row["updated_at"]),
                ),
            )
            if cursor.lastrowid is None:  # pragma: no cover - defensive against unexpected SQLite behavior
                raise RuntimeError("Backfilled chat session run insert did not return an id.")
            run_id = int(cursor.lastrowid)
        else:
            run_id = int(run_row["id"])
            connection.execute(
                """
                UPDATE chat_session_runs
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (str(row["status"]), str(row["updated_at"]), run_id),
            )

        connection.execute(
            """
            UPDATE chat_turn_requests
            SET run_id = ?
            WHERE id = ?
            """,
            (run_id, int(row["id"])),
        )
