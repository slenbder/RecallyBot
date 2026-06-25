from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage

from ...models import Review

log = logging.getLogger(__name__)

_FILLED_STAR_HASH = "b883dfce-1e0a-49be-9291-8e4d3f8acc13"

_REVIEW_BLOCK_RE = re.compile(
    r"<!-- review -->(.*?)<!-- review END -->", re.DOTALL
)
_STARS_BLOCK_RE = re.compile(
    r"<!-- stars -->(.*?)<!-- stars END -->", re.DOTALL
)


class YandexParser:
    source = "yandex"

    def is_review(self, msg: MailMessage) -> bool:
        if "отзыв" in (msg.subject or "").lower():
            return True
        h = msg.html or ""
        return "<!-- review -->" in h or "<!-- stars -->" in h

    def parse(self, msg: MailMessage) -> list[Review]:
        try:
            return self._parse(msg)
        except Exception:
            log.exception("YandexParser raised for uid=%s", getattr(msg, "uid", "?"))
            return []

    def _parse(self, msg: MailMessage) -> list[Review]:
        raw_html = msg.html or ""
        if not raw_html:
            return []

        dt = msg.date.isoformat() if msg.date else ""
        results: list[Review] = []

        for block in _REVIEW_BLOCK_RE.findall(raw_html):
            text = _extract_text(block)
            rating = _extract_rating(block)
            url = _extract_url(block)
            # Known limitation: two rating-only reviews with no text in the same
            # digest would share a dedup key and collapse — acceptable for now.
            results.append(
                Review(
                    source=self.source,
                    author=None,
                    date=dt,
                    text=text,
                    rating=rating,
                    url=url,
                )
            )

        return results


def _extract_text(block: str) -> str | None:
    soup = BeautifulSoup(block, "html.parser")
    # Take the longest text node — avoids short button labels like "Ответить"
    texts = [s.strip() for s in soup.strings if s.strip()]
    if not texts:
        return None
    return max(texts, key=len)


def _extract_rating(block: str) -> int | None:
    m = _STARS_BLOCK_RE.search(block)
    if not m:
        return None
    stars_soup = BeautifulSoup(m.group(1), "html.parser")
    count = sum(
        _FILLED_STAR_HASH in (img.get("src") or "")
        for img in stars_soup.find_all("img")
    )
    return count if 1 <= count <= 5 else None


def _extract_url(block: str) -> str | None:
    soup = BeautifulSoup(block, "html.parser")
    a = soup.find("a", href=True)
    return a["href"] if a else None
