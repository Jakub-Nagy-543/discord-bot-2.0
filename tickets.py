from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import safe_reply


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="ticket", description="Support ticket commands")
        self.group.add_command(self.create)
        self.bot.tree.add_command(self.group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.group.name)

    @app_commands.command(name="create", description="Create a private support ticket")
    async def create(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await safe_reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await safe_reply(interaction, "Could not resolve your member profile.", ephemeral=True)
            return

        config = await self.bot.storage.get_guild_config(guild.id)
        category_id = config.get("ticket_category_id")
        category = guild.get_channel(int(category_id)) if category_id else None
        if category_id and not isinstance(category, discord.CategoryChannel):
            category = None

        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing is not None:
            await safe_reply(interaction, f"You already have a ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # Allow moderator roles with manage_guild permission.
        for role in guild.roles:
            if role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.id}",
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user}",
            )
            await channel.send(
                f"Hello {interaction.user.mention}, support will be with you shortly."
            )
            await safe_reply(interaction, f"Ticket created: {channel.mention}", ephemeral=True)
        except discord.Forbidden:
            await safe_reply(interaction, "I do not have permission to create ticket channels.", ephemeral=True)
        except discord.HTTPException as exc:
            print(f"Ticket creation failed: {exc}")
            await safe_reply(interaction, "Ticket could not be created due to a Discord API error.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketsCog(bot))
