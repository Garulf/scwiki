from __future__ import annotations


class ScwikiError(Exception):
    """Base class for every error raised by scwiki."""


class TransportError(ScwikiError):
    """The HTTP transport could not complete the request."""


class CacheError(ScwikiError):
    """The cache store failed."""


class ApiError(ScwikiError):
    def __init__(self, status: int, body: bytes = b"", message: str | None = None) -> None:
        self.status = status
        self.body = body
        super().__init__(message or f"API returned HTTP {status}")


class NotFound(ApiError):
    def __init__(self, family: str, identifier: str | None) -> None:
        self.family = family
        self.identifier = identifier
        super().__init__(404, message=f"{family}: {identifier!r} not found")


class RateLimited(ApiError):
    def __init__(self, retry_after: float | None = None, body: bytes = b"") -> None:
        self.retry_after = retry_after
        super().__init__(429, body, message="rate limited by the API")


class ServerError(ApiError):
    def __init__(self, status: int, body: bytes = b"") -> None:
        super().__init__(status, body, message=f"API server error HTTP {status}")
