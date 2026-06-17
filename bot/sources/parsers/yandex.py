from __future__ import annotations

from imap_tools import MailMessage

from ...models import Review


class YandexParser:
    source = "yandex"

    def is_review(self, msg: MailMessage) -> bool:
        return False

    def parse(self, msg: MailMessage) -> Review | None:
        # TODO: implement once real .eml fixtures are available
        return None
