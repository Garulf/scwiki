from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, nested, nested_list, text
from scwiki.models.common import Dimension, Image, ManufacturerRef


@dataclass(frozen=True)
class Item(Model):
    uuid: str | None = None
    name: str | None = None
    slug: str | None = None
    class_name: str | None = None
    type: str | None = None
    sub_type: str | None = None
    classification: str | None = None
    size: int | None = None
    grade: str | None = None
    rarity: str | None = None
    manufacturer: ManufacturerRef | None = None
    dimension: Dimension | None = None
    mass: float | None = None
    description: str | None = None
    images: tuple[Image, ...] = ()
    web_url: str | None = None
    version: str | None = None
    updated_at: str | None = None

    _derive: ClassVar = {
        "manufacturer": nested("manufacturer", ManufacturerRef),
        "dimension": nested("dimension", Dimension),
        "description": text("description"),
        "images": nested_list("images", Image),
    }


@dataclass(frozen=True)
class Weapon(Item):
    pass


@dataclass(frozen=True)
class Armor(Item):
    pass


@dataclass(frozen=True)
class Clothing(Item):
    pass


@dataclass(frozen=True)
class Food(Item):
    pass


@dataclass(frozen=True)
class VehicleItem(Item):
    pass


@dataclass(frozen=True)
class VehicleWeapon(Item):
    pass


@dataclass(frozen=True)
class WeaponAttachment(Item):
    pass
