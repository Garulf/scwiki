"""Async and sync clients. Both drive the same transport-free plans."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping, Sequence
from typing import Any, Generic, TypeVar

from scwiki._http import AsyncTransport, SyncTransport
from scwiki.cache.lru import LruFront
from scwiki.cache.sqlite import SqliteStore
from scwiki.cache.store import CacheStore
from scwiki.client_base import (
    BASE_URL,
    ClientConfig,
    Plan,
    apply_version,
    needs_version,
    version_plan,
    with_defaults,
)
from scwiki.core.families import FAMILIES, SEARCH, Family
from scwiki.core.paging import MAX_PAGE_SIZE, page_info
from scwiki.core.parse import Parsed
from scwiki.core.ratelimit import TokenBucket
from scwiki.core.requests import Query, detail_path, list_path
from scwiki.core.retry import should_retry
from scwiki.errors import ScwikiError
from scwiki.models import (
    MODELS,
    Armor,
    Blueprint,
    CelestialObject,
    Clothing,
    CommLink,
    CommLinkImage,
    Commodity,
    Faction,
    Food,
    GalactapediaArticle,
    GameVersion,
    Item,
    Location,
    Manufacturer,
    Mission,
    Model,
    Position,
    ResultMeta,
    SearchGroup,
    ShipMatrixVehicle,
    StarSystem,
    Stats,
    Vehicle,
    VehicleItem,
    VehicleWeapon,
    Weapon,
    WeaponAttachment,
)
from scwiki.models.search import SearchHit

M = TypeVar("M", bound=Model)
Result = tuple[Parsed, ResultMeta]

SEARCH_RATE = 60
SEARCH_PER = 60.0


class _Default:
    pass


DEFAULT_CACHE = _Default()


def _default_cache() -> CacheStore:
    return LruFront(SqliteStore())


def _wrap(model: type[M], parsed: Parsed, meta: ResultMeta) -> M:
    return model.from_payload(parsed.data or {}, meta)


def _wrap_rows(model: type[M], parsed: Parsed, meta: ResultMeta) -> list[M]:
    rows = parsed.data if isinstance(parsed.data, Sequence) else []
    return [model.from_payload(row, meta) for row in rows]


class _ClientCore:
    """Everything both clients share except the four lines that touch the transport."""

    def __init__(
        self,
        *,
        cache: CacheStore | _Default | None,
        base_url: str,
        locale: str | None,
        version: str | None,
        default_version_ttl: float,
        timeout: float,
        clock: Callable[[], float],
    ) -> None:
        self.config = ClientConfig(
            base_url=base_url,
            locale=locale,
            version=version,
            default_version_ttl=default_version_ttl,
            timeout=timeout,
        )
        self.cache: CacheStore | None = _default_cache() if isinstance(cache, _Default) else cache
        self._search_cache: CacheStore = LruFront(None, maxsize=128)
        self._clock = clock
        self._bucket = TokenBucket(SEARCH_RATE, SEARCH_PER)

    def plan(
        self,
        family: Family,
        path: str,
        identifier: str | None,
        query: Query,
        *,
        is_list: bool,
        fresh: bool = False,
        ttl: float | None = None,
        cache: CacheStore | _Default | None = DEFAULT_CACHE,
    ) -> Plan:
        store = self.cache if isinstance(cache, _Default) else cache
        return Plan(
            self.config,
            store,
            family,
            path,
            identifier,
            query,
            is_list=is_list,
            fresh=fresh,
            clock=self._clock,
            ttl=ttl,
        )

    def version_plan(self, *, fresh: bool = False) -> Plan:
        return version_plan(self.config, self.cache, self._clock, fresh=fresh)

    def purge_cache(self, *, version: str | None = None, family: str | None = None) -> int:
        """Drop cached entries, optionally only for one game build or one family."""
        if self.cache is None:
            return 0
        prefix = None if family is None else f"{family}:"
        return self.cache.purge(version=version, prefix=prefix)


class _Pages(Generic[M]):
    total: int | None = None

    def __init__(self, model: type[M], limit: int | None) -> None:
        self.model = model
        self.limit = limit
        self.yielded = 0

    def take(self, parsed: Parsed, meta: ResultMeta) -> tuple[list[M], bool]:
        info = page_info(parsed)
        if info is not None:
            self.total = info.total
        rows = _wrap_rows(self.model, parsed, meta)
        if self.limit is not None:
            rows = rows[: self.limit - self.yielded]
        self.yielded += len(rows)
        done = self.limit is not None and self.yielded >= self.limit
        more = info is not None and info.has_next and not done
        return rows, more


class AsyncPages(_Pages[M]):
    def __init__(
        self, fetch: Callable[[int], Awaitable[Result]], model: type[M], limit: int | None
    ):
        super().__init__(model, limit)
        self._fetch = fetch

    async def __aiter__(self) -> AsyncIterator[M]:
        page = 1
        while True:
            rows, more = self.take(*await self._fetch(page))
            for row in rows:
                yield row
            if not more:
                return
            page += 1


class SyncPages(_Pages[M]):
    def __init__(self, fetch: Callable[[int], Result], model: type[M], limit: int | None):
        super().__init__(model, limit)
        self._fetch = fetch

    def __iter__(self) -> Iterator[M]:
        page = 1
        while True:
            rows, more = self.take(*self._fetch(page))
            yield from rows
            if not more:
                return
            page += 1


def _query(
    *,
    include: Sequence[str] = (),
    locale: str | None = None,
    version: str | None = None,
    filter: Mapping[str, Any] | None = None,
    sort: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Query:
    return Query(
        version=version,
        include=tuple(include),
        locale=locale,
        filter={k: str(v) for k, v in (filter or {}).items()},
        sort=sort,
        page=page,
        page_size=page_size,
    )


# --------------------------------------------------------------------------- async


class AsyncClient(_ClientCore):
    def __init__(
        self,
        transport: AsyncTransport | None = None,
        *,
        cache: CacheStore | _Default | None = DEFAULT_CACHE,
        base_url: str = BASE_URL,
        locale: str | None = None,
        version: str | None = None,
        default_version_ttl: float = 3600.0,
        timeout: float = 20.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        super().__init__(
            cache=cache,
            base_url=base_url,
            locale=locale,
            version=version,
            default_version_ttl=default_version_ttl,
            timeout=timeout,
            clock=clock,
        )
        self._transport = transport
        self._sleep = sleep
        self.vehicles: AsyncResource[Vehicle] = AsyncResource(self, FAMILIES["vehicles"])
        self.ground_vehicles: AsyncResource[Vehicle] = AsyncResource(
            self, FAMILIES["ground_vehicles"]
        )
        self.gravlev_vehicles: AsyncResource[Vehicle] = AsyncResource(
            self, FAMILIES["gravlev_vehicles"]
        )
        self.items: AsyncResource[Item] = AsyncResource(self, FAMILIES["items"])
        self.weapons: AsyncResource[Weapon] = AsyncResource(self, FAMILIES["weapons"])
        self.armor: AsyncResource[Armor] = AsyncResource(self, FAMILIES["armor"])
        self.clothes: AsyncResource[Clothing] = AsyncResource(self, FAMILIES["clothes"])
        self.food: AsyncResource[Food] = AsyncResource(self, FAMILIES["food"])
        self.vehicle_items: AsyncResource[VehicleItem] = AsyncResource(
            self, FAMILIES["vehicle_items"]
        )
        self.vehicle_weapons: AsyncResource[VehicleWeapon] = AsyncResource(
            self, FAMILIES["vehicle_weapons"]
        )
        self.weapon_attachments: AsyncResource[WeaponAttachment] = AsyncResource(
            self, FAMILIES["weapon_attachments"]
        )
        self.commodities: AsyncResource[Commodity] = AsyncResource(self, FAMILIES["commodities"])
        self.missions: AsyncResource[Mission] = AsyncResource(self, FAMILIES["missions"])
        self.locations = AsyncLocations(self, FAMILIES["locations"])
        self.blueprints: AsyncResource[Blueprint] = AsyncResource(self, FAMILIES["blueprints"])
        self.celestial_objects: AsyncResource[CelestialObject] = AsyncResource(
            self, FAMILIES["celestial_objects"]
        )
        self.starsystems: AsyncResource[StarSystem] = AsyncResource(self, FAMILIES["starsystems"])
        self.comm_links: AsyncResource[CommLink] = AsyncResource(self, FAMILIES["comm_links"])
        self.comm_link_images = AsyncCommLinkImages(self, FAMILIES["comm_link_images"])
        self.galactapedia: AsyncResource[GalactapediaArticle] = AsyncResource(
            self, FAMILIES["galactapedia"]
        )
        self.manufacturers: AsyncResource[Manufacturer] = AsyncResource(
            self, FAMILIES["manufacturers"]
        )
        self.factions: AsyncResource[Faction] = AsyncResource(self, FAMILIES["factions"])
        self.game_versions = AsyncGameVersions(self, FAMILIES["game_versions"])
        self.shipmatrix_vehicles: AsyncResource[ShipMatrixVehicle] = AsyncResource(
            self, FAMILIES["shipmatrix_vehicles"]
        )
        self.stats = AsyncStats(self, FAMILIES["stats"])

    def resource(self, family: str) -> AsyncResource[Any]:
        return getattr(self, family)  # type: ignore[no-any-return]

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._transport is not None:
            await self._transport.aclose()
        if self.cache is not None:
            self.cache.close()

    def _get_transport(self) -> AsyncTransport:
        if self._transport is None:
            from scwiki.transports import resolve_async

            self._transport = resolve_async(self.config.timeout)
        return self._transport

    async def run(self, plan: Plan) -> Result:
        hit = plan.cached()
        if hit is not None:
            return hit
        attempt = 0
        while True:
            try:
                response = await self._get_transport().send(plan.request())
                return plan.accept(response)
            except ScwikiError as exc:
                delay = should_retry(exc, attempt)
                if delay is None:
                    fallback = plan.fallback(exc)
                    if fallback is not None:
                        return fallback
                    raise
                await self._sleep(delay)
                attempt += 1

    async def resolve(self, family: Family, query: Query) -> Query:
        query = with_defaults(family, query, self.config)
        if needs_version(family, query, self.config):
            parsed, _ = await self.run(self.version_plan())
            query = apply_version(query, parsed.data["code"])
        return query

    async def fetch(
        self,
        family: Family,
        path: str,
        identifier: str | None,
        query: Query,
        *,
        is_list: bool,
        fresh: bool = False,
    ) -> Result:
        query = await self.resolve(family, query)
        return await self.run(
            self.plan(family, path, identifier, query, is_list=is_list, fresh=fresh)
        )

    async def search(self, query: str, *, version: str | None = None) -> list[SearchGroup]:
        q = Query(filter={"query": query}, version=version or self.config.version)
        plan = self.plan(SEARCH, "search", None, q, is_list=True, cache=self._search_cache)
        if plan.cached() is None:
            delay = self._bucket.acquire_delay()
            if delay > 0:
                await self._sleep(delay)
        parsed, _ = await self.run(plan)
        return [SearchGroup.build(group, fetch=self._fetch_hit) for group in parsed.data or []]

    def _fetch_hit(self, hit: SearchHit) -> Awaitable[Any]:
        if hit.family is None or hit.identifier is None:
            raise ScwikiError(f"cannot resolve search hit {hit.name!r}")
        return self.resource(hit.family).get(hit.identifier)


class AsyncResource(Generic[M]):
    def __init__(self, client: AsyncClient, family: Family) -> None:
        self.client = client
        self.family = family
        self.model: type[M] = MODELS[family.model]  # type: ignore[assignment]

    async def get(
        self,
        identifier: str,
        *,
        include: Sequence[str] = (),
        locale: str | None = None,
        version: str | None = None,
        fresh: bool = False,
    ) -> M:
        q = _query(include=include, locale=locale, version=version)
        parsed, meta = await self.client.fetch(
            self.family,
            detail_path(self.family, identifier),
            identifier,
            q,
            is_list=False,
            fresh=fresh,
        )
        return _wrap(self.model, parsed, meta)

    def list(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        sort: str | None = None,
        include: Sequence[str] = (),
        version: str | None = None,
        page_size: int = MAX_PAGE_SIZE,
        limit: int | None = None,
        fresh: bool = False,
    ) -> AsyncPages[M]:
        async def fetch(page: int) -> Result:
            q = _query(
                include=include,
                version=version,
                filter=filter,
                sort=sort,
                page=page,
                page_size=page_size,
            )
            return await self.client.fetch(
                self.family, list_path(self.family), None, q, is_list=True, fresh=fresh
            )

        return AsyncPages(fetch, self.model, limit)

    async def filters(
        self, *, version: str | None = None, fresh: bool = False
    ) -> Mapping[str, Any]:
        if not self.family.has_filters:
            raise ScwikiError(f"{self.family.name} has no filters endpoint")
        parsed, _ = await self.client.fetch(
            self.family,
            f"{self.family.path}/filters",
            "filters",
            _query(version=version),
            is_list=False,
            fresh=fresh,
        )
        return parsed.data or {}

    async def _sub(self, path: str, query: Query, *, is_list: bool, fresh: bool = False) -> Result:
        return await self.client.fetch(self.family, path, path, query, is_list=is_list, fresh=fresh)


class AsyncGameVersions(AsyncResource[GameVersion]):
    async def default(self, *, fresh: bool = False) -> GameVersion:
        parsed, meta = await self.client.run(self.client.version_plan(fresh=fresh))
        return _wrap(GameVersion, parsed, meta)

    async def changelog(self, code: str, *, fresh: bool = False) -> Mapping[str, Any]:
        parsed, _ = await self._sub(
            f"{detail_path(self.family, code)}/changelog", Query(), is_list=False, fresh=fresh
        )
        return parsed.data or {}


class AsyncCommLinkImages(AsyncResource[CommLinkImage]):
    async def random(self, *, limit: int = 1, tags: str | None = None) -> list[CommLinkImage]:
        filters = {"tags": tags} if tags else {}
        q = Query(filter={**filters, "limit": str(limit)})
        parsed, meta = await self._sub("comm-link-images/random", q, is_list=True, fresh=True)
        return _wrap_rows(self.model, parsed, meta)


class AsyncLocations(AsyncResource[Location]):
    async def positions(
        self, *, system: str | None = None, type: str | None = None, fresh: bool = False
    ) -> list[Position]:
        filters = {k: v for k, v in (("system", system), ("type", type)) if v}
        parsed, meta = await self._sub(
            "locations/positions", Query(filter=filters), is_list=True, fresh=fresh
        )
        return _wrap_rows(Position, parsed, meta)


class AsyncStats(AsyncResource[Stats]):
    async def latest(self, *, fresh: bool = False) -> Stats:
        parsed, meta = await self._sub("stats/latest", Query(), is_list=False, fresh=fresh)
        return _wrap(Stats, parsed, meta)


# --------------------------------------------------------------------------- sync


class Client(_ClientCore):
    def __init__(
        self,
        transport: SyncTransport | None = None,
        *,
        cache: CacheStore | _Default | None = DEFAULT_CACHE,
        base_url: str = BASE_URL,
        locale: str | None = None,
        version: str | None = None,
        default_version_ttl: float = 3600.0,
        timeout: float = 20.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(
            cache=cache,
            base_url=base_url,
            locale=locale,
            version=version,
            default_version_ttl=default_version_ttl,
            timeout=timeout,
            clock=clock,
        )
        self._transport = transport
        self._sleep = sleep
        self.vehicles: Resource[Vehicle] = Resource(self, FAMILIES["vehicles"])
        self.ground_vehicles: Resource[Vehicle] = Resource(self, FAMILIES["ground_vehicles"])
        self.gravlev_vehicles: Resource[Vehicle] = Resource(self, FAMILIES["gravlev_vehicles"])
        self.items: Resource[Item] = Resource(self, FAMILIES["items"])
        self.weapons: Resource[Weapon] = Resource(self, FAMILIES["weapons"])
        self.armor: Resource[Armor] = Resource(self, FAMILIES["armor"])
        self.clothes: Resource[Clothing] = Resource(self, FAMILIES["clothes"])
        self.food: Resource[Food] = Resource(self, FAMILIES["food"])
        self.vehicle_items: Resource[VehicleItem] = Resource(self, FAMILIES["vehicle_items"])
        self.vehicle_weapons: Resource[VehicleWeapon] = Resource(self, FAMILIES["vehicle_weapons"])
        self.weapon_attachments: Resource[WeaponAttachment] = Resource(
            self, FAMILIES["weapon_attachments"]
        )
        self.commodities: Resource[Commodity] = Resource(self, FAMILIES["commodities"])
        self.missions: Resource[Mission] = Resource(self, FAMILIES["missions"])
        self.locations = Locations(self, FAMILIES["locations"])
        self.blueprints: Resource[Blueprint] = Resource(self, FAMILIES["blueprints"])
        self.celestial_objects: Resource[CelestialObject] = Resource(
            self, FAMILIES["celestial_objects"]
        )
        self.starsystems: Resource[StarSystem] = Resource(self, FAMILIES["starsystems"])
        self.comm_links: Resource[CommLink] = Resource(self, FAMILIES["comm_links"])
        self.comm_link_images = CommLinkImages(self, FAMILIES["comm_link_images"])
        self.galactapedia: Resource[GalactapediaArticle] = Resource(self, FAMILIES["galactapedia"])
        self.manufacturers: Resource[Manufacturer] = Resource(self, FAMILIES["manufacturers"])
        self.factions: Resource[Faction] = Resource(self, FAMILIES["factions"])
        self.game_versions = GameVersions(self, FAMILIES["game_versions"])
        self.shipmatrix_vehicles: Resource[ShipMatrixVehicle] = Resource(
            self, FAMILIES["shipmatrix_vehicles"]
        )
        self.stats = StatsResource(self, FAMILIES["stats"])

    def resource(self, family: str) -> Resource[Any]:
        return getattr(self, family)  # type: ignore[no-any-return]

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
        if self.cache is not None:
            self.cache.close()

    def _get_transport(self) -> SyncTransport:
        if self._transport is None:
            from scwiki.transports import resolve_sync

            self._transport = resolve_sync(self.config.timeout)
        return self._transport

    def run(self, plan: Plan) -> Result:
        hit = plan.cached()
        if hit is not None:
            return hit
        attempt = 0
        while True:
            try:
                response = self._get_transport().send(plan.request())
                return plan.accept(response)
            except ScwikiError as exc:
                delay = should_retry(exc, attempt)
                if delay is None:
                    fallback = plan.fallback(exc)
                    if fallback is not None:
                        return fallback
                    raise
                self._sleep(delay)
                attempt += 1

    def resolve(self, family: Family, query: Query) -> Query:
        query = with_defaults(family, query, self.config)
        if needs_version(family, query, self.config):
            parsed, _ = self.run(self.version_plan())
            query = apply_version(query, parsed.data["code"])
        return query

    def fetch(
        self,
        family: Family,
        path: str,
        identifier: str | None,
        query: Query,
        *,
        is_list: bool,
        fresh: bool = False,
    ) -> Result:
        query = self.resolve(family, query)
        return self.run(self.plan(family, path, identifier, query, is_list=is_list, fresh=fresh))

    def search(self, query: str, *, version: str | None = None) -> list[SearchGroup]:
        q = Query(filter={"query": query}, version=version or self.config.version)
        plan = self.plan(SEARCH, "search", None, q, is_list=True, cache=self._search_cache)
        if plan.cached() is None:
            delay = self._bucket.acquire_delay()
            if delay > 0:
                self._sleep(delay)
        parsed, _ = self.run(plan)
        return [SearchGroup.build(group, fetch=self._fetch_hit) for group in parsed.data or []]

    def _fetch_hit(self, hit: SearchHit) -> Any:
        if hit.family is None or hit.identifier is None:
            raise ScwikiError(f"cannot resolve search hit {hit.name!r}")
        return self.resource(hit.family).get(hit.identifier)


class Resource(Generic[M]):
    def __init__(self, client: Client, family: Family) -> None:
        self.client = client
        self.family = family
        self.model: type[M] = MODELS[family.model]  # type: ignore[assignment]

    def get(
        self,
        identifier: str,
        *,
        include: Sequence[str] = (),
        locale: str | None = None,
        version: str | None = None,
        fresh: bool = False,
    ) -> M:
        q = _query(include=include, locale=locale, version=version)
        parsed, meta = self.client.fetch(
            self.family,
            detail_path(self.family, identifier),
            identifier,
            q,
            is_list=False,
            fresh=fresh,
        )
        return _wrap(self.model, parsed, meta)

    def list(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        sort: str | None = None,
        include: Sequence[str] = (),
        version: str | None = None,
        page_size: int = MAX_PAGE_SIZE,
        limit: int | None = None,
        fresh: bool = False,
    ) -> SyncPages[M]:
        def fetch(page: int) -> Result:
            q = _query(
                include=include,
                version=version,
                filter=filter,
                sort=sort,
                page=page,
                page_size=page_size,
            )
            return self.client.fetch(
                self.family, list_path(self.family), None, q, is_list=True, fresh=fresh
            )

        return SyncPages(fetch, self.model, limit)

    def filters(self, *, version: str | None = None, fresh: bool = False) -> Mapping[str, Any]:
        if not self.family.has_filters:
            raise ScwikiError(f"{self.family.name} has no filters endpoint")
        parsed, _ = self.client.fetch(
            self.family,
            f"{self.family.path}/filters",
            "filters",
            _query(version=version),
            is_list=False,
            fresh=fresh,
        )
        return parsed.data or {}

    def _sub(self, path: str, query: Query, *, is_list: bool, fresh: bool = False) -> Result:
        return self.client.fetch(self.family, path, path, query, is_list=is_list, fresh=fresh)


class GameVersions(Resource[GameVersion]):
    def default(self, *, fresh: bool = False) -> GameVersion:
        parsed, meta = self.client.run(self.client.version_plan(fresh=fresh))
        return _wrap(GameVersion, parsed, meta)

    def changelog(self, code: str, *, fresh: bool = False) -> Mapping[str, Any]:
        parsed, _ = self._sub(
            f"{detail_path(self.family, code)}/changelog", Query(), is_list=False, fresh=fresh
        )
        return parsed.data or {}


class CommLinkImages(Resource[CommLinkImage]):
    def random(self, *, limit: int = 1, tags: str | None = None) -> list[CommLinkImage]:
        filters = {"tags": tags} if tags else {}
        q = Query(filter={**filters, "limit": str(limit)})
        parsed, meta = self._sub("comm-link-images/random", q, is_list=True, fresh=True)
        return _wrap_rows(self.model, parsed, meta)


class Locations(Resource[Location]):
    def positions(
        self, *, system: str | None = None, type: str | None = None, fresh: bool = False
    ) -> list[Position]:
        filters = {k: v for k, v in (("system", system), ("type", type)) if v}
        parsed, meta = self._sub(
            "locations/positions", Query(filter=filters), is_list=True, fresh=fresh
        )
        return _wrap_rows(Position, parsed, meta)


class StatsResource(Resource[Stats]):
    def latest(self, *, fresh: bool = False) -> Stats:
        parsed, meta = self._sub("stats/latest", Query(), is_list=False, fresh=fresh)
        return _wrap(Stats, parsed, meta)
