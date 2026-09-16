from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Model


@dataclass(frozen=True)
class Manufacturer(Model):
    uuid: str | None = None
    code: str | None = None
    name: str | None = None
    link: str | None = None
