from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.cache import MemoryCache
from utils.database import Database
from utils.helpers import safe_reply
from utils.storage import Storage

BOT_VERSION = "2.0.0"

# Required for welcome, automod, and leveling systems.
intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class MyBot(commands.AutoShardedBot):
    def __init__(self) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.version = BOT_VERSION
        self.start_time = datetime.now(timezone.utc)
        self.db = Database(str(Path("data") / "bot.db"))
        self.cache = MemoryCache()
        self.storage = Storage(self.db, self.cache)

    async def setup_hook(self) -> None:
        await self.db.initialize()

        initial_extensions = [
            "cogs.utility",
            "cogs.info",
            "cogs.moderation",
            "cogs.automod",
            "cogs.tickets",
            "cogs.leveling",
            "cogs.custom_commands",
            "cogs.scheduler",
            "cogs.config",
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension: {ext}")
            except Exception as exc:
                print(f"Failed to load extension {ext}: {exc}")

        try:
            await self.tree.sync()
            print("Slash commands synced.")
        except Exception as exc:
            print(f"Slash sync failed: {exc}")


bot = MyBot()


@bot.event
async def on_ready() -> None:
    shard_info = f"{len(bot.shards)} shards" if bot.shards else "single shard"
    print(f"Logged in as {bot.user} ({shard_info})")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    print(f"Slash command error: {error}")

    if isinstance(error, app_commands.MissingPermissions):
        await safe_reply(interaction, "You do not have permission to run this command.", ephemeral=True)
        return

    if isinstance(error, app_commands.BotMissingPermissions):
        await safe_reply(interaction, "I do not have the required permissions for this command.", ephemeral=True)
        return

    if isinstance(error, app_commands.CommandOnCooldown):
        await safe_reply(interaction, "This command is on cooldown. Try again in a moment.", ephemeral=True)
        return

    await safe_reply(interaction, "An unexpected error occurred while running this command.", ephemeral=True)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in environment variables.")
    bot.run(token)


if __name__ == "__main__":
    main()
