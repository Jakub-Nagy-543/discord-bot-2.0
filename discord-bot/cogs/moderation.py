from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import safe_reply, utcnow


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="moderation", description="Moderation commands")
        self.group.add_command(self.moderate)
        self.bot.tree.add_command(self.group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.group.name)

    async def _log_action(
        self,
        guild: discord.Guild,
        moderator: discord.abc.User,
        target: discord.Member,
        action: str,
    ) -> None:
        config = await self.bot.storage.get_guild_config(guild.id)
        channel_id = config.get("modlog_channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(title="Moderation Action", color=discord.Color.orange(), timestamp=utcnow())
        embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=False)
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=False)
        embed.add_field(name="Action", value=action, inline=False)
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @app_commands.command(name="moderate", description="Kick or ban a user if permissions allow")
    @app_commands.describe(action="Action type", user="Target user")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="kick", value="kick"),
            app_commands.Choice(name="ban", value="ban"),
        ]
    )
    async def moderate(self, interaction: discord.Interaction, action: app_commands.Choice[str], user: discord.Member) -> None:
        guild = interaction.guild
        if guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await safe_reply(interaction, "Could not verify your permissions.", ephemeral=True)
            return

        if action.value == "kick" and not interaction.user.guild_permissions.kick_members:
            await safe_reply(interaction, "You need the Kick Members permission.", ephemeral=True)
            return
        if action.value == "ban" and not interaction.user.guild_permissions.ban_members:
            await safe_reply(interaction, "You need the Ban Members permission.", ephemeral=True)
            return

        me = guild.me
        if me is None:
            await safe_reply(interaction, "Could not verify bot permissions.", ephemeral=True)
            return

        if action.value == "kick" and not me.guild_permissions.kick_members:
            await safe_reply(interaction, "I need the Kick Members permission.", ephemeral=True)
            return
        if action.value == "ban" and not me.guild_permissions.ban_members:
            await safe_reply(interaction, "I need the Ban Members permission.", ephemeral=True)
            return

        if user == interaction.user:
            await safe_reply(interaction, "You cannot moderate yourself.", ephemeral=True)
            return
        if user == guild.owner:
            await safe_reply(interaction, "You cannot moderate the server owner.", ephemeral=True)
            return

        try:
            if action.value == "kick":
                await user.kick(reason=f"Moderated by {interaction.user}")
                await safe_reply(interaction, f"{user} was kicked.")
                await self._log_action(guild, interaction.user, user, "kick")
            else:
                await user.ban(reason=f"Moderated by {interaction.user}")
                await safe_reply(interaction, f"{user} was banned.")
                await self._log_action(guild, interaction.user, user, "ban")
        except discord.Forbidden:
            await safe_reply(interaction, "Action failed due to role hierarchy or missing permissions.", ephemeral=True)
        except discord.HTTPException as exc:
            print(f"Moderation action failed: {exc}")
            await safe_reply(interaction, "Action failed due to a Discord API error.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
