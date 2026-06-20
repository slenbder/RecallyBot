from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Review:
    source: str               # "yandex" | "dgis" | "google"
    author: str | None        # Yandex emails do not include the reviewer name
    date: str                 # ISO-8601 date string as parsed from email
    text: str | None
    rating: int | None = None # 1-5, None if not present
    url: str | None = None

    @property
    def dedup_key(self) -> str:
        payload = (
            self.source
            + (self.author or "").strip().lower()
            + (self.date or "")
            + (self.text or "")[:100]
        )
        return hashlib.sha256(payload.encode()).hexdigest()
