from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Entry:
    payload: Any
    stored_at: float
    expires_at: float | None
    version: str | None

    def is_fresh(self, now: float) -> bool:
        return self.expires_at is None or now < self.expires_at
