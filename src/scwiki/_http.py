"""Transport-neutral HTTP primitives.

The core builds ``Request`` objects and consumes ``Response`` objects. Anything
that can turn one into the other satisfies a transport protocol; the library
never imports an HTTP client itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes


@runtime_checkable
class SyncTransport(Protocol):
    def send(self, request: Request) -> Response: ...

    def close(self) -> None: ...


@runtime_checkable
class AsyncTransport(Protocol):
    async def send(self, request: Request) -> Response: ...

    async def aclose(self) -> None: ...
