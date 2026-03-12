from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import format_uptime, parse_duration_to_seconds, safe_reply, utcnow


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.utility_group = app_commands.Group(name="utility", description="Utility commands")

        self.utility_group.add_command(self.hello)
        self.utility_group.add_command(self.ping)
        self.utility_group.add_command(self.uptime)
        self.utility_group.add_command(self.remind)
        self.utility_group.add_command(self.poll)

        self.bot.tree.add_command(self.utility_group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.utility_group.name)

    @app_commands.command(name="hello", description="Greets the user")
    async def hello(self, interaction: discord.Interaction) -> None:
        await safe_reply(interaction, f"Hello, {interaction.user.mention}!")

    @app_commands.command(name="ping", description="Shows bot latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        await safe_reply(interaction, f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="uptime", description="Shows how long the bot has been online")
    async def uptime(self, interaction: discord.Interaction) -> None:
        await safe_reply(interaction, f"Uptime: {format_uptime(self.bot.start_time)}")

    @app_commands.command(name="remind", description="Sets a reminder after a specified time")
    @app_commands.describe(
        time="Time format: 10s, 5m, 2h, 1d",
        message="Reminder message",
    )
    async def remind(self, interaction: discord.Interaction, time: str, message: str) -> None:
        seconds = parse_duration_to_seconds(time)
        if seconds is None:
            await safe_reply(
                interaction,
                "Invalid time format. Use 10s, 5m, 2h, or 1d (max 7d).",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if channel is None:
            await safe_reply(interaction, "Could not find the target channel.", ephemeral=True)
            return

        due_ts = int(utcnow().timestamp()) + seconds
        guild_id = interaction.guild_id
        await self.bot.storage.add_reminder(guild_id, channel.id, interaction.user.id, message, due_ts)
        await safe_reply(interaction, f"Reminder set for {time.strip().lower()}.", ephemeral=True)

    @app_commands.command(name="poll", description="Creates a poll with two options")
    @app_commands.describe(
        question="Question to vote on",
        option1="First option",
        option2="Second option",
    )
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str) -> None:
        poll_text = f"**{question}**\n1️⃣ {option1}\n2️⃣ {option2}"
        await safe_reply(interaction, poll_text)

        try:
            poll_message = await interaction.original_response()
            await poll_message.add_reaction("1️⃣")
            await poll_message.add_reaction("2️⃣")
        except discord.Forbidden:
            await safe_reply(
                interaction,
                "I can send the poll, but I do not have permission to add reactions.",
                ephemeral=True,
            )
        except discord.HTTPException as exc:
            print(f"Poll reaction add failed: {exc}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))
