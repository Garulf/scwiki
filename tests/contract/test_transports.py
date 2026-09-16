"""Live checks against the real API. Enable with SCWIKI_NETWORK=1."""

from __future__ import annotations

import json
import os

import pytest

from scwiki._http import Request
from scwiki.client_base import USER_AGENT
from scwiki.transports.aiohttp import AiohttpTransport
from scwiki.transports.httpx import AsyncHttpxTransport, HttpxTransport
from scwiki.transports.urllib import UrllibTransport

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(os.environ.get("SCWIKI_NETWORK") != "1", reason="set SCWIKI_NETWORK=1"),
]

REQ = Request(
    "GET",
    "https://api.star-citizen.wiki/api/game-versions/default",
    {"Accept": "application/json", "User-Agent": USER_AGENT},
)


def _check(body: bytes, status: int) -> None:
    assert status == 200
    assert json.loads(body)["data"]["code"]


def test_urllib_live() -> None:
    res = UrllibTransport().send(REQ)
    _check(res.body, res.status)


def test_httpx_live() -> None:
    t = HttpxTransport()
    res = t.send(REQ)
    t.close()
    _check(res.body, res.status)


async def test_httpx_async_live() -> None:
    t = AsyncHttpxTransport()
    res = await t.send(REQ)
    await t.aclose()
    _check(res.body, res.status)


async def test_aiohttp_live() -> None:
    t = AiohttpTransport()
    res = await t.send(REQ)
    await t.aclose()
    _check(res.body, res.status)
