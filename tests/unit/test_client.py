from __future__ import annotations

import json
from typing import Any

import pytest

from scwiki import AsyncClient, Client, MemoryStore, NotFound, ServerError
from scwiki._http import Response
from scwiki.models import GameVersion, Stats, Vehicle
from tests.conftest import (
    AsyncFakeTransport,
    FakeClock,
    FakeTransport,
    fixture_bytes,
    json_response,
)

BUILD = "4.10.0-LIVE.12519617"


def version_response() -> Response:
    return Response(200, {}, fixture_bytes("game-versions.default"))


def vehicle_response() -> Response:
    return Response(200, {}, fixture_bytes("vehicles.detail"))


def list_pages() -> list[Response]:
    base = json.loads(fixture_bytes("vehicles.list"))
    p1 = dict(base, meta=dict(base["meta"], current_page=1, last_page=2, total=4))
    p2 = dict(base, meta=dict(base["meta"], current_page=2, last_page=2, total=4))
    return [json_response(p1), json_response(p2)]


class Sleeper:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.calls.append(delay)

    def sync(self, delay: float) -> None:
        self.calls.append(delay)


def make_async(
    clock: FakeClock, responses: list[Response], **kw: Any
) -> tuple[AsyncClient, AsyncFakeTransport, Sleeper]:
    transport = AsyncFakeTransport(responses)
    sleeper = Sleeper()
    client = AsyncClient(transport, cache=MemoryStore(), clock=clock, sleep=sleeper, **kw)
    return client, transport, sleeper


def make_sync(
    clock: FakeClock, responses: list[Response], **kw: Any
) -> tuple[Client, FakeTransport, Sleeper]:
    transport = FakeTransport(responses)
    sleeper = Sleeper()
    client = Client(transport, cache=MemoryStore(), clock=clock, sleep=sleeper.sync, **kw)
    return client, transport, sleeper


async def test_get_resolves_version_then_caches(clock: FakeClock) -> None:
    client, transport, _ = make_async(clock, [version_response(), vehicle_response()])
    ship = await client.vehicles.get("aegs-avenger-stalker", include=["ports"])
    assert isinstance(ship, Vehicle)
    assert ship.slug == "aegs-avenger-stalker"
    assert ship.meta.cached is False and ship.meta.version == BUILD
    assert [r.url.split("/api/")[1] for r in transport.requests] == [
        "game-versions/default",
        f"vehicles/aegs-avenger-stalker?include=ports&version={BUILD}",
    ]
    again = await client.vehicles.get("aegs-avenger-stalker", include=["ports"])
    assert again.meta.cached is True
    assert len(transport.requests) == 2


async def test_pinned_version_skips_probe(clock: FakeClock) -> None:
    client, transport, _ = make_async(clock, [vehicle_response()], version="4.9.0")
    await client.vehicles.get("x")
    assert transport.requests[0].url.endswith("vehicles/x?version=4.9.0")


async def test_fresh_bypasses_cache(clock: FakeClock) -> None:
    client, transport, _ = make_async(
        clock, [version_response(), vehicle_response(), vehicle_response()]
    )
    await client.vehicles.get("x")
    await client.vehicles.get("x", fresh=True)
    assert len(transport.requests) == 3


async def test_locale_default_applies_to_supporting_families(clock: FakeClock) -> None:
    client, transport, _ = make_async(
        clock, [version_response(), json_response({"data": {}}), vehicle_response()], locale="de_DE"
    )
    await client.items.get("x")
    assert "locale=de_DE" in transport.requests[1].url
    await client.vehicles.get("y")
    assert "locale" not in transport.requests[2].url


async def test_list_pagination_and_limit(clock: FakeClock) -> None:
    client, transport, _ = make_async(clock, [version_response(), *list_pages()])
    pages = client.vehicles.list(filter={"manufacturer": "AEGS"}, limit=3)
    rows = [v async for v in pages]
    assert len(rows) == 3
    assert pages.total == 4
    assert len(transport.requests) == 3
    assert "filter%5Bmanufacturer%5D=AEGS" in transport.requests[1].url
    assert "page%5Bnumber%5D=2" in transport.requests[2].url


async def test_list_stops_at_last_page(clock: FakeClock) -> None:
    client, transport, _ = make_async(clock, [version_response(), *list_pages()])
    rows = [v async for v in client.vehicles.list()]
    assert len(rows) == 4
    assert len(transport.requests) == 3


