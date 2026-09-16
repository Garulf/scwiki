from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from scwiki._http import Request, Response

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    with (FIXTURES / f"{name}.json").open() as fh:
        return json.load(fh)


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes()


def json_response(payload: Any, status: int = 200) -> Response:
    body = json.dumps(payload).encode()
    return Response(status, {"content-type": "application/json"}, body)


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeTransport:
    """Sync transport that replays queued responses and records requests."""

    def __init__(self, responses: list[Response] | None = None) -> None:
        self.queue: deque[Response] = deque(responses or [])
        self.requests: list[Request] = []
        self.closed = False

    def push(self, response: Response) -> None:
        self.queue.append(response)

    def send(self, request: Request) -> Response:
        self.requests.append(request)
        if not self.queue:
            raise AssertionError(f"unexpected request {request.url}")
        return self.queue.popleft()

    def close(self) -> None:
        self.closed = True


class AsyncFakeTransport(FakeTransport):
    async def send(self, request: Request) -> Response:  # type: ignore[override]
        return FakeTransport.send(self, request)

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
