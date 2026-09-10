"""Simple TTL cache layer backed by SQLite for request caching."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class RequestCache:
    def __init__(
        self,
        cache_db: Optional[str] = None,
        default_ttl_seconds: int = 86400,
        db_path: Optional[str] = None,
    ):
        target_db = db_path or cache_db or "data/cache.db"
        self.default_ttl = default_ttl_seconds
        if target_db != ":memory:":
            Path(target_db).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(target_db, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS http_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
            """)

    @staticmethod
    def generate_key(prefix: str, params: Any) -> str:
        serialized = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        return f"{prefix}:{digest}"

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT payload, expires_at FROM http_cache WHERE cache_key = ?", (key,)
        )
        row = cur.fetchone()
        if not row:
            return None
        payload_str, expires_at = row
        if now > expires_at:
            # Expired
            with self.conn:
                self.conn.execute("DELETE FROM http_cache WHERE cache_key = ?", (key,))
            return None
        try:
            return json.loads(payload_str)
        except Exception:
            return payload_str

    def set(self, key: str, payload: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()
        expires_at = now + ttl
        payload_str = json.dumps(payload, default=str)
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO http_cache (cache_key, payload, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload=excluded.payload,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at
                """,
                (key, payload_str, now, expires_at),
            )

    def close(self) -> None:
        self.conn.close()


# Alias for backward/forward naming compatibility
SQLiteCache = RequestCache

