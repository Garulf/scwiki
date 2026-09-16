"""aiohttp adapter. Requires ``scwiki[aiohttp]``."""

from __future__ import annotations

import aiohttp

from scwiki._http import Request, Response
from scwiki.errors import TransportError


class AiohttpTransport:
    def __init__(self, session: aiohttp.ClientSession | None = None, timeout: float = 20.0) -> None:
        self._session = session
        self._owned = session is None
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def send(self, request: Request) -> Response:
        try:
            async with self._get_session().request(
                request.method, request.url, headers=dict(request.headers)
            ) as res:
                body = await res.read()
                return Response(res.status, dict(res.headers.items()), body)
        except (TimeoutError, aiohttp.ClientError) as exc:
            raise TransportError(str(exc)) from exc

    async def aclose(self) -> None:
        if self._session is not None and self._owned:
            await self._session.close()
