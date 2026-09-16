from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote, urlparse

from scwiki.core.families import FAMILIES
from scwiki.models.base import Model, Value

_TYPE_TO_FAMILY = {fam.path.replace("/", "-"): name for name, fam in FAMILIES.items()}


@dataclass(frozen=True)
class SearchHit(Value):
    type: str | None = None
    name: str | None = None
    class_name: str | None = None
    classification: str | None = None
    api_url: str | None = None
    web_url: str | None = None
    _fetch: Any = field(default=None, repr=False, compare=False)

    @property
    def identifier(self) -> str | None:
        if not self.api_url:
            return None
        return unquote(urlparse(self.api_url).path.rstrip("/").rsplit("/", 1)[-1])

    @property
    def family(self) -> str | None:
        candidates = []
        if self.type:
            candidates.append(self.type.replace("_", "-"))
        if self.api_url:
            segments = urlparse(self.api_url).path.rstrip("/").split("/")
            if len(segments) >= 2:
                candidates.append(segments[-2])
        for candidate in candidates:
            if candidate in _TYPE_TO_FAMILY:
                return _TYPE_TO_FAMILY[candidate]
        return None

    def fetch(self) -> Any:
        """Resolve the full record through the client this hit came from."""
        if self._fetch is None:
            raise RuntimeError("this SearchHit is not bound to a client")
        return self._fetch(self)


@dataclass(frozen=True)
class SearchGroup(Model):
    type: str | None = None
    label: str | None = None
    results: tuple[SearchHit, ...] = ()

    @classmethod
    def build(cls, data: Any, fetch: Any = None) -> SearchGroup:
        group_type = data.get("type")
        hits = tuple(
            SearchHit(
                raw=r,
                _fetch=fetch,
                type=r.get("type") or group_type,
                **{k: r.get(k) for k in _HIT_KEYS},
            )
            for r in data.get("results") or ()
        )
        return cls(raw=data, type=data.get("type"), label=data.get("label"), results=hits)


_HIT_KEYS = ("name", "class_name", "classification", "api_url", "web_url")
