"""Transport-free fetch plan shared by the async and sync clients.

Driver loop (implemented by each client, four lines apart):

1. If the family is versioned and no version is pinned, resolve the current
   default build through ``version_plan`` and put its code on the query.
2. Unless ``fresh``, return ``plan.cached()`` when it yields a fresh entry.
3. Send ``plan.request()`` with retries per ``should_retry``; on success
   return ``plan.accept(response)``.
4. On final failure return ``plan.fallback(exc)`` if it yields a stale entry,
   otherwise raise.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from scwiki import __version__
from scwiki._http import Request, Response
from scwiki.cache.entry import Entry
from scwiki.cache.keys import make_key
from scwiki.cache.policy import expires_for
from scwiki.cache.store import CacheStore
from scwiki.core.families import FAMILIES, Family
from scwiki.core.parse import Parsed, parse_response
from scwiki.core.requests import Query, build_request
from scwiki.errors import ScwikiError
from scwiki.models.base import ResultMeta

BASE_URL = "https://api.star-citizen.wiki/api"
USER_AGENT = f"scwiki/{__version__} (+https://github.com/Garulf/scwiki)"


@dataclass(frozen=True)
class ClientConfig:
    base_url: str = BASE_URL
    user_agent: str = USER_AGENT
    locale: str | None = None
    version: str | None = None
    default_version_ttl: float = 3600.0
    timeout: float = 20.0


class Plan:
    """One logical fetch: a detail record, a list page, or a sub-endpoint."""

    def __init__(
        self,
        config: ClientConfig,
        cache: CacheStore | None,
        family: Family,
        path: str,
        identifier: str | None,
        query: Query,
        *,
        is_list: bool,
        fresh: bool = False,
        clock: Callable[[], float] = time.time,
        ttl: float | None = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self.family = family
        self.path = path
        self.identifier = identifier
        self.query = query
        self.is_list = is_list
        self.fresh = fresh
        self.clock = clock
        self.ttl = ttl
        self.key = make_key(f"{family.name}:{path}", identifier, query)

    def _meta(self, entry: Entry, *, cached: bool, stale: bool) -> ResultMeta:
        payload = entry.payload
        meta = payload.get("meta") or {}
        return ResultMeta(
            version=entry.version or meta.get("resource", {}).get("version"),
            processed_at=meta.get("processed_at"),
            cached=cached,
            stale=stale,
            fetched_at=entry.stored_at,
        )

    @staticmethod
    def _parsed(entry: Entry) -> Parsed:
        payload = entry.payload
        return Parsed(payload.get("data"), payload.get("meta") or {}, payload.get("links") or {})

    def cached(self) -> tuple[Parsed, ResultMeta] | None:
        if self.cache is None or self.fresh:
            return None
        entry = self.cache.get(self.key)
        if entry is None or not entry.is_fresh(self.clock()):
            return None
        return self._parsed(entry), self._meta(entry, cached=True, stale=False)

    def request(self) -> Request:
        return build_request(
            self.config.base_url, self.path, self.query, user_agent=self.config.user_agent
        )

    def accept(self, response: Response) -> tuple[Parsed, ResultMeta]:
        parsed = parse_response(response, family=self.family.name, identifier=self.identifier)
        now = self.clock()
        expires = (
            now + self.ttl
            if self.ttl is not None
            else expires_for(self.family, is_list=self.is_list, now=now)
        )
        version = self.query.version if self.family.versioned else None
        entry = Entry(
            {"data": parsed.data, "meta": dict(parsed.meta), "links": dict(parsed.links)},
            stored_at=now,
            expires_at=expires,
            version=version,
        )
        if self.cache is not None:
            self.cache.put(self.key, entry)
        return parsed, self._meta(entry, cached=False, stale=False)

    def fallback(self, exc: ScwikiError) -> tuple[Parsed, ResultMeta] | None:
        if self.cache is None:
            return None
        entry = self.cache.get(self.key)
        if entry is None:
            return None
        return self._parsed(entry), self._meta(entry, cached=True, stale=True)


def version_plan(
    config: ClientConfig, cache: CacheStore | None, clock: Callable[[], float] = time.time
) -> Plan:
    return Plan(
        config,
        cache,
        FAMILIES["game_versions"],
        "game-versions/default",
        "default",
        Query(),
        is_list=False,
        clock=clock,
        ttl=config.default_version_ttl,
    )


def needs_version(family: Family, query: Query, config: ClientConfig) -> bool:
    return family.versioned and query.version is None and config.version is None


def with_defaults(family: Family, query: Query, config: ClientConfig) -> Query:
    version = query.version
    if family.versioned and version is None:
        version = config.version
    locale = query.locale
    if family.supports_locale and locale is None:
        locale = config.locale
    return replace(query, version=version, locale=locale)


def apply_version(query: Query, code: Any) -> Query:
    return replace(query, version=str(code))
