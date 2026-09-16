from __future__ import annotations

from typing import Protocol, runtime_checkable

from scwiki.cache.entry import Entry


@runtime_checkable
class CacheStore(Protocol):
    def get(self, key: str) -> Entry | None: ...

    def put(self, key: str, entry: Entry) -> None: ...

    def delete(self, key: str) -> None: ...

    def purge(self, *, version: str | None = None, prefix: str | None = None) -> int: ...

    def close(self) -> None: ...


def _matches(key: str, entry: Entry, version: str | None, prefix: str | None) -> bool:
    if version is not None and entry.version != version:
        return False
    return prefix is None or key.startswith(prefix)


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, Entry] = {}

    def get(self, key: str) -> Entry | None:
        return self._data.get(key)

    def put(self, key: str, entry: Entry) -> None:
        self._data[key] = entry

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def purge(self, *, version: str | None = None, prefix: str | None = None) -> int:
        doomed = [k for k, e in self._data.items() if _matches(k, e, version, prefix)]
        for k in doomed:
            del self._data[k]
        return len(doomed)

    def close(self) -> None:
        self._data.clear()
