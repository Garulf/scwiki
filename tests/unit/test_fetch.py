import pytest

from scwiki._http import Response
from scwiki.cache.store import MemoryStore
from scwiki.client_base import (
    ClientConfig,
    Plan,
    apply_version,
    needs_version,
    version_plan,
    with_defaults,
)
from scwiki.core.families import FAMILIES, SEARCH
from scwiki.core.requests import Query, detail_path
from scwiki.errors import ServerError
from tests.conftest import FakeClock, fixture_bytes, json_response

CFG = ClientConfig()
VEH = FAMILIES["vehicles"]
CL = FAMILIES["comm_links"]


def vehicle_plan(store: MemoryStore | None, clock: FakeClock, **kw: object) -> Plan:
    q = Query(version="4.10.0-LIVE.12519617")
    return Plan(
        CFG,
        store,
        VEH,
        detail_path(VEH, "aegs-avenger-stalker"),
        "aegs-avenger-stalker",
        q,
        is_list=False,
        clock=clock,
        **kw,  # type: ignore[arg-type]
    )


def test_miss_then_hit(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = vehicle_plan(store, clock)
    assert plan.cached() is None
    parsed, meta = plan.accept(Response(200, {}, fixture_bytes("vehicles.detail")))
    assert parsed.data["slug"] == "aegs-avenger-stalker"
    assert meta.cached is False and meta.version == "4.10.0-LIVE.12519617"
    hit = vehicle_plan(store, clock).cached()
    assert hit is not None
    assert hit[1].cached is True and hit[1].stale is False
    assert hit[0].data["slug"] == "aegs-avenger-stalker"


def test_versioned_entry_never_expires(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = vehicle_plan(store, clock)
    plan.accept(Response(200, {}, fixture_bytes("vehicles.detail")))
    entry = store.get(plan.key)
    assert entry is not None
    assert entry.expires_at is None
    assert entry.version == "4.10.0-LIVE.12519617"
    clock.advance(10**9)
    assert vehicle_plan(store, clock).cached() is not None


def test_fresh_skips_read_but_writes(clock: FakeClock) -> None:
    store = MemoryStore()
    vehicle_plan(store, clock).accept(Response(200, {}, fixture_bytes("vehicles.detail")))
    plan = vehicle_plan(store, clock, fresh=True)
    assert plan.cached() is None
    plan.accept(Response(200, {}, b'{"data": {"slug": "new"}}'))
    hit = vehicle_plan(store, clock).cached()
    assert hit is not None and hit[0].data["slug"] == "new"


def test_unversioned_entry_expires_per_policy(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = Plan(CFG, store, CL, "comm-links/1", "1", Query(), is_list=False, clock=clock)
    plan.accept(json_response({"data": {"id": 1}}))
    entry = store.get(plan.key)
    assert entry is not None and entry.expires_at == clock.now + 7 * 24 * 3600
    assert entry.version is None
    clock.advance(7 * 24 * 3600 + 1)
    assert (
        Plan(CFG, store, CL, "comm-links/1", "1", Query(), is_list=False, clock=clock).cached()
        is None
    )


def test_ttl_override(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = version_plan(ClientConfig(default_version_ttl=60.0), store, clock)
    plan.accept(json_response({"data": {"code": "x"}}))
    entry = store.get(plan.key)
    assert entry is not None and entry.expires_at == clock.now + 60.0


def test_fallback_returns_stale_entry(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = Plan(CFG, store, CL, "comm-links/1", "1", Query(), is_list=False, clock=clock)
    plan.accept(json_response({"data": {"id": 1}}))
    clock.advance(10**7)
    later = Plan(CFG, store, CL, "comm-links/1", "1", Query(), is_list=False, clock=clock)
    assert later.cached() is None
    fb = later.fallback(ServerError(500))
    assert fb is not None
    assert fb[1].stale is True and fb[1].cached is True
    assert fb[0].data == {"id": 1}


def test_fallback_without_entry_or_cache(clock: FakeClock) -> None:
    assert vehicle_plan(MemoryStore(), clock).fallback(ServerError(500)) is None
    assert vehicle_plan(None, clock).fallback(ServerError(500)) is None


def test_no_cache_never_stores(clock: FakeClock) -> None:
    plan = vehicle_plan(None, clock)
    parsed, _ = plan.accept(Response(200, {}, fixture_bytes("vehicles.detail")))
    assert parsed.data["slug"] == "aegs-avenger-stalker"
    assert vehicle_plan(None, clock).cached() is None


def test_accept_raises_on_error_and_leaves_cache_alone(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = vehicle_plan(store, clock)
    with pytest.raises(ServerError):
        plan.accept(Response(500, {}, b""))
    assert store.get(plan.key) is None


def test_search_plan_uses_short_ttl(clock: FakeClock) -> None:
    store = MemoryStore()
    plan = Plan(
        CFG, store, SEARCH, "search", None, Query(filter={"query": "x"}), is_list=True, clock=clock
    )
    plan.accept(json_response({"data": []}))
    entry = store.get(plan.key)
    assert entry is not None and entry.expires_at == clock.now + 300


def test_version_helpers() -> None:
    assert needs_version(VEH, Query(), CFG)
    assert not needs_version(VEH, Query(version="v"), CFG)
    assert not needs_version(VEH, Query(), ClientConfig(version="pinned"))
    assert not needs_version(CL, Query(), CFG)
    q = with_defaults(VEH, Query(), ClientConfig(version="pinned", locale="de_DE"))
    assert q.version == "pinned" and q.locale is None
    q = with_defaults(FAMILIES["items"], Query(), ClientConfig(locale="de_DE"))
    assert q.locale == "de_DE"
    assert apply_version(Query(), "4.10").version == "4.10"


def test_request_uses_config(clock: FakeClock) -> None:
    plan = vehicle_plan(None, clock)
    req = plan.request()
    assert req.url.startswith("https://api.star-citizen.wiki/api/vehicles/aegs-avenger-stalker?")
    assert req.headers["User-Agent"].startswith("scwiki/")
