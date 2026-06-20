from __future__ import annotations

import base64
import html
import logging
import re
from urllib.parse import parse_qs, urlparse

from imap_tools import MailMessage

from ...models import Review

log = logging.getLogger(__name__)

_FILLED_STAR_HASH = "da4c269728c1678632b1590dabb9f4df"


class DgisParser:
    source = "dgis"

    def is_review(self, msg: MailMessage) -> bool:
        if "отзыв" in (msg.subject or "").lower():
            return True
        h = msg.html or ""
        return 'class="stars"' in h

    def parse(self, msg: MailMessage) -> Review | None:
        try:
            return self._parse(msg)
        except Exception:
            log.exception("DgisParser raised for uid=%s", getattr(msg, "uid", "?"))
            return None

    def _parse(self, msg: MailMessage) -> Review | None:
        text = msg.text or ""
        blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]

        header_idx = None
        for i, block in enumerate(blocks):
            if "написали" in block and "отзыв" in block:
                header_idx = i
                break

        if header_idx is None or header_idx + 2 >= len(blocks):
            return None

        author = blocks[header_idx + 1]

        # HTML extraction preserves correct word spacing lost in the text/plain block
        review_text = _extract_review_text(msg.html or "") or blocks[header_idx + 2]

        if not author or not review_text:
            return None

        url = None
        for block in blocks[header_idx + 2 :]:
            m = re.search(r"Читать полностью \((https?://[^)]+)\)", block)
            if m:
                url = _decode_tracker_url(m.group(1))
                break

        rating = _extract_rating(msg.html or "")
        dt = msg.date.isoformat() if msg.date else ""

        return Review(
            source=self.source,
            author=author,
            date=dt,
            text=review_text,
            rating=rating,
            url=url,
        )


def _extract_review_text(raw_html: str) -> str | None:
    """Return the review text from the first non-link <div class="text"> in the HTML."""
    for raw in re.findall(r'<div class="text">(.*?)</div>', raw_html, re.DOTALL):
        stripped = raw.strip()
        if stripped and not stripped.startswith("<"):
            return html.unescape(re.sub(r"\s+", " ", stripped))
    return None


def _decode_tracker_url(tracker_url: str) -> str:
    """Decode the base64url `url=` param; falls back to the raw tracker URL on error."""
    try:
        params = parse_qs(urlparse(tracker_url).query)
        encoded = params.get("url", [""])[0]
        if not encoded:
            return tracker_url
        # 2GIS tracker encodes with ~ for = padding; map to standard base64
        encoded = encoded.replace("~", "=").replace("-", "+").replace("_", "/")
        return base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return tracker_url


def _extract_rating(raw_html: str) -> int | None:
    # ASSUMPTION pending a low-rating sample — we don't yet know
    # the empty-star hash or whether 4★ renders as 4 imgs or 5. Validate later.
    m = re.search(
        r'<td\b[^>]*class="stars"[^>]*>(.*?)</td>', raw_html, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None
    count = m.group(1).count(_FILLED_STAR_HASH)
    return count if 1 <= count <= 5 else None
