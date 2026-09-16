from __future__ import annotations

from scwiki.errors import RateLimited, ServerError, TransportError

RETRY_DELAYS: tuple[float, ...] = (0.5, 1.5)


def should_retry(exc: BaseException, attempt: int) -> float | None:
    """Return the delay before retrying ``attempt`` (0-based), or None to give up."""
    if isinstance(exc, RateLimited):
        if attempt > 0:
            return None
        return exc.retry_after if exc.retry_after is not None else RETRY_DELAYS[0]
    if not isinstance(exc, ServerError | TransportError):
        return None
    if attempt >= len(RETRY_DELAYS):
        return None
    return RETRY_DELAYS[attempt]
