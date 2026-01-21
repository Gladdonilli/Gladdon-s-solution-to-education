"""Database models and configuration functions for Canvas Sync.

This module contains all SQLite database operations including:
- Database initialization and connection management
- Configuration get/set operations
- Sync state tracking

All functions require explicit vault_path or connection to avoid circular dependencies.
"""

import sqlite3
from pathlib import Path
from typing import Any

from canvas_sync.config import DEFAULT_SYNC_TIME, DEFAULT_VAULT_PATH


def get_db_path(vault_path: str) -> Path:
    """Get the path to the SQLite database file.

    Args:
        vault_path: Path to the Obsidian vault

    Returns:
        Path to sync.db file
    """
    return Path(vault_path) / ".canvas_sync" / "sync.db"


def init_db(vault_path: str) -> sqlite3.Connection:
    """Initialize database, creating tables if needed.

    Called on app startup and before any sync operation.
    Safe to call multiple times (idempotent).

    Args:
        vault_path: Path to the Obsidian vault

    Returns:
        SQLite connection with Row factory enabled
    """
    db_path = get_db_path(vault_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript(
        """
        -- Tracks sync state for each Canvas item
        CREATE TABLE IF NOT EXISTS sync_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canvas_id INTEGER NOT NULL,
            canvas_type TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            content_hash TEXT NOT NULL,
            canvas_updated_at TEXT,
            synced_at TEXT NOT NULL,
            UNIQUE(canvas_id, canvas_type)
        );

        -- Tracks user-selected courses
        CREATE TABLE IF NOT EXISTS selected_courses (
            course_id INTEGER PRIMARY KEY,
            course_name TEXT NOT NULL,
            selected_at TEXT NOT NULL
        );

        -- Stores app configuration
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sync_canvas ON sync_state(canvas_id, canvas_type);
        CREATE INDEX IF NOT EXISTS idx_sync_course ON sync_state(course_id);
    """
    )
    conn.commit()
    return conn


def get_db(vault_path: str | None = None) -> sqlite3.Connection:
    """Get database connection. Creates DB if needed.

    Args:
        vault_path: Path to the Obsidian vault. Uses default if None.

    Returns:
        SQLite connection
    """
    if vault_path is None:
        vault_path = str(DEFAULT_VAULT_PATH)
    return init_db(vault_path)


def get_config(conn: sqlite3.Connection, key: str) -> str | None:
    """Get config value from database.

    Args:
        conn: SQLite connection
        key: Config key to retrieve

    Returns:
        Config value or None if not found
    """
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set config value in database.

    Args:
        conn: SQLite connection
        key: Config key
        value: Config value
    """
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()


def get_vault_path_from_config(conn: sqlite3.Connection) -> str:
    """Get vault path from DB config, with fallback to constant.

    Args:
        conn: SQLite connection

    Returns:
        Vault path string
    """
    path = get_config(conn, "vault_path")
    return path if path else str(DEFAULT_VAULT_PATH)


def get_sync_time_from_config(conn: sqlite3.Connection) -> str:
    """Get sync time from DB config, with fallback to constant.

    Args:
        conn: SQLite connection

    Returns:
        Sync time in HH:MM format
    """
    return get_config(conn, "sync_time") or DEFAULT_SYNC_TIME


def get_selected_courses(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get list of selected courses from database.

    Args:
        conn: SQLite connection

    Returns:
        List of dicts with course_id, course_name, selected_at
    """
    cursor = conn.execute(
        "SELECT course_id, course_name, selected_at FROM selected_courses"
    )
    return [dict(row) for row in cursor.fetchall()]


def set_selected_courses(
    conn: sqlite3.Connection, courses: list[dict[str, Any]]
) -> None:
    """Replace all selected courses with new selection.

    Args:
        conn: SQLite connection
        courses: List of dicts with 'course_id' and 'course_name' keys
    """
    from datetime import datetime

    conn.execute("DELETE FROM selected_courses")
    for course in courses:
        conn.execute(
            "INSERT INTO selected_courses (course_id, course_name, selected_at) VALUES (?, ?, ?)",
            (course["course_id"], course["course_name"], datetime.now().isoformat()),
        )
    conn.commit()


def get_sync_state(
    conn: sqlite3.Connection, canvas_id: int, canvas_type: str
) -> dict[str, Any] | None:
    """Get sync state for a Canvas item.

    Args:
        conn: SQLite connection
        canvas_id: Canvas item ID
        canvas_type: 'assignment' or 'calendar_event'

    Returns:
        Dict with sync state or None if not found
    """
    cursor = conn.execute(
        "SELECT * FROM sync_state WHERE canvas_id = ? AND canvas_type = ?",
        (canvas_id, canvas_type),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def set_sync_state(
    conn: sqlite3.Connection,
    canvas_id: int,
    canvas_type: str,
    course_id: int,
    file_path: str,
    content_hash: str,
    canvas_updated_at: str | None,
    synced_at: str,
) -> None:
    """Insert or update sync state for a Canvas item.

    Args:
        conn: SQLite connection
        canvas_id: Canvas item ID
        canvas_type: 'assignment' or 'calendar_event'
        course_id: Canvas course ID
        file_path: Relative path in vault
        content_hash: SHA256 of markdown content
        canvas_updated_at: ISO8601 from Canvas API
        synced_at: ISO8601 of sync time
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO sync_state 
        (canvas_id, canvas_type, course_id, file_path, content_hash, canvas_updated_at, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            canvas_id,
            canvas_type,
            course_id,
            file_path,
            content_hash,
            canvas_updated_at,
            synced_at,
        ),
    )
    conn.commit()
