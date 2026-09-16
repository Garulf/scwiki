from scwiki.errors import ApiError, NotFound, RateLimited, ScwikiError, ServerError, TransportError


def test_not_found_is_api_error_and_names_resource() -> None:
    err = NotFound("vehicles", "nope")
    assert isinstance(err, ApiError)
    assert isinstance(err, ScwikiError)
    assert err.status == 404
    assert "vehicles" in str(err)
    assert "nope" in str(err)


def test_rate_limited_carries_retry_after() -> None:
    assert RateLimited(retry_after=3.0).retry_after == 3.0
    assert RateLimited().retry_after is None
    assert RateLimited().status == 429


def test_server_error_status() -> None:
    assert ServerError(503).status == 503


def test_transport_error_is_scwiki_error() -> None:
    assert isinstance(TransportError("boom"), ScwikiError)
