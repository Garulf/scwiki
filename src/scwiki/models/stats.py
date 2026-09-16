from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from scwiki.models.base import Model


@dataclass(frozen=True)
class Stats(Model):
    funds: Decimal | None = None
    fans: int | None = None
    fleet: int | None = None
    timestamp: str | None = None

    _derive: ClassVar = {
        "funds": lambda d: None if d.get("funds") is None else Decimal(str(d["funds"]))
    }
