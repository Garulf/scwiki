"""Token bucket used to stay under the API's search rate limit."""

from __future__ import annotations

import time
from collections.abc import Callable


class TokenBucket:
    def __init__(self, rate: int, per: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.rate = rate
        self.per = per
        self._clock = clock
        self._tokens = float(rate)
        self._updated = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        self._updated = now
        self._tokens = min(float(self.rate), self._tokens + elapsed * self.rate / self.per)

    def acquire_delay(self) -> float:
        """Reserve one call and return how long the caller must wait before making it."""
        self._refill()
        self._tokens -= 1.0
        if self._tokens >= 0.0:
            return 0.0
        return -self._tokens * self.per / self.rate
