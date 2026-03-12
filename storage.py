from __future__ import annotations

from typing import Any

from utils.cache import MemoryCache
from utils.database import Database


class Storage:
    """Storage facade backed by SQLite + in-memory cache."""

    def __init__(self, db: Database, cache: MemoryCache):
        self.db = db
        self.cache = cache

    async def get_guild_config(self, guild_id: int) -> dict[str, Any]:
        cached = self.cache.get_config(guild_id)
        if cached is not None:
            return cached

        row = await self.db.fetchone(
            "SELECT welcome_channel_id, modlog_channel_id, ticket_category_id FROM guild_config WHERE guild_id = ?",
            (guild_id,),
        )
        config = {
            "welcome_channel_id": row["welcome_channel_id"] if row else None,
            "modlog_channel_id": row["modlog_channel_id"] if row else None,
            "ticket_category_id": row["ticket_category_id"] if row else None,
        }
        self.cache.set_config(guild_id, config)
        return config

    async def set_config_value(self, guild_id: int, key: str, value: int | None) -> None:
        await self.db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
        await self.db.execute(f"UPDATE guild_config SET {key} = ? WHERE guild_id = ?", (value, guild_id))
        config = await self.get_guild_config(guild_id)
        config[key] = value
        self.cache.set_config(guild_id, config)

    async def get_badwords(self, guild_id: int) -> set[str]:
        cached = self.cache.badwords.get(guild_id)
        if cached is not None:
            return cached
        rows = await self.db.fetchall("SELECT word FROM badwords WHERE guild_id = ?", (guild_id,))
        words = {row["word"] for row in rows}
        self.cache.badwords[guild_id] = words
        return words

    async def add_badword(self, guild_id: int, word: str) -> None:
        normalized = word.strip().lower()
        if not normalized:
            return
        await self.db.execute(
            "INSERT OR IGNORE INTO badwords (guild_id, word) VALUES (?, ?)",
            (guild_id, normalized),
        )
        words = await self.get_badwords(guild_id)
        words.add(normalized)

    async def remove_badword(self, guild_id: int, word: str) -> None:
        normalized = word.strip().lower()
        await self.db.execute("DELETE FROM badwords WHERE guild_id = ? AND word = ?", (guild_id, normalized))
        words = await self.get_badwords(guild_id)
        words.discard(normalized)

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int, bool]:
        row = await self.db.fetchone("SELECT xp, level FROM xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if row is None:
            xp = amount
            level = 1
            await self.db.execute(
                "INSERT INTO xp (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, xp, level),
            )
        else:
            xp = int(row["xp"]) + amount
            level = int(row["level"])

        leveled_up = False
        while xp >= self._xp_for_next_level(level):
            xp -= self._xp_for_next_level(level)
            level += 1
            leveled_up = True

        await self.db.execute(
            "INSERT INTO xp (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, level=excluded.level",
            (guild_id, user_id, xp, level),
        )
        self.cache.xp[(guild_id, user_id)] = (xp, level)
        return xp, level, leveled_up

    async def get_xp(self, guild_id: int, user_id: int) -> tuple[int, int]:
        cached = self.cache.xp.get((guild_id, user_id))
        if cached is not None:
            return cached
        row = await self.db.fetchone("SELECT xp, level FROM xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        if row is None:
            return (0, 1)
        result = (int(row["xp"]), int(row["level"]))
        self.cache.xp[(guild_id, user_id)] = result
        return result

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list[tuple[int, int, int]]:
        rows = await self.db.fetchall(
            "SELECT user_id, xp, level FROM xp WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
            (guild_id, limit),
        )
        return [(int(r["user_id"]), int(r["xp"]), int(r["level"])) for r in rows]

    async def set_custom_command(self, guild_id: int, name: str, response: str) -> None:
        await self.db.execute(
            "INSERT INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, name) DO UPDATE SET response = excluded.response",
            (guild_id, name, response),
        )
        commands = self.cache.custom_commands.setdefault(guild_id, {})
        commands[name] = response

    async def remove_custom_command(self, guild_id: int, name: str) -> None:
        await self.db.execute("DELETE FROM custom_commands WHERE guild_id = ? AND name = ?", (guild_id, name))
        commands = self.cache.custom_commands.setdefault(guild_id, {})
        commands.pop(name, None)

    async def list_custom_commands(self, guild_id: int) -> dict[str, str]:
        cached = self.cache.custom_commands.get(guild_id)
        if cached is not None:
            return cached
        rows = await self.db.fetchall("SELECT name, response FROM custom_commands WHERE guild_id = ?", (guild_id,))
        data = {str(r["name"]): str(r["response"]) for r in rows}
        self.cache.custom_commands[guild_id] = data
        return data

    async def add_scheduled_message(
        self,
        guild_id: int,
        channel_id: int,
        message: str,
        interval_seconds: int,
        next_run_ts: int,
    ) -> None:
        await self.db.execute(
            "INSERT INTO scheduled_messages (guild_id, channel_id, message, interval_seconds, next_run_ts) VALUES (?, ?, ?, ?, ?)",
            (guild_id, channel_id, message, interval_seconds, next_run_ts),
        )

    async def get_due_scheduled(self, now_ts: int) -> list[dict[str, int | str]]:
        rows = await self.db.fetchall(
            "SELECT id, guild_id, channel_id, message, interval_seconds, next_run_ts FROM scheduled_messages WHERE next_run_ts <= ?",
            (now_ts,),
        )
        return [dict(r) for r in rows]

    async def bump_scheduled(self, sched_id: int, next_run_ts: int) -> None:
        await self.db.execute("UPDATE scheduled_messages SET next_run_ts = ? WHERE id = ?", (next_run_ts, sched_id))

    async def add_reminder(self, guild_id: int | None, channel_id: int, user_id: int, message: str, due_ts: int) -> None:
        await self.db.execute(
            "INSERT INTO reminders (guild_id, channel_id, user_id, message, due_ts) VALUES (?, ?, ?, ?, ?)",
            (guild_id, channel_id, user_id, message, due_ts),
        )

    async def get_due_reminders(self, now_ts: int) -> list[dict[str, int | str | None]]:
        rows = await self.db.fetchall(
            "SELECT id, guild_id, channel_id, user_id, message, due_ts FROM reminders WHERE due_ts <= ?",
            (now_ts,),
        )
        return [dict(r) for r in rows]

    async def delete_reminder(self, reminder_id: int) -> None:
        await self.db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    async def set_reaction_role(self, guild_id: int, message_id: int, emoji: str, role_id: int) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO reaction_roles (guild_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?)",
            (guild_id, message_id, emoji, role_id),
        )
        message_map = self.cache.reaction_roles.setdefault(message_id, {})
        message_map[emoji] = role_id

    async def get_reaction_roles_for_message(self, message_id: int) -> dict[str, int]:
        cached = self.cache.reaction_roles.get(message_id)
        if cached is not None:
            return cached
        rows = await self.db.fetchall("SELECT emoji, role_id FROM reaction_roles WHERE message_id = ?", (message_id,))
        data = {str(r["emoji"]): int(r["role_id"]) for r in rows}
        self.cache.reaction_roles[message_id] = data
        return data

    @staticmethod
    def _xp_for_next_level(level: int) -> int:
        return 100 + (level - 1) * 50
