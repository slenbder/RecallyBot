from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from imap_tools import MailBox, MailMessage, AND

from ..config import settings

log = logging.getLogger(__name__)


@contextmanager
def open_mailbox() -> Generator[MailBox, None, None]:
    with MailBox(settings.imap_host, settings.imap_port).login(
        settings.imap_user, settings.imap_password, settings.imap_mailbox
    ) as mb:
        yield mb


def fetch_unseen(mb: MailBox) -> list[MailMessage]:
    """Return all unread messages without marking them as seen."""
    return list(mb.fetch(AND(seen=False), mark_seen=False))


def mark_seen(mb: MailBox, msg: MailMessage) -> None:
    mb.seen([msg.uid], True)
