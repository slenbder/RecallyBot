# Review Bot

Pushes new restaurant reviews from Яндекс Карты, 2ГИС, and Google Maps to a
Telegram group in real time. The review platforms send email notifications to a
service mailbox; the bot polls that mailbox over IMAP and forwards each new
review to Telegram.

## Status

**Parsers are stubs.** All three parsers (`yandex`, `dgis`, `google`) return
`None` until real `.eml` notification samples are provided. In the meantime the
bot falls back to a "raw" Telegram message showing the email subject and source
hint — the owner still hears about every review.

Add `.eml` samples to `tests/fixtures/` and implement the corresponding parser
once you have real emails to work from.

---

## Requirements

- Python 3.12+
- A service mailbox that receives forwarded review notifications
- A Telegram bot token and a group/channel chat ID

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env with your credentials
```

## Running locally

```bash
python -m bot.main
```

The bot will:
1. Send "✅ Бот запущен" to the Telegram chat.
2. Process all currently unread mail (catch-up pass).
3. Enter an IMAP IDLE loop, falling back to a poll every
   `POLL_FALLBACK_SECONDS` seconds (default 60).

## Running tests

```bash
pytest
```

Tests skip gracefully when no `.eml` fixtures are present.

---

## Systemd deployment

```bash
# 1. Create a dedicated user
sudo useradd -r -s /usr/sbin/nologin reviewbot

# 2. Deploy the project
sudo mkdir -p /opt/review-bot
sudo cp -r . /opt/review-bot
sudo cp .env /opt/review-bot/.env
sudo chown -R reviewbot:reviewbot /opt/review-bot

# 3. Install and start the service
sudo cp deploy/review-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now review-bot

# 4. View logs
sudo journalctl -u review-bot -f
```

The service file sets `Restart=always` and `RestartSec=10`, so the bot
recovers automatically after crashes or network interruptions.

---

## Architecture notes

| Invariant | Implementation |
|---|---|
| Exactly-once output | `\Seen` flag set **after** successful Telegram send; SQLite dedup prevents duplicate sends on retry |
| No silent loss | Unmatched / unparseable emails → `send_raw()` fallback |
| Dedup key | SHA-256 of `source + author(lower) + date + text[:100]` |
| Real-time | IMAP IDLE + polling fallback |
| Catch-up | All unread mail processed on startup before IDLE |
| Silence alert | Heartbeat table; alert after `SILENCE_ALERT_HOURS` (default 168 h) without mail |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `IMAP_HOST` | — | IMAP server hostname |
| `IMAP_PORT` | `993` | IMAP port (TLS) |
| `IMAP_USER` | — | Mailbox username |
| `IMAP_PASSWORD` | — | Mailbox password / app password |
| `IMAP_MAILBOX` | `INBOX` | Folder to watch |
| `TELEGRAM_BOT_TOKEN` | — | Bot API token |
| `TELEGRAM_CHAT_ID` | — | Target chat / group ID |
| `POLL_FALLBACK_SECONDS` | `60` | IDLE fallback poll interval |
| `SILENCE_ALERT_HOURS` | `168` | Hours of silence before alert |
| `DB_PATH` | `reviews.db` | SQLite database file path |
