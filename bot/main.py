from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta

from imap_tools import MailBox

from .config import settings
from .storage import Storage
from .notifier import send_review, send_raw, send_text
from .sources.imap_client import open_mailbox, fetch_unseen, mark_seen
from .sources.router import resolve, source_hint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


def process_message(mb: MailBox, msg, storage: Storage) -> None:
    """Parse one message and forward to Telegram; mark seen only on success."""
    hint = source_hint(msg)
    parser = resolve(msg)

    review = None
    if parser is not None:
        try:
            review = parser.parse(msg)
        except Exception:
            log.exception("Parser %s raised for uid=%s", parser.source, msg.uid)

    if review is not None:
        if storage.is_new(review):
            send_review(review)
        else:
            log.info("Duplicate review skipped (uid=%s)", msg.uid)
    else:
        # No parser matched or parser returned None — raw fallback (invariant #2).
        # Dedup by Message-ID so a crash between send and mark_seen never double-sends.
        raw_key = "raw|" + (msg.headers.get("message-id", [msg.uid])[0])
        if storage.is_new_key(raw_key):
            send_raw(hint, msg.subject or "(no subject)")
        else:
            log.info("Duplicate raw fallback skipped (uid=%s)", msg.uid)

    # Mark seen ONLY after a successful Telegram send (invariant #1)
    mark_seen(mb, msg)


def check_silence(storage: Storage) -> None:
    last = storage.last_poll_at()
    if last is None:
        return
    silence = datetime.now(timezone.utc) - last
    threshold = timedelta(hours=settings.silence_alert_hours)
    if silence >= threshold:
        hours = int(silence.total_seconds() // 3600)
        send_text(
            f"ℹ️ Бот активен, но писем с отзывами не было уже {hours} ч. "
            f"(порог: {settings.silence_alert_hours} ч.)"
        )


def run_once(storage: Storage) -> None:
    """Fetch all unread mail, process each, update heartbeat."""
    with open_mailbox() as mb:
        messages = fetch_unseen(mb)
        log.info("Fetched %d unread message(s)", len(messages))
        for msg in messages:
            try:
                process_message(mb, msg, storage)
            except Exception:
                log.exception("Failed to process uid=%s, will retry", msg.uid)
    storage.record_heartbeat()
    check_silence(storage)


def main() -> None:
    storage = Storage(settings.db_path)
    send_text("✅ Бот запущен")

    # Invariant #5: catch-up pass before entering IDLE
    log.info("Catch-up: processing unread mail on startup")
    run_once(storage)

    log.info("Entering IDLE loop (fallback every %ds)", settings.poll_fallback_seconds)
    while True:
        try:
            with open_mailbox() as mb:
                # IMAP IDLE — blocks until server pushes an EXISTS notification
                # or the fallback timeout fires, whichever comes first.
                responses = mb.idle.wait(timeout=settings.poll_fallback_seconds)
                if responses:
                    log.info("IDLE: server notified new mail")
            run_once(storage)
        except Exception:
            log.exception("Error in main loop, backing off 10s")
            time.sleep(10)


if __name__ == "__main__":
    main()
