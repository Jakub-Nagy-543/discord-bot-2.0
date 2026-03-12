from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import safe_reply


class ConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="config", description="Server configuration commands")
        self.group.add_command(self.set_welcome_channel)
        self.group.add_command(self.set_modlog_channel)
        self.group.add_command(self.set_ticket_category)
        self.group.add_command(self.add_badword)
        self.group.add_command(self.remove_badword)
        self.group.add_command(self.create_reaction_roles)
        self.bot.tree.add_command(self.group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.group.name)

    @staticmethod
    def _is_admin(user: discord.abc.User) -> bool:
        return isinstance(user, discord.Member) and user.guild_permissions.manage_guild

    @app_commands.command(name="set_welcome_channel", description="Set the welcome channel")
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        await self.bot.storage.set_config_value(interaction.guild_id, "welcome_channel_id", channel.id)
        await safe_reply(interaction, f"Welcome channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set_modlog_channel", description="Set the moderation log channel")
    async def set_modlog_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        await self.bot.storage.set_config_value(interaction.guild_id, "modlog_channel_id", channel.id)
        await safe_reply(interaction, f"Moderation log channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set_ticket_category", description="Set the ticket category")
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        await self.bot.storage.set_config_value(interaction.guild_id, "ticket_category_id", category.id)
        await safe_reply(interaction, f"Ticket category set to **{category.name}**.", ephemeral=True)

    @app_commands.command(name="add_badword", description="Add a banned word for automod")
    async def add_badword(self, interaction: discord.Interaction, word: str) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        await self.bot.storage.add_badword(interaction.guild_id, word)
        await safe_reply(interaction, f"Added bad word: `{word.strip().lower()}`.", ephemeral=True)

    @app_commands.command(name="remove_badword", description="Remove a banned word for automod")
    async def remove_badword(self, interaction: discord.Interaction, word: str) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        await self.bot.storage.remove_badword(interaction.guild_id, word)
        await safe_reply(interaction, f"Removed bad word: `{word.strip().lower()}`.", ephemeral=True)

    @app_commands.command(name="create_reaction_roles", description="Create a reaction-role message (🎮 and 🎨)")
    @app_commands.describe(
        channel="Channel where the message is sent",
        gamer_role="Role assigned by 🎮",
        artist_role="Role assigned by 🎨",
        title="Embed title",
    )
    async def create_reaction_roles(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        gamer_role: discord.Role,
        artist_role: discord.Role,
        title: str = "Choose your roles",
    ) -> None:
        if interaction.guild_id is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return
        if not self._is_admin(interaction.user):
            await safe_reply(interaction, "You need Manage Server permission.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=f"React with 🎮 for {gamer_role.mention}\nReact with 🎨 for {artist_role.mention}",
            color=discord.Color.blurple(),
        )

        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("🎮")
            await msg.add_reaction("🎨")
            await self.bot.storage.set_reaction_role(interaction.guild_id, msg.id, "🎮", gamer_role.id)
            await self.bot.storage.set_reaction_role(interaction.guild_id, msg.id, "🎨", artist_role.id)
            await safe_reply(interaction, f"Reaction roles message created in {channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await safe_reply(interaction, "I do not have permission to send messages/reactions there.", ephemeral=True)
        except discord.HTTPException as exc:
            print(f"Reaction role message creation failed: {exc}")
            await safe_reply(interaction, "Could not create reaction role message.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigCog(bot))
