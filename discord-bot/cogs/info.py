from __future__ import annotations

from datetime import timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import format_uptime, safe_reply


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.info_group = app_commands.Group(name="info", description="Information commands")

        self.info_group.add_command(self.server)
        self.info_group.add_command(self.serverstats)
        self.info_group.add_command(self.avatar)
        self.info_group.add_command(self.userinfo)
        self.info_group.add_command(self.roles)
        self.info_group.add_command(self.servericon)
        self.info_group.add_command(self.botinfo)
        self.info_group.add_command(self.rules)
        self.info_group.add_command(self.help)

        self.bot.tree.add_command(self.info_group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.info_group.name)

    @app_commands.command(name="server", description="Shows server information")
    async def server(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        await safe_reply(
            interaction,
            f"Server: {guild.name}\nID: {guild.id}\nMembers: {guild.member_count}",
        )

    @app_commands.command(name="serverstats", description="Shows server statistics")
    async def serverstats(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        total_members = guild.member_count or 0
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)

        await safe_reply(
            interaction,
            f"Stats for {guild.name}:\n"
            f"Total members: {total_members}\n"
            f"Online members: {online_members}\n"
            f"Text channels: {text_channels}\n"
            f"Voice channels: {voice_channels}",
        )

    @app_commands.command(name="avatar", description="Shows a user avatar")
    @app_commands.describe(user="User to display")
    async def avatar(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        target = user or interaction.user
        await safe_reply(interaction, f"Avatar for {target.mention}: {target.display_avatar.url}")

    @app_commands.command(name="userinfo", description="Shows detailed info about a user")
    @app_commands.describe(user="User to inspect")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        if interaction.guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        member = user or interaction.user
        if not isinstance(member, discord.Member):
            await safe_reply(interaction, "Could not resolve this user in the server.", ephemeral=True)
            return

        joined_at = member.joined_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if member.joined_at else "Unknown"
        created_at = member.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        roles_text = ", ".join(roles) if roles else "No special roles"

        await safe_reply(
            interaction,
            f"User: {member.mention}\n"
            f"Name: {member}\n"
            f"ID: {member.id}\n"
            f"Account created: {created_at}\n"
            f"Joined server: {joined_at}\n"
            f"Roles: {roles_text}\n"
            f"Avatar: {member.display_avatar.url}",
        )

    @app_commands.command(name="roles", description="Shows user roles")
    @app_commands.describe(user="User to inspect")
    async def roles(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        if interaction.guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        member = user or interaction.user
        if not isinstance(member, discord.Member):
            await safe_reply(interaction, "Could not resolve this user in the server.", ephemeral=True)
            return

        role_list = [role.mention for role in member.roles if role.name != "@everyone"]
        role_text = ", ".join(role_list) if role_list else "No special roles"
        await safe_reply(interaction, f"Roles for {member.mention}: {role_text}")

    @app_commands.command(name="servericon", description="Shows the server icon")
    async def servericon(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        if guild.icon is None:
            await safe_reply(interaction, "This server has no icon.")
            return

        await safe_reply(interaction, f"Server icon for {guild.name}: {guild.icon.url}")

    @app_commands.command(name="botinfo", description="Shows bot information")
    async def botinfo(self, interaction: discord.Interaction) -> None:
        if self.bot.user is None:
            await safe_reply(interaction, "The bot is not ready yet.", ephemeral=True)
            return

        await safe_reply(
            interaction,
            f"Bot: {self.bot.user.name}\n"
            f"Version: {self.bot.version}\n"
            f"Uptime: {format_uptime(self.bot.start_time)}\n"
            f"Servers: {len(self.bot.guilds)}",
        )

    @app_commands.command(name="rules", description="Shows server rules")
    async def rules(self, interaction: discord.Interaction) -> None:
        rules_message = (
            "Here are the server rules:\n"
            "1. Be respectful to everyone.\n"
            "2. No spamming or advertising.\n"
            "3. Follow Discord's Terms of Service."
        )
        await safe_reply(interaction, rules_message)

    @app_commands.command(name="help", description="Lists all commands grouped by category")
    async def help(self, interaction: discord.Interaction) -> None:
        message = (
            "**Utility**\n"
            "/utility hello - Greets the user\n"
            "/utility ping - Shows bot latency\n"
            "/utility uptime - Shows how long the bot has been online\n"
            "/utility remind - Sets a reminder after a specified time\n"
            "/utility poll - Creates a poll with two options\n\n"
            "**Info**\n"
            "/info server - Shows server information\n"
            "/info serverstats - Shows server statistics\n"
            "/info avatar - Shows a user avatar\n"
            "/info userinfo - Shows detailed info about a user\n"
            "/info roles - Shows user roles\n"
            "/info servericon - Shows the server icon\n"
            "/info botinfo - Shows bot information\n"
            "/info rules - Shows server rules\n"
            "/info help - Lists all commands grouped by category\n\n"
            "**Moderation**\n"
            "/moderation moderate - Kick or ban a user if allowed\n\n"
            "**Other**\n"
            "/ticket create, /level, /rank, /leaderboard, /custom ..., /schedule ..., /config ..."
        )
        await safe_reply(interaction, message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InfoCog(bot))
