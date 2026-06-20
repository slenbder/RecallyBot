from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from imap_tools import MailMessage

from ...models import Review
from .html_utils import slice_html_by_comment

log = logging.getLogger(__name__)

_FILLED_STAR_HASH = "b883dfce-1e0a-49be-9291-8e4d3f8acc13"


class YandexParser:
    source = "yandex"

    def is_review(self, msg: MailMessage) -> bool:
        if "отзыв" in (msg.subject or "").lower():
            return True
        h = msg.html or ""
        return "<!-- review -->" in h or "<!-- stars -->" in h

    def parse(self, msg: MailMessage) -> Review | None:
        try:
            return self._parse(msg)
        except Exception:
            log.exception("YandexParser raised for uid=%s", getattr(msg, "uid", "?"))
            return None

    def _parse(self, msg: MailMessage) -> Review | None:
        raw_html = msg.html or ""
        if not raw_html:
            return None

        # Yandex review emails do not include the reviewer name
        author = None

        text = _extract_text(raw_html)
        if not text:
            return None

        rating = _extract_rating(raw_html)
        url = _extract_url(raw_html)
        dt = msg.date.isoformat() if msg.date else ""

        return Review(
            source=self.source,
            author=author,
            date=dt,
            text=text,
            rating=rating,
            url=url,
        )


def _extract_text(raw_html: str) -> str | None:
    slice_ = slice_html_by_comment(raw_html, "review")
    if not slice_:
        return None
    soup = BeautifulSoup(slice_, "html.parser")
    # Take the longest text node — avoids short button labels like "Ответить"
    texts = [s.strip() for s in soup.strings if s.strip()]
    if not texts:
        return None
    return max(texts, key=len)


def _extract_rating(raw_html: str) -> int | None:
    # ASSUMPTION pending a low-rating sample — we don't yet know
    # whether empty stars use a different hash or are absent. Validate later.
    slice_ = slice_html_by_comment(raw_html, "stars")
    if not slice_:
        return None
    soup = BeautifulSoup(slice_, "html.parser")
    count = sum(
        _FILLED_STAR_HASH in (img.get("src") or "") for img in soup.find_all("img")
    )
    return count if 1 <= count <= 5 else None


def _extract_url(raw_html: str) -> str | None:
    slice_ = slice_html_by_comment(raw_html, "review")
    if not slice_:
        return None
    soup = BeautifulSoup(slice_, "html.parser")
    a = soup.find("a", href=True)
    return a["href"] if a else None
