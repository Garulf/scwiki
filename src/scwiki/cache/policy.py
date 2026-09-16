"""Decide how long a payload stays fresh.

Versioned game data never expires: a given game build is immutable, and a
new build produces new keys. Everything else expires on a per-family TTL.
"""

from __future__ import annotations

from scwiki.core.families import Family


def expires_for(family: Family, *, is_list: bool, now: float) -> float | None:
    ttl = family.list_ttl if is_list else family.detail_ttl
    if ttl is None:
        return None
    return now + ttl.total_seconds()
