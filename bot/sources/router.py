from __future__ import annotations

from imap_tools import MailMessage

from .parsers.base import Parser
from .parsers.yandex import YandexParser
from .parsers.dgis import DgisParser
from .parsers.google import GoogleParser

_DOMAIN_MAP: list[tuple[tuple[str, ...], Parser]] = [
    (("yandex.ru", "yandex.com", "ya.ru"), YandexParser()),
    (("2gis.ru", "2gis.com"), DgisParser()),
    (("google.com", "business.google.com"), GoogleParser()),
]


def _sender_domain(msg: MailMessage) -> str:
    """Return the domain part of the From address, lower-cased."""
    addr = msg.from_ or ""
    if "<" in addr:
        addr = addr.split("<", 1)[1].rstrip(">")
    return addr.partition("@")[2].lower()


def resolve(msg: MailMessage) -> Parser | None:
    """Return the matching Parser, or None if no domain rule matches."""
    domain = _sender_domain(msg)
    for domains, parser in _DOMAIN_MAP:
        if any(domain == d or domain.endswith("." + d) for d in domains):
            return parser
    return None


def source_hint(msg: MailMessage) -> str:
    """Human-readable source label for the raw fallback message."""
    domain = _sender_domain(msg)
    if not domain:
        return msg.from_ or "unknown"
    for domains, parser in _DOMAIN_MAP:
        if any(domain == d or domain.endswith("." + d) for d in domains):
            return parser.source
    return domain
