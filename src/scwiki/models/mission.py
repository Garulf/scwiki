from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, Value, nested


@dataclass(frozen=True)
class FactionRef(Value):
    uuid: str | None = None
    name: str | None = None
    faction_type: str | None = None
    lawful: bool | None = None


@dataclass(frozen=True)
class Mission(Model):
    uuid: str | None = None
    title: str | None = None
    debug_name: str | None = None
    description: str | None = None
    mission_type: str | None = None
    mission_giver: str | None = None
    faction: FactionRef | None = None
    illegal: bool | None = None
    has_combat: bool | None = None
    reward_min: float | None = None
    reward_max: float | None = None
    web_url: str | None = None
    game_version: str | None = None

    _derive: ClassVar = {
        "title": lambda d: d.get("title") or d.get("debug_name"),
        "faction": nested("faction", FactionRef),
    }
