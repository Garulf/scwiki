"""SQLite-backed store. Safe to share between processes (WAL mode)."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from pathlib import Path

from scwiki.cache.entry import Entry
from scwiki.errors import CacheError

log = logging.getLogger("scwiki")

SWEEP_EVERY = 500
DEFAULT_MAX_BYTES = 256 * 1024 * 1024

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    key TEXT PRIMARY KEY,
    payload BLOB NOT NULL,
    stored_at REAL NOT NULL,
    expires_at REAL,
    version TEXT
);
CREATE INDEX IF NOT EXISTS entries_version ON entries(version);
CREATE INDEX IF NOT EXISTS entries_stored_at ON entries(stored_at);
"""


def default_cache_path() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    elif os.environ.get("XDG_CACHE_HOME"):
        base = Path(os.environ["XDG_CACHE_HOME"])
    else:
        base = Path.home() / ".cache"
    return base / "scwiki" / "cache.sqlite3"


class SqliteStore:
    def __init__(self, path: Path | str | None = None, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        self.max_bytes = max_bytes
        self._conn: sqlite3.Connection | None = None
        self._writes = 0

    def _connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = self._open()
        except sqlite3.DatabaseError as exc:
            self._quarantine(exc)
            self._conn = self._open()
        self.sweep()
        return self._conn

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        return conn

    def _quarantine(self, exc: Exception) -> None:
        aside = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time())}")
        log.warning("scwiki cache at %s is corrupt (%s); moving it to %s", self.path, exc, aside)
        try:
            self.path.replace(aside)
        except OSError as os_exc:
            raise CacheError(f"cannot move corrupt cache aside: {os_exc}") from os_exc

    def get(self, key: str) -> Entry | None:
        row = (
            self._connect()
            .execute(
                "SELECT payload, stored_at, expires_at, version FROM entries WHERE key = ?", (key,)
            )
            .fetchone()
        )
        if row is None:
            return None
        payload, stored_at, expires_at, version = row
        return Entry(json.loads(payload), stored_at, expires_at, version)

    def put(self, key: str, entry: Entry) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO entries(key, payload, stored_at, expires_at, version)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                key,
                json.dumps(entry.payload, separators=(",", ":")).encode(),
                entry.stored_at,
                entry.expires_at,
                entry.version,
            ),
        )
        self._writes += 1
        if self._writes % SWEEP_EVERY == 0:
            self.sweep()

    def delete(self, key: str) -> None:
        self._connect().execute("DELETE FROM entries WHERE key = ?", (key,))

    def purge(self, *, version: str | None = None, prefix: str | None = None) -> int:
        clauses: list[str] = []
        args: list[object] = []
        if version is not None:
            clauses.append("version = ?")
            args.append(version)
        if prefix is not None:
            clauses.append("key >= ? AND key < ?")
            args.extend([prefix, prefix + "￿"])
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = self._connect().execute(f"DELETE FROM entries{where}", args)
        return int(cur.rowcount)

    def sweep(self, now: float | None = None) -> None:
        conn = self._connect()
        now = time.time() if now is None else now
        conn.execute("DELETE FROM entries WHERE expires_at IS NOT NULL AND expires_at <= ?", (now,))
        while self._payload_bytes(conn) > self.max_bytes:
            count = int(conn.execute("SELECT count(*) FROM entries").fetchone()[0])
            batch = max(1, count // 10)
            conn.execute(
                "DELETE FROM entries WHERE key IN"
                " (SELECT key FROM entries ORDER BY stored_at ASC LIMIT ?)",
                (batch,),
            )

    @staticmethod
    def _payload_bytes(conn: sqlite3.Connection) -> int:
        total = conn.execute("SELECT coalesce(sum(length(payload)), 0) FROM entries").fetchone()[0]
        return int(total)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
