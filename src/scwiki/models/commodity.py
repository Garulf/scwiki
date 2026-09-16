from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Model


@dataclass(frozen=True)
class Commodity(Model):
    uuid: str | None = None
    name: str | None = None
    display_name: str | None = None
    slug: str | None = None
    kind: str | None = None
    tier: int | None = None
    is_mineable: bool | None = None
    description: str | None = None
    web_url: str | None = None
