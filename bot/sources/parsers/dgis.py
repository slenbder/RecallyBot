from __future__ import annotations

from imap_tools import MailMessage

from ...models import Review


class DgisParser:
    source = "dgis"

    def parse(self, msg: MailMessage) -> Review | None:
        # TODO: implement once real .eml fixtures are available
        return None
