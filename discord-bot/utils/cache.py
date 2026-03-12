from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryCache:
    guild_config: dict[int, dict[str, Any]] = field(default_factory=dict)
    badwords: dict[int, set[str]] = field(default_factory=dict)
    xp: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    custom_commands: dict[int, dict[str, str]] = field(default_factory=dict)
    reaction_roles: dict[int, dict[str, int]] = field(default_factory=dict)

    def clear_guild(self, guild_id: int) -> None:
        self.guild_config.pop(guild_id, None)
        self.badwords.pop(guild_id, None)
        self.custom_commands.pop(guild_id, None)

    def get_config(self, guild_id: int) -> dict[str, Any] | None:
        return self.guild_config.get(guild_id)

    def set_config(self, guild_id: int, config: dict[str, Any]) -> None:
        self.guild_config[guild_id] = config
