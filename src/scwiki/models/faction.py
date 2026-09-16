from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Model


@dataclass(frozen=True)
class Faction(Model):
    uuid: str | None = None
    name: str | None = None
    faction_type: str | None = None
    lawful: bool | None = None
    is_npc: bool | None = None
    focus: str | None = None
    headquarters: str | None = None
    description: str | None = None
