from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Review


class Storage:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_reviews (
                dedup_key TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS heartbeat (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_poll_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def is_new(self, review: Review) -> bool:
        """Insert dedup record. Returns True only when the row is genuinely new."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO seen_reviews (dedup_key, created_at) VALUES (?, ?)",
            (review.dedup_key, _now()),
        )
        self._conn.commit()
        return cur.rowcount == 1

    def record_heartbeat(self) -> None:
        self._conn.execute(
            """INSERT INTO heartbeat (id, last_poll_at) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET last_poll_at = excluded.last_poll_at""",
            (_now(),),
        )
        self._conn.commit()

    def last_poll_at(self) -> datetime | None:
        row = self._conn.execute(
            "SELECT last_poll_at FROM heartbeat WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])

    def close(self) -> None:
        self._conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
