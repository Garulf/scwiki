"""Deterministic cache keys that are stable across processes."""

from __future__ import annotations

from scwiki.core.requests import Query


def make_key(family: str, identifier: str | None, query: Query) -> str:
    include = ",".join(sorted(query.include))
    filters = "&".join(f"{k}={v}" for k, v in sorted(query.filter.items()))
    page = "" if query.page is None else f"{query.page}/{query.page_size or ''}"
    parts = (
        family,
        identifier if identifier is not None else "*",
        query.version or "-",
        query.locale or "-",
        include,
        filters,
        query.sort or "",
        page,
    )
    return "|".join(parts)
