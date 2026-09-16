from scwiki._http import Request, Response


def test_request_defaults_and_immutability() -> None:
    req = Request("GET", "https://example.test/x")
    assert req.headers == {}
    res = Response(200, {"content-type": "application/json"}, b"{}")
    assert res.status == 200
