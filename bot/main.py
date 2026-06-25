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

    if parser is not None and not parser.is_review(msg):
        # Known platform but not a review notification — ignore silently.
        log.info("Known platform %s, not a review (uid=%s) — ignoring", parser.source, msg.uid)
        mark_seen(mb, msg)
        return

    def _raw_fallback() -> None:
        raw_key = "raw|" + (msg.headers.get("message-id", [msg.uid])[0])
        if storage.is_new_key(raw_key):
            send_raw(hint, msg.subject or "(no subject)")
        else:
            log.info("Duplicate raw fallback skipped (uid=%s)", msg.uid)

    if parser is None:
        # Unknown sender in the folder — raw fallback (rare).
        # Dedup by Message-ID so a crash between send and mark_seen never double-sends.
        _raw_fallback()
    else:
        reviews = []
        try:
            reviews = parser.parse(msg)
        except Exception:
            log.exception("Parser %s raised for uid=%s", parser.source, msg.uid)

        if not reviews:
            # Looked like a review but parse returned nothing — raw fallback.
            _raw_fallback()
        else:
            # Send each new review; if any send raises, abort without marking seen
            # so the whole email is retried. Already-sent reviews dedup out next pass.
            for review in reviews:
                if storage.is_new(review):
                    send_review(review)
                else:
                    log.info("Duplicate review skipped (uid=%s)", msg.uid)

    # Mark seen ONLY after the whole list is processed without exception (invariant #1)
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
