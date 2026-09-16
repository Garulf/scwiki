from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Model


@dataclass(frozen=True)
class GameVersion(Model):
    code: str | None = None
    channel: str | None = None
    is_default: bool | None = None
    released_at: str | None = None
