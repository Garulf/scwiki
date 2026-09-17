"""Python client for the Star Citizen Wiki API."""

__version__ = "0.2.0"  # x-release-please-version

from scwiki._http import AsyncTransport, Request, Response, SyncTransport
from scwiki.cache import CacheStore, LruFront, MemoryStore, SqliteStore
from scwiki.client import AsyncClient, Client
from scwiki.errors import (
    ApiError,
    CacheError,
    NotFound,
    RateLimited,
    ScwikiError,
    ServerError,
    TransportError,
)

__all__ = [
    "ApiError",
    "AsyncClient",
    "AsyncTransport",
    "CacheError",
    "CacheStore",
    "Client",
    "LruFront",
    "MemoryStore",
    "NotFound",
    "RateLimited",
    "Request",
    "Response",
    "ScwikiError",
    "ServerError",
    "SqliteStore",
    "SyncTransport",
    "TransportError",
    "__version__",
]
