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
