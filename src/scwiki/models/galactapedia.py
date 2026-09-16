from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from scwiki.models.base import Model, nested_list
from scwiki.models.base import text as localized_text
from scwiki.models.common import Named


@dataclass(frozen=True)
class GalactapediaArticle(Model):
    id: str | None = None
    title: str | None = None
    slug: str | None = None
    type: str | None = None
    template: str | None = None
    thumbnail: str | None = None
    rsi_url: str | None = None
    created_at: str | None = None
    categories: tuple[Named, ...] = ()
    tags: tuple[Named, ...] = ()
    text: str | None = None

    _derive: ClassVar = {
        "categories": nested_list("categories", Named),
        "tags": nested_list("tags", Named),
        "text": localized_text("translations"),
    }
