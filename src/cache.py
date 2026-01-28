from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SqliteCache:
    """Tiny sqlite cache for expensive web calls.

    Values are stored as JSON strings with a created_at timestamp.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # `:memory:` is supported for tests.
        if self.path != ":memory:":
            p = Path(self.path)
            p.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_cache (
                  k TEXT PRIMARY KEY,
                  v TEXT NOT NULL,
                  created_at INTEGER NOT NULL
                )
                """
            )

    def get(self, key: str, *, max_age_s: int | None) -> Any | None:
        now = int(time.time())
        with self._connect() as con:
            row = con.execute("SELECT v, created_at FROM kv_cache WHERE k=?", (key,)).fetchone()
        if not row:
            return None
        v, created_at = row
        if max_age_s is not None and now - int(created_at) > max_age_s:
            return None
        try:
            return json.loads(v)
        except Exception:
            return v

    def set(self, key: str, value: Any) -> None:
        now = int(time.time())
        payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO kv_cache(k, v, created_at) VALUES(?, ?, ?)",
                (key, payload, now),
            )

