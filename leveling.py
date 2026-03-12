from __future__ import annotations

import random
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import safe_reply, utcnow


class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldowns: dict[tuple[int, int], float] = defaultdict(float)
        self.cooldown_seconds = 45

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command("level")
        self.bot.tree.remove_command("rank")
        self.bot.tree.remove_command("leaderboard")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        key = (message.guild.id, message.author.id)
        now_ts = utcnow().timestamp()
        if now_ts - self.xp_cooldowns[key] < self.cooldown_seconds:
            return

        self.xp_cooldowns[key] = now_ts
        gained = random.randint(8, 16)
        xp, level, leveled_up = await self.bot.storage.add_xp(message.guild.id, message.author.id, gained)

        if leveled_up:
            try:
                await message.channel.send(f"{message.author.mention} leveled up to **{level}**!")
            except (discord.Forbidden, discord.HTTPException):
                pass

    @app_commands.command(name="level", description="Show your current level")
    async def level(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        xp, level = await self.bot.storage.get_xp(interaction.guild_id, interaction.user.id)
        await safe_reply(interaction, f"You are level **{level}** with **{xp} XP** toward the next level.")

    @app_commands.command(name="rank", description="Show XP stats for a user")
    @app_commands.describe(user="User to inspect")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        target = user or interaction.user
        xp, level = await self.bot.storage.get_xp(interaction.guild_id, target.id)
        await safe_reply(interaction, f"{target.mention} is level **{level}** with **{xp} XP**.")

    @app_commands.command(name="leaderboard", description="Show top users by level and XP")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        top = await self.bot.storage.get_leaderboard(interaction.guild.id, limit=10)
        if not top:
            await safe_reply(interaction, "No XP data yet.")
            return

        lines = ["**Leaderboard**"]
        for idx, (user_id, xp, level) in enumerate(top, start=1):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            lines.append(f"{idx}. {name} - Level {level}, {xp} XP")

        await safe_reply(interaction, "\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    cog = LevelingCog(bot)
    await bot.add_cog(cog)
    if bot.tree.get_command("level") is None:
        bot.tree.add_command(cog.level)
    if bot.tree.get_command("rank") is None:
        bot.tree.add_command(cog.rank)
    if bot.tree.get_command("leaderboard") is None:
        bot.tree.add_command(cog.leaderboard)
