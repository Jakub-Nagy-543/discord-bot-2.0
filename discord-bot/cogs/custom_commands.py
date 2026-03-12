from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import safe_reply


class CustomCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="custom", description="Manage custom slash commands")
        self.group.add_command(self.add)
        self.group.add_command(self.remove)
        self.group.add_command(self.list)
        self.bot.tree.add_command(self.group)
        self._registered_dynamic: set[str] = set()

    async def cog_load(self) -> None:
        rows = await self.bot.db.fetchall("SELECT DISTINCT name FROM custom_commands")
        for row in rows:
            name = str(row["name"])
            await self._ensure_dynamic_command(name)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.group.name)
        for name in list(self._registered_dynamic):
            self.bot.tree.remove_command(name)

    @staticmethod
    def _is_valid_name(name: str) -> bool:
        return re.fullmatch(r"[a-z0-9_]{1,32}", name) is not None

    async def _ensure_dynamic_command(self, name: str) -> None:
        if name in self._registered_dynamic:
            return
        if self.bot.tree.get_command(name) is not None:
            return

        async def _dynamic(interaction: discord.Interaction) -> None:
            if interaction.guild_id is None:
                await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
                return

            commands_map = await self.bot.storage.list_custom_commands(interaction.guild_id)
            response = commands_map.get(name)
            if response is None:
                await safe_reply(interaction, "This custom command is not configured on this server.", ephemeral=True)
                return
            await safe_reply(interaction, response)

        cmd = app_commands.Command(name=name, description="Custom server command", callback=_dynamic)
        self.bot.tree.add_command(cmd)
        self._registered_dynamic.add(name)

    async def _remove_dynamic_if_unused(self, name: str) -> None:
        row = await self.bot.db.fetchone("SELECT 1 FROM custom_commands WHERE name = ? LIMIT 1", (name,))
        if row is None:
            self.bot.tree.remove_command(name)
            self._registered_dynamic.discard(name)

    @app_commands.command(name="add", description="Create or update a custom slash command")
    @app_commands.describe(name="Command name", response="Response text")
    async def add(self, interaction: discord.Interaction, name: str, response: str) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        normalized = name.strip().lower()
        if normalized in {"help", "custom", "config", "ticket", "utility", "info", "moderation"}:
            await safe_reply(interaction, "This command name is reserved.", ephemeral=True)
            return
        if not self._is_valid_name(normalized):
            await safe_reply(interaction, "Invalid name. Use lowercase letters, numbers, underscore (max 32).", ephemeral=True)
            return

        await self.bot.storage.set_custom_command(interaction.guild_id, normalized, response)
        await self._ensure_dynamic_command(normalized)
        await self.bot.tree.sync()
        await safe_reply(interaction, f"Custom command `/{normalized}` saved.", ephemeral=True)

    @app_commands.command(name="remove", description="Remove a custom slash command")
    @app_commands.describe(name="Command name")
    async def remove(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        normalized = name.strip().lower()
        await self.bot.storage.remove_custom_command(interaction.guild_id, normalized)
        await self._remove_dynamic_if_unused(normalized)
        await self.bot.tree.sync()
        await safe_reply(interaction, f"Custom command `/{normalized}` removed.", ephemeral=True)

    @app_commands.command(name="list", description="List custom commands for this server")
    async def list(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        commands_map = await self.bot.storage.list_custom_commands(interaction.guild_id)
        if not commands_map:
            await safe_reply(interaction, "No custom commands configured.", ephemeral=True)
            return

        lines = ["Custom commands:"]
        for name in sorted(commands_map.keys()):
            lines.append(f"/{name}")
        await safe_reply(interaction, "\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomCommandsCog(bot))
