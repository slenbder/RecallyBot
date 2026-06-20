from __future__ import annotations

from bs4 import BeautifulSoup
from imap_tools import MailMessage


def get_html_soup(msg: MailMessage) -> BeautifulSoup | None:
    raw = msg.html
    if not raw:
        return None
    return BeautifulSoup(raw, "html.parser")


def get_plain_text(msg: MailMessage) -> str:
    return msg.text or ""


def slice_html_by_comment(html: str, name: str) -> str | None:
    """Return the substring between '<!-- name -->' and '<!-- name END -->', or None."""
    start_marker = f"<!-- {name} -->"
    end_marker = f"<!-- {name} END -->"
    start = html.find(start_marker)
    if start == -1:
        return None
    start += len(start_marker)
    end = html.find(end_marker, start)
    if end == -1:
        return None
    return html[start:end]
