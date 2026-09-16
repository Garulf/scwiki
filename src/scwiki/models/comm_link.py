from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model
from scwiki.models.base import text as localized_text


@dataclass(frozen=True)
class CommLink(Model):
    id: int | None = None
    title: str | None = None
    channel: str | None = None
    series: str | None = None
    category: str | None = None
    created_at: str | None = None
    rsi_url: str | None = None
    images_count: int | None = None
    text: str | None = None

    _derive: ClassVar = {"text": localized_text("translations")}


@dataclass(frozen=True)
class CommLinkImage(Model):
    id: int | None = None
    name: str | None = None
    alt: str | None = None
    rsi_url: str | None = None
    mime_type: str | None = None
    size: int | None = None
    tags: tuple[str, ...] = ()
    last_modified: str | None = None

    _derive: ClassVar = {"tags": lambda d: tuple(str(t) for t in d.get("tags") or ())}
