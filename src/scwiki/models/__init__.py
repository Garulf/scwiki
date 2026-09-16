from scwiki.models.base import Model, ResultMeta, Value, localized
from scwiki.models.blueprint import Blueprint
from scwiki.models.comm_link import CommLink, CommLinkImage
from scwiki.models.commodity import Commodity
from scwiki.models.common import (
    Crew,
    Dimension,
    Image,
    ManufacturerRef,
    Named,
    Shield,
    Signature,
    Speed,
)
from scwiki.models.faction import Faction
from scwiki.models.galactapedia import GalactapediaArticle
from scwiki.models.game_version import GameVersion
from scwiki.models.item import (
    Armor,
    Clothing,
    Food,
    Item,
    VehicleItem,
    VehicleWeapon,
    Weapon,
    WeaponAttachment,
)
from scwiki.models.location import Location, LocationRef, LocationType, Position
from scwiki.models.manufacturer import Manufacturer
from scwiki.models.mission import FactionRef, Mission
from scwiki.models.search import SearchGroup, SearchHit
from scwiki.models.shipmatrix import ShipMatrixVehicle
from scwiki.models.starmap import CelestialObject, StarSystem
from scwiki.models.stats import Stats
from scwiki.models.vehicle import Vehicle

MODELS: dict[str, type[Model]] = {
    "Vehicle": Vehicle,
    "ShipMatrixVehicle": ShipMatrixVehicle,
    "Item": Item,
    "Weapon": Weapon,
    "Armor": Armor,
    "Clothing": Clothing,
    "Food": Food,
    "VehicleItem": VehicleItem,
    "VehicleWeapon": VehicleWeapon,
    "WeaponAttachment": WeaponAttachment,
    "Commodity": Commodity,
    "Mission": Mission,
    "Location": Location,
    "Blueprint": Blueprint,
    "StarSystem": StarSystem,
    "CelestialObject": CelestialObject,
    "CommLink": CommLink,
    "CommLinkImage": CommLinkImage,
    "GalactapediaArticle": GalactapediaArticle,
    "Manufacturer": Manufacturer,
    "Faction": Faction,
    "GameVersion": GameVersion,
    "Stats": Stats,
}

__all__ = [
    "MODELS",
    "Armor",
    "Blueprint",
    "CelestialObject",
    "Clothing",
    "CommLink",
    "CommLinkImage",
    "Commodity",
    "Crew",
    "Dimension",
    "Faction",
    "FactionRef",
    "Food",
    "GalactapediaArticle",
    "GameVersion",
    "Image",
    "Item",
    "Location",
    "LocationRef",
    "LocationType",
    "Manufacturer",
    "ManufacturerRef",
    "Mission",
    "Model",
    "Named",
    "Position",
    "ResultMeta",
    "SearchGroup",
    "SearchHit",
    "Shield",
    "ShipMatrixVehicle",
    "Signature",
    "Speed",
    "StarSystem",
    "Stats",
    "Value",
    "Vehicle",
    "VehicleItem",
    "VehicleWeapon",
    "Weapon",
    "WeaponAttachment",
    "localized",
]
