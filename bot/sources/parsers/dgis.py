from __future__ import annotations

import base64
import logging
import re
from urllib.parse import parse_qs, urlparse

from imap_tools import MailMessage

from ...models import Review
from .html_utils import get_html_soup, get_plain_text

log = logging.getLogger(__name__)

_FILLED_STAR_HASH = "da4c269728c1678632b1590dabb9f4df"


class DgisParser:
    source = "dgis"

    def is_review(self, msg: MailMessage) -> bool:
        if "отзыв" in (msg.subject or "").lower():
            return True
        soup = get_html_soup(msg)
        return soup is not None and soup.select_one("td.stars") is not None

    def parse(self, msg: MailMessage) -> list[Review]:
        try:
            review = self._parse(msg)
            return [review] if review is not None else []
        except Exception:
            log.exception("DgisParser raised for uid=%s", getattr(msg, "uid", "?"))
            return []

    def _parse(self, msg: MailMessage) -> Review | None:
        plain = get_plain_text(msg)
        text = plain.replace("\r\n", "\n").replace("\r", "\n")
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
        soup = get_html_soup(msg)
        review_text = _extract_review_text(soup) or blocks[header_idx + 2]

        if not author or not review_text:
            return None

        url = None
        for block in blocks[header_idx + 2 :]:
            m = re.search(r"Читать полностью \((https?://[^)]+)\)", block)
            if m:
                url = _decode_tracker_url(m.group(1))
                break

        rating = _extract_rating(soup)
        dt = msg.date.isoformat() if msg.date else ""

        return Review(
            source=self.source,
            author=author,
            date=dt,
            text=review_text,
            rating=rating,
            url=url,
        )


def _extract_review_text(soup) -> str | None:
    if soup is None:
        return None
    tag = soup.select_one("div.text")
    if tag is None:
        return None
    text = tag.get_text(separator=" ").strip()
    return re.sub(r"\s+", " ", text) if text else None


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


def _extract_rating(soup) -> int | None:
    # 2GIS always renders exactly 5 <img> tags in td.stars regardless of rating:
    # filled star hash: da4c269728c1678632b1590dabb9f4df
    # empty  star hash: da6adc9504b90b97bb3e48b35b3230b3
    # Counting only filled imgs gives the exact rating (confirmed on 1★ and 5★ samples).
    if soup is None:
        return None
    td = soup.select_one("td.stars")
    if td is None:
        return None
    count = sum(
        _FILLED_STAR_HASH in (img.get("src") or "") for img in td.select("img")
    )
    return count if 1 <= count <= 5 else None
