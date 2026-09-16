from __future__ import annotations

import asyncio

import httpx
import pytest
from aiohttp import web

from scwiki._http import Request
from scwiki.errors import TransportError
from scwiki.transports import resolve_async, resolve_sync
from scwiki.transports.aiohttp import AiohttpTransport
from scwiki.transports.httpx import AsyncHttpxTransport, HttpxTransport
from scwiki.transports.urllib import UrllibTransport

REQ = Request("GET", "https://api.test/api/x", {"Accept": "application/json", "User-Agent": "t"})


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("boom"):
        raise httpx.ConnectError("nope")
    assert request.headers["user-agent"] == "t"
    return httpx.Response(404, headers={"x-test": "1"}, content=b"<html>")


def test_httpx_sync_maps_response_and_errors() -> None:
    t = HttpxTransport(httpx.Client(transport=httpx.MockTransport(_handler)))
    res = t.send(REQ)
    assert res.status == 404 and res.body == b"<html>" and res.headers["x-test"] == "1"
    with pytest.raises(TransportError):
        t.send(Request("GET", "https://api.test/boom"))
    t.close()


async def test_httpx_async_maps_response_and_errors() -> None:
    t = AsyncHttpxTransport(httpx.AsyncClient(transport=httpx.MockTransport(_handler)))
    res = await t.send(REQ)
    assert res.status == 404 and res.body == b"<html>"
    with pytest.raises(TransportError):
        await t.send(Request("GET", "https://api.test/boom"))
    await t.aclose()


async def test_aiohttp_maps_response_and_errors() -> None:
    async def hello(request: web.Request) -> web.Response:
        assert request.headers["User-Agent"] == "t"
        return web.Response(status=404, body=b"<html>", headers={"x-test": "1"})

    app = web.Application()
    app.router.add_get("/api/x", hello)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    t = AiohttpTransport()
    try:
        res = await t.send(Request("GET", f"http://127.0.0.1:{port}/api/x", REQ.headers))
        assert res.status == 404 and res.body == b"<html>" and res.headers["x-test"] == "1"
        with pytest.raises(TransportError):
            await t.send(Request("GET", "http://127.0.0.1:1/nothing"))
    finally:
        await t.aclose()
        await runner.cleanup()


def test_urllib_maps_errors() -> None:
    t = UrllibTransport(timeout=1.0)
    with pytest.raises(TransportError):
        t.send(Request("GET", "http://127.0.0.1:1/nothing"))
    t.close()


def test_resolvers() -> None:
    assert isinstance(resolve_sync(1.0), UrllibTransport)
    assert isinstance(resolve_async(1.0), AsyncHttpxTransport)


async def test_async_client_resolves_transport_lazily() -> None:
    from scwiki import AsyncClient

    client = AsyncClient(cache=None)
    assert client._transport is None
    assert isinstance(client._get_transport(), AsyncHttpxTransport)
    await client.aclose()
    await asyncio.sleep(0)
