"""Every resource family the API exposes, with its caching characteristics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
WEEK = timedelta(days=7)


@dataclass(frozen=True)
class Family:
    name: str
    path: str
    versioned: bool
    supports_locale: bool = False
    detail_ttl: timedelta | None = None
    list_ttl: timedelta | None = None
    has_filters: bool = False
    model: str = ""


def _versioned(
    name: str, path: str, model: str, *, locale: bool = True, filters: bool = False
) -> Family:
    return Family(name, path, True, supports_locale=locale, has_filters=filters, model=model)


def _timed(
    name: str,
    path: str,
    model: str,
    detail_ttl: timedelta,
    list_ttl: timedelta,
    *,
    locale: bool = False,
    filters: bool = False,
) -> Family:
    return Family(
        name,
        path,
        False,
        supports_locale=locale,
        detail_ttl=detail_ttl,
        list_ttl=list_ttl,
        has_filters=filters,
        model=model,
    )


_ALL: tuple[Family, ...] = (
    _versioned("vehicles", "vehicles", "Vehicle", locale=False, filters=True),
    _versioned("ground_vehicles", "ground-vehicles", "Vehicle", locale=False),
    _versioned("gravlev_vehicles", "gravlev-vehicles", "Vehicle", locale=False),
    _versioned("items", "items", "Item", filters=True),
    _versioned("weapons", "weapons", "Weapon"),
    _versioned("armor", "armor", "Armor"),
    _versioned("clothes", "clothes", "Clothing"),
    _versioned("food", "food", "Food"),
    _versioned("vehicle_items", "vehicle-items", "VehicleItem"),
    _versioned("vehicle_weapons", "vehicle-weapons", "VehicleWeapon"),
    _versioned("weapon_attachments", "weapon-attachments", "WeaponAttachment"),
    _versioned("commodities", "commodities", "Commodity", locale=False, filters=True),
    _versioned("missions", "missions", "Mission", locale=False, filters=True),
    _versioned("locations", "locations", "Location", locale=False, filters=True),
    _versioned("blueprints", "blueprints", "Blueprint", locale=False, filters=True),
    _timed("celestial_objects", "celestial-objects", "CelestialObject", DAY, DAY),
    _timed("starsystems", "starsystems", "StarSystem", DAY, DAY, filters=True),
    _timed("comm_links", "comm-links", "CommLink", WEEK, HOUR, filters=True),
    _timed("comm_link_images", "comm-link-images", "CommLinkImage", WEEK, HOUR),
    _timed(
        "galactapedia", "galactapedia", "GalactapediaArticle", WEEK, HOUR, locale=True, filters=True
    ),
    _timed("manufacturers", "manufacturers", "Manufacturer", DAY, DAY),
    _timed("factions", "factions", "Faction", DAY, DAY),
    _timed("game_versions", "game-versions", "GameVersion", HOUR, HOUR),
    _timed(
        "shipmatrix_vehicles", "shipmatrix/vehicles", "ShipMatrixVehicle", DAY, DAY, filters=True
    ),
    _timed("stats", "stats", "Stats", HOUR, HOUR),
)

FAMILIES: dict[str, Family] = {f.name: f for f in _ALL}

SEARCH = Family(
    "search", "search", False, detail_ttl=timedelta(minutes=5), list_ttl=timedelta(minutes=5)
)
