from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, text


@dataclass(frozen=True)
class StarSystem(Model):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    type: str | None = None
    status: str | None = None
    description: str | None = None

    _derive: ClassVar = {"description": text("description")}


@dataclass(frozen=True)
class CelestialObject(Model):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    type: str | None = None
    designation: str | None = None
    description: str | None = None
    system_id: int | None = None
    parent_id: int | None = None
    habitable: bool | None = None

    _derive: ClassVar = {"description": text("description")}
