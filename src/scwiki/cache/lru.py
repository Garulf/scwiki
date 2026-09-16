from __future__ import annotations

from collections import OrderedDict

from scwiki.cache.entry import Entry
from scwiki.cache.store import CacheStore, _matches


class LruFront:
    """In-process LRU in front of an optional persistent store."""

    def __init__(self, store: CacheStore | None, maxsize: int = 512) -> None:
        self.store = store
        self.maxsize = maxsize
        self._hot: OrderedDict[str, Entry] = OrderedDict()

    def cached_keys(self) -> list[str]:
        return list(self._hot)

    def _remember(self, key: str, entry: Entry) -> None:
        self._hot[key] = entry
        self._hot.move_to_end(key)
        while len(self._hot) > self.maxsize:
            self._hot.popitem(last=False)

    def get(self, key: str) -> Entry | None:
        hit = self._hot.get(key)
        if hit is not None:
            self._hot.move_to_end(key)
            return hit
        if self.store is None:
            return None
        entry = self.store.get(key)
        if entry is not None:
            self._remember(key, entry)
        return entry

    def put(self, key: str, entry: Entry) -> None:
        self._remember(key, entry)
        if self.store is not None:
            self.store.put(key, entry)

    def delete(self, key: str) -> None:
        self._hot.pop(key, None)
        if self.store is not None:
            self.store.delete(key)

    def purge(self, *, version: str | None = None, prefix: str | None = None) -> int:
        doomed = [k for k, e in self._hot.items() if _matches(k, e, version, prefix)]
        for k in doomed:
            del self._hot[k]
        if self.store is not None:
            return self.store.purge(version=version, prefix=prefix)
        return len(doomed)

    def close(self) -> None:
        self._hot.clear()
        if self.store is not None:
            self.store.close()
