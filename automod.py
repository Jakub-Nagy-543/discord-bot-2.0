from __future__ import annotations

from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands, tasks

from utils.helpers import utcnow


class AutoModCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_windows: dict[tuple[int, int], deque[float]] = defaultdict(deque)
        self.spam_window_seconds = 6
        self.spam_limit = 6
        self.mention_limit = 8
        self.cleanup_spam_cache.start()

    async def cog_unload(self) -> None:
        self.cleanup_spam_cache.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_spam_cache(self) -> None:
        cutoff = utcnow().timestamp() - 60
        stale_keys = []
        for key, timestamps in self.message_windows.items():
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if not timestamps:
                stale_keys.append(key)
        for key in stale_keys:
            self.message_windows.pop(key, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        config = await self.bot.storage.get_guild_config(member.guild.id)
        channel_id = config.get("welcome_channel_id")
        if not channel_id:
            return

        channel = member.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return

        me = member.guild.me
        if me and not channel.permissions_for(me).send_messages:
            return

        embed = discord.Embed(
            title="Welcome!",
            description=(
                f"Welcome {member.mention} to **{member.guild.name}**.\n"
                f"You are member **#{member.guild.member_count}**."
            ),
            color=discord.Color.green(),
            timestamp=utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            return

        emoji = str(payload.emoji)
        mapping = await self.bot.storage.get_reaction_roles_for_message(payload.message_id)
        role_id = mapping.get(emoji)
        if not role_id:
            return

        role = guild.get_role(role_id)
        if role is None:
            return

        try:
            await member.add_roles(role, reason="Reaction role assignment")
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            return

        emoji = str(payload.emoji)
        mapping = await self.bot.storage.get_reaction_roles_for_message(payload.message_id)
        role_id = mapping.get(emoji)
        if not role_id:
            return

        role = guild.get_role(role_id)
        if role is None:
            return

        try:
            await member.remove_roles(role, reason="Reaction role removal")
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        # Mention spam check.
        if len(message.mentions) >= self.mention_limit:
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, too many mentions in one message.",
                    delete_after=10,
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        # Bad words check.
        badwords = await self.bot.storage.get_badwords(message.guild.id)
        lowered = message.content.lower()
        if badwords and any(badword in lowered for badword in badwords):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, that message contained blocked language.",
                    delete_after=10,
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        # Basic spam detection by message frequency.
        key = (message.guild.id, message.author.id)
        now_ts = utcnow().timestamp()
        bucket = self.message_windows[key]
        bucket.append(now_ts)

        while bucket and now_ts - bucket[0] > self.spam_window_seconds:
            bucket.popleft()

        if len(bucket) >= self.spam_limit:
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, please slow down (spam detected).",
                    delete_after=10,
                )
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoModCog(bot))
