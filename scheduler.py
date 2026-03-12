from __future__ import annotations

from datetime import timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.helpers import parse_duration_to_seconds, safe_reply, utcnow


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="schedule", description="Scheduled message commands")
        self.group.add_command(self.create)
        self.bot.tree.add_command(self.group)

        self.scheduled_loop.start()
        self.reminder_loop.start()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.group.name)
        self.scheduled_loop.cancel()
        self.reminder_loop.cancel()

    @tasks.loop(seconds=30)
    async def scheduled_loop(self) -> None:
        now_ts = int(utcnow().timestamp())
        due = await self.bot.storage.get_due_scheduled(now_ts)
        for item in due:
            channel = self.bot.get_channel(int(item["channel_id"]))
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(str(item["message"]))
                except (discord.Forbidden, discord.HTTPException):
                    pass

            interval = int(item["interval_seconds"])
            await self.bot.storage.bump_scheduled(int(item["id"]), now_ts + interval)

    @tasks.loop(seconds=20)
    async def reminder_loop(self) -> None:
        now_ts = int(utcnow().timestamp())
        due = await self.bot.storage.get_due_reminders(now_ts)
        for item in due:
            channel = self.bot.get_channel(int(item["channel_id"]))
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    await channel.send(f"<@{item['user_id']}> reminder: {item['message']}")
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await self.bot.storage.delete_reminder(int(item["id"]))

    @app_commands.command(name="create", description="Create an automatic scheduled message")
    @app_commands.describe(
        channel="Target channel",
        message="Message content",
        interval="Interval format: 10m, 1h, 24h",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        interval: str,
    ) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        seconds = parse_duration_to_seconds(interval)
        if seconds is None or seconds < 60:
            await safe_reply(interaction, "Invalid interval. Use 1m to 7d (e.g. 24h).", ephemeral=True)
            return

        next_run_ts = int(utcnow().timestamp()) + seconds
        await self.bot.storage.add_scheduled_message(interaction.guild_id, channel.id, message, seconds, next_run_ts)
        await safe_reply(interaction, f"Scheduled message created for {channel.mention} every {interval}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SchedulerCog(bot))
