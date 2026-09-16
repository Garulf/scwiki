from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Model


@dataclass(frozen=True)
class Blueprint(Model):
    uuid: str | None = None
    key: str | None = None
    output_name: str | None = None
    output_class: str | None = None
    craft_time_seconds: float | None = None
    ingredient_count: int | None = None
    is_available_by_default: bool | None = None
    web_url: str | None = None
    game_version: str | None = None
