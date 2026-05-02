"""
core/db.py — SQLite-Layer für die Agent Company

Zentrale DB:
- managers_shared.db   (Leadership Channel + teams + workspaces +
                        software_requests)

Pro Team eine eigene Chat-DB:
- team_<team_id>_chat.db   (zur Laufzeit angelegt, wenn CEO ein Team erstellt)
"""

from __future__ import annotations

import os
import aiosqlite
from datetime import datetime, timezone
from typing import Any, Optional

import settings


# =============================================================================
# DB-Pfade
# =============================================================================

def managers_db_path() -> str:
    return os.path.join(settings.DB_DIR, "managers_shared.db")


def team_chat_db_path(team_id: int) -> str:
    return os.path.join(settings.DB_DIR, f"team_{team_id}_chat.db")


# =============================================================================
# Schemas
# =============================================================================

_MANAGERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    name        TEXT NOT NULL,
    vault_path  TEXT
);

CREATE TABLE IF NOT EXISTS user_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    direction   TEXT NOT NULL,    -- "in" (User->CEO) | "out" (CEO->User)
    content     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS workspaces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    short_name  TEXT NOT NULL,
    path        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',  -- active | closed
    user_request TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS teams (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    session_id   INTEGER,
    workspace_id INTEGER NOT NULL,
    slug         TEXT NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL,
    capabilities TEXT NOT NULL,         -- JSON-Array
    worker_count INTEGER NOT NULL,
    folder_path  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS master_plans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    session_id   INTEGER,
    workspace_id INTEGER,
    user_request TEXT NOT NULL,
    content      TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS briefings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    plan_id     INTEGER,
    target_team_id INTEGER NOT NULL,
    content     TEXT NOT NULL,
    read_at     TEXT,
    FOREIGN KEY (plan_id)        REFERENCES master_plans(id),
    FOREIGN KEY (target_team_id) REFERENCES teams(id),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    parent_id   INTEGER,
    author      TEXT NOT NULL,
    topic       TEXT,
    content     TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES threads(id),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS status_updates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    author      TEXT NOT NULL,
    team_id     INTEGER,
    status      TEXT NOT NULL,
    blocker     INTEGER NOT NULL DEFAULT 0,
    message     TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    author      TEXT NOT NULL,
    team_id     INTEGER,
    plan_id     INTEGER,
    summary_path TEXT,                   -- Pfad zur Zusammenfassungs-Datei
    content     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS software_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    requester   TEXT NOT NULL,           -- agent_id
    team_id     INTEGER,
    package     TEXT NOT NULL,
    reason      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | denied
    decided_by  TEXT,                    -- "user" oder "ceo"
    decided_at  TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS access_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    requester   TEXT NOT NULL,
    team_id     INTEGER,
    resource_type TEXT NOT NULL,        -- obsidian | upload
    access_mode TEXT NOT NULL,          -- read | write
    target_path TEXT NOT NULL,
    reason      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending', -- pending | approved | denied
    decided_by  TEXT,
    decided_at  TEXT,
    note        TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS terminal_commands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    session_id  INTEGER,
    requester   TEXT NOT NULL,
    command     TEXT NOT NULL,
    cwd         TEXT,
    reason      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    exit_code   INTEGER,
    stdout      TEXT,
    stderr      TEXT,
    decided_at  TEXT,
    finished_at TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS web_actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    action      TEXT NOT NULL,
    payload     TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    result      TEXT,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_threads_created   ON threads(created_at);
CREATE INDEX IF NOT EXISTS idx_briefings_team    ON briefings(target_team_id);
CREATE INDEX IF NOT EXISTS idx_status_team       ON status_updates(team_id);
CREATE INDEX IF NOT EXISTS idx_reports_team      ON reports(team_id);
CREATE INDEX IF NOT EXISTS idx_software_status   ON software_requests(status);
CREATE INDEX IF NOT EXISTS idx_access_status     ON access_requests(status);
CREATE INDEX IF NOT EXISTS idx_terminal_status   ON terminal_commands(status);
CREATE INDEX IF NOT EXISTS idx_web_actions       ON web_actions(status);
"""

_TEAM_CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    assigner     TEXT NOT NULL,
    worker_id    TEXT NOT NULL,
    description  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS chat (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    author      TEXT NOT NULL,
    content     TEXT NOT NULL,
    reply_to    INTEGER,
    FOREIGN KEY (reply_to) REFERENCES chat(id)
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    task_id     INTEGER NOT NULL,
    worker_id   TEXT NOT NULL,
    content     TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat(created_at);
"""


async def init_managers_db() -> None:
    async with aiosqlite.connect(managers_db_path()) as conn:
        await conn.executescript(_MANAGERS_SCHEMA)
        await _run_migrations(conn)
        await conn.commit()


async def init_team_chat_db(team_id: int) -> None:
    async with aiosqlite.connect(team_chat_db_path(team_id)) as conn:
        await conn.executescript(_TEAM_CHAT_SCHEMA)
        await conn.commit()


# =============================================================================
# Database-Wrapper
# =============================================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def _run_migrations(conn: aiosqlite.Connection) -> None:
    await _ensure_column(conn, "chat_sessions", "vault_path", "TEXT")
    await _ensure_column(conn, "user_messages", "session_id", "INTEGER")
    await _ensure_column(conn, "workspaces", "session_id", "INTEGER")
    await _ensure_column(conn, "teams", "session_id", "INTEGER")
    await _ensure_column(conn, "master_plans", "session_id", "INTEGER")
    await _ensure_column(conn, "briefings", "session_id", "INTEGER")
    await _ensure_column(conn, "threads", "session_id", "INTEGER")
    await _ensure_column(conn, "status_updates", "session_id", "INTEGER")
    await _ensure_column(conn, "reports", "session_id", "INTEGER")
    await _ensure_column(conn, "software_requests", "session_id", "INTEGER")
    await _ensure_column(conn, "access_requests", "session_id", "INTEGER")
    await _ensure_column(conn, "terminal_commands", "session_id", "INTEGER")


async def _ensure_column(
    conn: aiosqlite.Connection,
    table: str,
    column: str,
    ddl_type: str,
) -> None:
    cursor = await conn.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


class Database:
    """Wrapper um eine einzelne SQLite-DB."""

    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name

    async def fetch_all(
        self,
        table: str,
        where: Optional[str] = None,
        params: tuple = (),
        order_by: str = "id ASC",
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {int(limit)}"

        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetch_one(
        self,
        table: str,
        where: str,
        params: tuple,
    ) -> Optional[dict[str, Any]]:
        rows = await self.fetch_all(table, where=where, params=params, limit=1)
        return rows[0] if rows else None

    async def fetch_since(
        self,
        table: str,
        last_seen_id: int,
        order_by: str = "id ASC",
    ) -> list[dict[str, Any]]:
        return await self.fetch_all(
            table=table,
            where="id > ?",
            params=(last_seen_id,),
            order_by=order_by,
        )

    async def insert(self, table: str, data: dict[str, Any]) -> int:
        if "created_at" not in data:
            data = {**data, "created_at": now_iso()}
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        async with aiosqlite.connect(self.path) as conn:
            cursor = await conn.execute(sql, tuple(data.values()))
            await conn.commit()
            return cursor.lastrowid or 0

    async def update(
        self,
        table: str,
        set_data: dict[str, Any],
        where: str,
        params: tuple,
    ) -> int:
        set_clause = ", ".join(f"{k} = ?" for k in set_data)
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        async with aiosqlite.connect(self.path) as conn:
            cursor = await conn.execute(sql, tuple(set_data.values()) + params)
            await conn.commit()
            return cursor.rowcount

    async def delete(
        self,
        table: str,
        where: str,
        params: tuple,
    ) -> int:
        sql = f"DELETE FROM {table} WHERE {where}"
        async with aiosqlite.connect(self.path) as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

    async def max_id(self, table: str) -> int:
        async with aiosqlite.connect(self.path) as conn:
            cursor = await conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0


def get_managers_db() -> Database:
    return Database(managers_db_path(), "managers_shared")


def get_team_chat_db(team_id: int) -> Database:
    return Database(team_chat_db_path(team_id), f"team_{team_id}_chat")
