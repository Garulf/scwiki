import pytest

from scwiki._http import Response
from scwiki.core.paging import page_info
from scwiki.core.parse import parse_response
from scwiki.errors import ApiError, NotFound, RateLimited, ServerError
from tests.conftest import fixture_bytes, load_fixture

HTML = b"<!DOCTYPE html><html><title>404 - Signal Lost</title></html>"


def test_detail_payload_returns_data_and_meta() -> None:
    res = Response(200, {}, fixture_bytes("vehicles.detail"))
    parsed = parse_response(res, family="vehicles", identifier="aegs-avenger-stalker")
    assert parsed.data["slug"] == "aegs-avenger-stalker"
    assert parsed.meta["resource"]["type"] == "vehicle"
    assert parsed.links == {}


def test_list_payload_keeps_links() -> None:
    res = Response(200, {}, fixture_bytes("vehicles.list"))
    parsed = parse_response(res, family="vehicles", identifier=None)
    assert isinstance(parsed.data, list)
    assert parsed.links["first"]


def test_404_raises_not_found_with_context() -> None:
    with pytest.raises(NotFound) as exc:
        parse_response(Response(404, {}, HTML), family="vehicles", identifier="nope")
    assert exc.value.family == "vehicles"
    assert exc.value.identifier == "nope"


def test_429_reads_retry_after() -> None:
    with pytest.raises(RateLimited) as exc:
        parse_response(Response(429, {"Retry-After": "7"}, b""), family="search", identifier=None)
    assert exc.value.retry_after == 7.0


def test_429_without_header() -> None:
    with pytest.raises(RateLimited) as exc:
        parse_response(Response(429, {}, b""), family="search", identifier=None)
    assert exc.value.retry_after is None


def test_5xx_raises_server_error() -> None:
    with pytest.raises(ServerError) as exc:
        parse_response(Response(503, {}, b"down"), family="vehicles", identifier=None)
    assert exc.value.status == 503


def test_other_4xx_raises_api_error() -> None:
    with pytest.raises(ApiError) as exc:
        parse_response(Response(405, {}, b""), family="vehicles", identifier=None)
    assert exc.value.status == 405
    assert not isinstance(exc.value, NotFound)


def test_non_json_200_raises_api_error() -> None:
    with pytest.raises(ApiError):
        parse_response(Response(200, {}, HTML), family="vehicles", identifier=None)


def test_payload_without_data_key_is_wrapped() -> None:
    res = Response(200, {}, b'{"filters": {"size": []}}')
    parsed = parse_response(res, family="vehicles", identifier="filters")
    assert parsed.data == {"filters": {"size": []}}


def test_page_info_for_list_and_detail() -> None:
    lst = parse_response(
        Response(200, {}, fixture_bytes("vehicles.list")), family="vehicles", identifier=None
    )
    info = page_info(lst)
    assert info is not None
    assert info.current == 1
    assert info.last == load_fixture("vehicles.list")["meta"]["last_page"]
    assert info.total == 297
    det = parse_response(
        Response(200, {}, fixture_bytes("vehicles.detail")), family="vehicles", identifier="x"
    )
    assert page_info(det) is None
