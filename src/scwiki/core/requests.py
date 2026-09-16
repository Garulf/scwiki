"""Build transport-neutral requests from typed query parameters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote, urlencode

from scwiki._http import Request
from scwiki.core.families import Family


@dataclass(frozen=True)
class Query:
    version: str | None = None
    include: tuple[str, ...] = ()
    locale: str | None = None
    filter: Mapping[str, str] = field(default_factory=dict)
    sort: str | None = None
    page: int | None = None
    page_size: int | None = None

    def params(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for key, value in sorted(self.filter.items()):
            out.append((f"filter[{key}]", str(value)))
        if self.include:
            out.append(("include", ",".join(self.include)))
        if self.locale:
            out.append(("locale", self.locale))
        if self.page is not None:
            out.append(("page[number]", str(self.page)))
        if self.page_size is not None:
            out.append(("page[size]", str(self.page_size)))
        if self.sort:
            out.append(("sort", self.sort))
        if self.version:
            out.append(("version", self.version))
        return out


def detail_path(family: Family, identifier: str) -> str:
    return f"{family.path}/{quote(str(identifier), safe='')}"


def list_path(family: Family) -> str:
    return family.path


def build_request(base_url: str, path: str, query: Query, *, user_agent: str) -> Request:
    url = f"{base_url.rstrip('/')}/{path}"
    params = query.params()
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {"Accept": "application/json", "User-Agent": user_agent}
    return Request("GET", url, headers)