async def test_search_is_rate_limited_and_hits_fetch(clock: FakeClock) -> None:
    client, transport, sleeper = make_async(
        clock, [Response(200, {}, fixture_bytes("search")), version_response(), vehicle_response()]
    )
    client._bucket._tokens = 0.0
    groups = await client.search("avenger")
    assert sleeper.calls and sleeper.calls[0] > 0
    assert transport.requests[0].url.endswith("search?filter%5Bquery%5D=avenger")
    hit = groups[0].results[0]
    ship = await hit.fetch()
    assert isinstance(ship, Vehicle)
    cached = await client.search("avenger")
    assert len(transport.requests) == 3
    assert cached[0].type == "vehicles"
    assert client.cache is not None and client.cache.purge(prefix="search") == 0


async def test_retries_then_stale_fallback(clock: FakeClock) -> None:
    client, transport, sleeper = make_async(clock, [json_response({"data": {"id": 1}})])
    first = await client.comm_links.get("1")
    assert first.id == 1
    clock.advance(10**7)
    for _ in range(3):
        transport.push(Response(500, {}, b""))
    stale = await client.comm_links.get("1")
    assert stale.meta.stale is True
    assert sleeper.calls == [0.5, 1.5]


async def test_error_without_fallback_raises(clock: FakeClock) -> None:
    client, _, _ = make_async(clock, [version_response(), Response(404, {}, b"<html>")])
    with pytest.raises(NotFound):
        await client.vehicles.get("nope")


async def test_server_error_without_cache_raises_after_retries(clock: FakeClock) -> None:
    client, _, sleeper = make_async(clock, [Response(500, {}, b"")] * 3)
    with pytest.raises(ServerError):
        await client.game_versions.default()
    assert sleeper.calls == [0.5, 1.5]


async def test_sub_endpoints(clock: FakeClock) -> None:
    client, transport, _ = make_async(
        clock,
        [
            version_response(),
            Response(200, {}, fixture_bytes("stats.latest")),
            Response(200, {}, fixture_bytes("locations.positions")),
            Response(200, {}, fixture_bytes("vehicles.filters")),
        ],
    )
    build = await client.game_versions.default()
    assert isinstance(build, GameVersion) and build.code == BUILD
    stats = await client.stats.latest()
    assert isinstance(stats, Stats) and stats.fans
    positions = await client.locations.positions(system="stanton")
    assert positions and positions[0].uuid
    assert "filter%5Bsystem%5D=stanton" in transport.requests[2].url
    filters = await client.vehicles.filters()
    assert "filters" in filters
    with pytest.raises(Exception, match="no filters endpoint"):
        await client.manufacturers.filters()


async def test_purge_cache_by_family_and_version(clock: FakeClock) -> None:
    client, transport, _ = make_async(
        clock, [version_response(), vehicle_response(), vehicle_response()]
    )
    await client.vehicles.get("x")
    assert client.purge_cache(family="vehicles") == 1
    await client.vehicles.get("x")
    assert len(transport.requests) == 3
    assert client.purge_cache(version=BUILD) == 1


async def test_context_manager_closes_transport(clock: FakeClock) -> None:
    client, transport, _ = make_async(clock, [])
    async with client:
        pass
    assert transport.closed


def test_sync_client_mirrors_async(clock: FakeClock) -> None:
    client, transport, sleeper = make_sync(
        clock,
        [
            version_response(),
            vehicle_response(),
            *list_pages(),
            Response(200, {}, fixture_bytes("search")),
        ],
    )
    with client:
        ship = client.vehicles.get("aegs-avenger-stalker")
        assert ship.slug == "aegs-avenger-stalker"
        assert client.vehicles.get("aegs-avenger-stalker").meta.cached is True
        pages = client.vehicles.list(limit=3)
        assert len(list(pages)) == 3 and pages.total == 4
        client._bucket._tokens = 0.0
        groups = client.search("avenger")
        assert sleeper.calls and groups[0].results[0].name
        transport.push(vehicle_response())
        assert isinstance(groups[0].results[0].fetch(), Vehicle)
    assert transport.closed


def test_sync_retry_and_fallback(clock: FakeClock) -> None:
    client, transport, sleeper = make_sync(clock, [json_response({"data": {"code": "v"}})])
    assert client.game_versions.default().code == "v"
    clock.advance(10**6)
    for _ in range(3):
        transport.push(Response(503, {}, b""))
    assert client.game_versions.default().meta.stale is True
    assert sleeper.calls == [0.5, 1.5]


def test_cache_none_disables_storage(clock: FakeClock) -> None:
    transport = FakeTransport(
        [version_response(), vehicle_response(), version_response(), vehicle_response()]
    )
    client = Client(transport, cache=None, clock=clock)
    client.vehicles.get("x")
    client.vehicles.get("x")
    assert len(transport.requests) == 4
    assert client.purge_cache() == 0
