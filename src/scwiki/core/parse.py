"""Turn raw responses into parsed payloads or typed errors."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from scwiki._http import Response
from scwiki.errors import ApiError, NotFound, RateLimited, ServerError


@dataclass(frozen=True)
class Parsed:
    data: Any
    meta: Mapping[str, Any] = field(default_factory=dict)
    links: Mapping[str, Any] = field(default_factory=dict)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = _header(headers, "Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_response(response: Response, *, family: str, identifier: str | None) -> Parsed:
    status = response.status
    if status == 404:
        raise NotFound(family, identifier)
    if status == 429:
        raise RateLimited(_retry_after(response.headers), response.body)
    if status >= 500:
        raise ServerError(status, response.body)
    if status >= 400:
        raise ApiError(status, response.body)
    try:
        payload = json.loads(response.body)
    except ValueError as exc:
        raise ApiError(status, response.body, message="API returned a non-JSON body") from exc
    if isinstance(payload, dict) and "data" in payload:
        return Parsed(payload["data"], payload.get("meta") or {}, payload.get("links") or {})
    return Parsed(payload)
