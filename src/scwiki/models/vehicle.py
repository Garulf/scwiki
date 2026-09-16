from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, nested, nested_list, text
from scwiki.models.common import Crew, Dimension, Image, ManufacturerRef, Shield, Signature, Speed


@dataclass(frozen=True)
class Vehicle(Model):
    uuid: str | None = None
    name: str | None = None
    game_name: str | None = None
    slug: str | None = None
    class_name: str | None = None
    manufacturer: ManufacturerRef | None = None
    dimension: Dimension | None = None
    crew: Crew | None = None
    speed: Speed | None = None
    shield: Shield | None = None
    signature: Signature | None = None
    health: float | None = None
    mass_total: float | None = None
    cargo_capacity: float | None = None
    vehicle_inventory: float | None = None
    size_class: int | None = None
    career: str | None = None
    role: str | None = None
    msrp: float | None = None
    pledge_url: str | None = None
    production_status: str | None = None
    description: str | None = None
    images: tuple[Image, ...] = ()
    is_spaceship: bool | None = None
    is_gravlev: bool | None = None
    is_vehicle: bool | None = None
    version: str | None = None
    updated_at: str | None = None

    _derive: ClassVar = {
        "manufacturer": nested("manufacturer", ManufacturerRef),
        "dimension": nested("dimension", Dimension),
        "crew": nested("crew", Crew),
        "speed": nested("speed", Speed),
        "shield": nested("shield", Shield),
        "signature": nested("signature", Signature),
        "production_status": text("production_status"),
        "description": text("description"),
        "images": nested_list("images", Image),
    }
