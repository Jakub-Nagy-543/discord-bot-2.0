from __future__ import annotations

import re
from datetime import datetime, timezone

import discord


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_uptime(start_time: datetime) -> str:
    delta = utcnow() - start_time
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    return f"{hours}h {minutes}m {seconds}s"


def parse_duration_to_seconds(raw: str) -> int | None:
    """Parse values like 10s, 5m, 2h, 1d into seconds."""
    match = re.fullmatch(r"\s*(\d+)\s*([smhdSMHD])\s*", raw)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2).lower()
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    seconds = value * multiplier
    if seconds <= 0 or seconds > 604800:
        return None
    return seconds


async def safe_reply(interaction: discord.Interaction, message: str, ephemeral: bool = False) -> None:
    """Respond safely even if the interaction was already acknowledged."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(message, ephemeral=ephemeral)
    except discord.Forbidden:
        print("Cannot send interaction response: missing permissions.")
    except discord.HTTPException as exc:
        print(f"Failed to send interaction response: {exc}")
