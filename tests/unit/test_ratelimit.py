from scwiki.core.ratelimit import TokenBucket
from scwiki.core.retry import RETRY_DELAYS, should_retry
from scwiki.errors import ApiError, NotFound, RateLimited, ServerError, TransportError
from tests.conftest import FakeClock


def test_bucket_allows_rate_then_delays(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=60, per=60.0, clock=clock)
    assert all(bucket.acquire_delay() == 0.0 for _ in range(60))
    delay = bucket.acquire_delay()
    assert 0.0 < delay <= 60.0
    clock.advance(60.0)
    assert bucket.acquire_delay() == 0.0


def test_bucket_refills_gradually(clock: FakeClock) -> None:
    bucket = TokenBucket(rate=2, per=10.0, clock=clock)
    assert bucket.acquire_delay() == 0.0
    assert bucket.acquire_delay() == 0.0
    assert bucket.acquire_delay() == 5.0
    clock.advance(5.0)
    assert bucket.acquire_delay() == 5.0


def test_retry_policy() -> None:
    assert RETRY_DELAYS == (0.5, 1.5)
    assert should_retry(ServerError(500), 0) == 0.5
    assert should_retry(ServerError(500), 1) == 1.5
    assert should_retry(ServerError(500), 2) is None
    assert should_retry(TransportError("x"), 0) == 0.5
    assert should_retry(NotFound("v", "x"), 0) is None
    assert should_retry(ApiError(405), 0) is None
    assert should_retry(RateLimited(retry_after=2.0), 0) == 2.0
    assert should_retry(RateLimited(retry_after=2.0), 1) is None
    assert should_retry(RateLimited(), 0) == 0.5
    assert should_retry(ValueError("nope"), 0) is None
