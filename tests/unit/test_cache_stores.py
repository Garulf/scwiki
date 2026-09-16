from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

import pytest

from scwiki.cache.entry import Entry
from scwiki.cache.lru import LruFront
from scwiki.cache.sqlite import SqliteStore, default_cache_path
from scwiki.cache.store import CacheStore, MemoryStore


def entry(
    payload: object = "x",
    version: str | None = None,
    expires_at: float | None = None,
    stored_at: float = 1.0,
) -> Entry:
    return Entry(payload, stored_at=stored_at, expires_at=expires_at, version=version)


def stores(tmp_path: Path) -> list[CacheStore]:
    return [MemoryStore(), SqliteStore(tmp_path / "c.sqlite3"), LruFront(MemoryStore(), maxsize=4)]


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_roundtrip_and_delete(tmp_path: Path, idx: int) -> None:
    store = stores(tmp_path)[idx]
    assert store.get("k") is None
    store.put("k", entry({"a": [1, 2]}, version="v1", expires_at=5.0))
    got = store.get("k")
    assert got is not None
    assert got.payload == {"a": [1, 2]}
    assert got.version == "v1"
    assert got.expires_at == 5.0
    store.delete("k")
    assert store.get("k") is None
    store.close()


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_purge_by_version_and_prefix(tmp_path: Path, idx: int) -> None:
    store = stores(tmp_path)[idx]
    store.put("vehicles|a|old", entry(version="old"))
    store.put("vehicles|b|new", entry(version="new"))
    store.put("items|c|old", entry(version="old"))
    assert store.purge(version="old") == 2
    assert store.get("vehicles|b|new") is not None
    store.put("items|d|-", entry())
    assert store.purge(prefix="items|") == 1
    assert store.purge() == 1
    assert store.get("vehicles|b|new") is None


def test_lru_evicts_oldest_but_keeps_backing_store() -> None:
    backing = MemoryStore()
    lru = LruFront(backing, maxsize=2)
    for k in "abc":
        lru.put(k, entry(k))
    assert lru.cached_keys() == ["b", "c"]
    got = lru.get("a")
    assert got is not None and got.payload == "a"
    assert lru.cached_keys() == ["c", "a"]


def test_lru_front_without_backing_store() -> None:
    lru = LruFront(None, maxsize=2)
    lru.put("a", entry("a"))
    assert lru.get("a") is not None
    assert lru.purge() == 1


def test_sqlite_persists_across_reopen(tmp_path: Path) -> None:
    path = tmp_path / "c.sqlite3"
    s = SqliteStore(path)
    s.put("k", entry({"n": 1}, version="v"))
    s.close()
    s2 = SqliteStore(path)
    got = s2.get("k")
    assert got is not None and got.payload == {"n": 1}
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_sqlite_sweep_removes_expired_and_trims_to_budget(tmp_path: Path) -> None:
    s = SqliteStore(tmp_path / "c.sqlite3", max_bytes=6000)
    s.put("expired", entry("x", expires_at=10.0, stored_at=1.0))
    big = "y" * 2000
    for i in range(6):
        s.put(f"big{i}", entry(big, stored_at=float(i)))
    s.sweep(now=20.0)
    assert s.get("expired") is None
    remaining = [k for k in (f"big{i}" for i in range(6)) if s.get(k) is not None]
    assert remaining
    assert "big5" in remaining
    assert "big0" not in remaining


def test_sqlite_recovers_from_corrupt_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "c.sqlite3"
    path.write_bytes(b"this is not a database")
    with caplog.at_level(logging.WARNING, logger="scwiki"):
        s = SqliteStore(path)
        s.put("k", entry("v"))
    assert s.get("k") is not None
    assert any(p.name.startswith("c.sqlite3.corrupt-") for p in tmp_path.iterdir())
    assert "corrupt" in caplog.text.lower()


def test_default_cache_path_honours_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert default_cache_path() == tmp_path / "scwiki" / "cache.sqlite3"


def test_default_cache_path_falls_back_to_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert default_cache_path() == tmp_path / ".cache" / "scwiki" / "cache.sqlite3"
