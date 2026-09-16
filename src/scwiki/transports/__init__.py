"""Transport adapters. The core never imports these; the clients resolve one lazily."""

from __future__ import annotations

from scwiki._http import AsyncTransport, SyncTransport
from scwiki.transports.urllib import UrllibTransport


def resolve_sync(timeout: float) -> SyncTransport:
    return UrllibTransport(timeout=timeout)


def resolve_async(timeout: float) -> AsyncTransport:
    try:
        from scwiki.transports.httpx import AsyncHttpxTransport
    except ImportError:
        pass
    else:
        return AsyncHttpxTransport(timeout=timeout)
    try:
        from scwiki.transports.aiohttp import AiohttpTransport
    except ImportError:
        pass
    else:
        return AiohttpTransport(timeout=timeout)
    raise ImportError(
        "no async HTTP library found: install scwiki[httpx] or scwiki[aiohttp],"
        " or pass transport= to AsyncClient"
    )


__all__ = ["UrllibTransport", "resolve_async", "resolve_sync"]
