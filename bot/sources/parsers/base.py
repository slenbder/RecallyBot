from __future__ import annotations

from typing import Protocol

from imap_tools import MailMessage

from ...models import Review


class Parser(Protocol):
    source: str

    def is_review(self, msg: MailMessage) -> bool:
        ...

    def parse(self, msg: MailMessage) -> list[Review]:
        ...
