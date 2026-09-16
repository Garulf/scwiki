"""Stdlib transport. Zero dependencies, synchronous."""

from __future__ import annotations

import urllib.error
import urllib.request

from scwiki._http import Request, Response
from scwiki.errors import TransportError


class UrllibTransport:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def send(self, request: Request) -> Response:
        req = urllib.request.Request(
            request.url, headers=dict(request.headers), method=request.method
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as fh:
                return Response(fh.status, dict(fh.headers.items()), fh.read())
        except urllib.error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return Response(exc.code, dict(exc.headers.items()), body)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(str(exc)) from exc

    def close(self) -> None:
        return None
