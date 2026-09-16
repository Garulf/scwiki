from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, Value, nested


@dataclass(frozen=True)
class LocationType(Value):
    uuid: str | None = None
    name: str | None = None
    classification: str | None = None


@dataclass(frozen=True)
class LocationRef(Value):
    uuid: str | None = None
    name: str | None = None
    type_name: str | None = None
    slug: str | None = None


@dataclass(frozen=True)
class Location(Model):
    uuid: str | None = None
    name: str | None = None
    slug: str | None = None
    type: LocationType | None = None
    system: str | None = None
    parent: LocationRef | None = None
    designation: str | None = None
    description: str | None = None
    web_url: str | None = None
    version: str | None = None

    _derive: ClassVar = {
        "type": nested("type", LocationType),
        "parent": nested("parent", LocationRef),
    }


@dataclass(frozen=True)
class Position(Model):
    uuid: str | None = None
    name: str | None = None
    type: str | None = None
    system: str | None = None
    parent_uuid: str | None = None
    hidden: bool | None = None
