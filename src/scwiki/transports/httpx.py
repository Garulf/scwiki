"""httpx adapters, sync and async. Requires ``scwiki[httpx]``."""

from __future__ import annotations

import httpx

from scwiki._http import Request, Response
from scwiki.errors import TransportError


def _to_response(res: httpx.Response) -> Response:
    return Response(res.status_code, dict(res.headers.items()), res.content)


class HttpxTransport:
    def __init__(self, client: httpx.Client | None = None, timeout: float = 20.0) -> None:
        self._client = client or httpx.Client(timeout=timeout)

    def send(self, request: Request) -> Response:
        try:
            res = self._client.request(request.method, request.url, headers=dict(request.headers))
        except httpx.HTTPError as exc:
            raise TransportError(str(exc)) from exc
        return _to_response(res)

    def close(self) -> None:
        self._client.close()


class AsyncHttpxTransport:
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 20.0) -> None:
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def send(self, request: Request) -> Response:
        try:
            res = await self._client.request(
                request.method, request.url, headers=dict(request.headers)
            )
        except httpx.HTTPError as exc:
            raise TransportError(str(exc)) from exc
        return _to_response(res)

    async def aclose(self) -> None:
        await self._client.aclose()
