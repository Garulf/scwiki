from __future__ import annotations

from dataclasses import dataclass

from scwiki.core.parse import Parsed

MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageInfo:
    current: int
    last: int
    total: int | None

    @property
    def has_next(self) -> bool:
        return self.current < self.last


def page_info(parsed: Parsed) -> PageInfo | None:
    meta = parsed.meta
    if "current_page" not in meta or "last_page" not in meta:
        return None
    return PageInfo(int(meta["current_page"]), int(meta["last_page"]), meta.get("total"))
