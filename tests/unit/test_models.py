from dataclasses import fields
from decimal import Decimal

import pytest

from scwiki.core.families import FAMILIES
from scwiki.models import MODELS, ResultMeta, SearchGroup, Stats, Vehicle, localized
from tests.conftest import load_fixture


def _fixture_name(family_name: str) -> str:
    return FAMILIES[family_name].path.replace("/", "-")


@pytest.mark.parametrize("family_name", sorted(FAMILIES))
def test_every_family_detail_fixture_parses(family_name: str) -> None:
    fam = FAMILIES[family_name]
    fixture = "stats.latest" if family_name == "stats" else f"{_fixture_name(family_name)}.detail"
    data = load_fixture(fixture)["data"]
    model_cls = MODELS[fam.model]
    obj = model_cls.from_payload(data, ResultMeta(version="v"))
    assert obj.raw is data
    assert obj.meta.version == "v"
    typed = [f.name for f in fields(obj) if f.name not in ("raw", "meta")]
    assert any(getattr(obj, name) not in (None, ()) for name in typed)


@pytest.mark.parametrize("family_name", sorted(f for f in FAMILIES if f != "stats"))
def test_every_family_list_fixture_parses(family_name: str) -> None:
    fam = FAMILIES[family_name]
    rows = load_fixture(f"{_fixture_name(family_name)}.list")["data"]
    assert rows
    for row in rows:
        MODELS[fam.model].from_payload(row)


def test_vehicle_typed_fields() -> None:
    v = Vehicle.from_payload(load_fixture("vehicles.detail")["data"])
    assert v.slug == "aegs-avenger-stalker"
    assert v.manufacturer is not None and v.manufacturer.code == "AEGS"
    assert v.dimension is not None and v.dimension.length == 20
    assert v.crew is not None and v.crew.max == 1
    assert v.speed is not None and v.speed.scm == 262
    assert v.production_status == "flight-ready"
    assert v.description and v.description.startswith("Initially designed")
    assert v.images and v.images[0].original_url
    assert v.version == "4.10.0-LIVE.12519617"


def test_unknown_and_missing_keys_are_tolerated() -> None:
    v = Vehicle.from_payload({"slug": "x", "brand_new_field": 1})
    assert v.slug == "x"
    assert v.manufacturer is None
    assert v.images == ()
    assert v.raw["brand_new_field"] == 1


def test_localized_helper() -> None:
    assert localized({"en_EN": "a", "de_DE": "b"}) == "a"
    assert localized({"de_DE": "b"}) == "b"
    assert localized("plain") == "plain"
    assert localized(None) is None
    assert localized(42) is None


def test_stats_funds_is_decimal() -> None:
    s = Stats.from_payload(load_fixture("stats.latest")["data"])
    assert isinstance(s.funds, Decimal)


def test_search_group_and_hit() -> None:
    groups = [SearchGroup.build(g) for g in load_fixture("search")["data"]]
    assert groups[0].type == "vehicles"
    hit = groups[0].results[0]
    assert hit.identifier == hit.api_url.rsplit("/", 1)[-1]
    assert hit.family == "vehicles"
    with pytest.raises(RuntimeError):
        hit.fetch()
    bound = SearchGroup.build(load_fixture("search")["data"][0], fetch=lambda h: h.name)
    assert bound.results[0].fetch() == bound.results[0].name
