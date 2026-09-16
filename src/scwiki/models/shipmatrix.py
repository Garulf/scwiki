from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, nested, text
from scwiki.models.common import ManufacturerRef


@dataclass(frozen=True)
class ShipMatrixVehicle(Model):
    id: int | None = None
    name: str | None = None
    slug: str | None = None
    manufacturer: ManufacturerRef | None = None
    production_status: str | None = None
    type: str | None = None
    size: str | None = None
    msrp: float | None = None
    pledge_url: str | None = None
    description: str | None = None
    updated_at: str | None = None

    _derive: ClassVar = {
        "manufacturer": nested("manufacturer", ManufacturerRef),
        "production_status": text("production_status"),
        "type": text("type"),
        "size": text("size"),
        "description": text("description"),
    }
