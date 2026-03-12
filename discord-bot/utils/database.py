from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    modlog_channel_id INTEGER,
                    ticket_category_id INTEGER
                );

                CREATE TABLE IF NOT EXISTS badwords (
                    guild_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    PRIMARY KEY (guild_id, word)
                );

                CREATE TABLE IF NOT EXISTS xp (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    xp INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (guild_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS custom_commands (
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    response TEXT NOT NULL,
                    PRIMARY KEY (guild_id, name)
                );

                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    next_run_ts INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    due_ts INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reaction_roles (
                    guild_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    emoji TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, message_id, emoji)
                );
                """
            )

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        async with self._lock:
            await asyncio.to_thread(self._execute_sync, query, params)

    def _execute_sync(self, query: str, params: tuple[Any, ...]) -> None:
        with self._connect() as conn:
            conn.execute(query, params)
            conn.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        async with self._lock:
            return await asyncio.to_thread(self._fetchone_sync, query, params)

    def _fetchone_sync(self, query: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
        with self._connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        async with self._lock:
            return await asyncio.to_thread(self._fetchall_sync, query, params)

    def _fetchall_sync(self, query: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchall()
