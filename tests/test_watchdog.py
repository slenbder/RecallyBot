from __future__ import annotations

import os

# Provide stub values so pydantic Settings doesn't raise on import.
for _k, _v in {
    "IMAP_HOST": "test.example.com",
    "IMAP_USER": "test",
    "IMAP_PASSWORD": "test",
    "TELEGRAM_BOT_TOKEN": "stub_token",
    "TELEGRAM_CHAT_ID": "-100111",
}.items():
    os.environ.setdefault(_k, _v)

from bot.main import watchdog_should_exit  # noqa: E402


def test_stale_progress_triggers_exit() -> None:
    last_progress = 0.0
    now = 400.0
    timeout = 300.0
    assert watchdog_should_exit(last_progress, now, timeout) is True


def test_fresh_progress_does_not_trigger_exit() -> None:
    last_progress = 100.0
    now = 200.0
    timeout = 300.0
    assert watchdog_should_exit(last_progress, now, timeout) is False


def test_exactly_at_boundary_does_not_trigger_exit() -> None:
    last_progress = 0.0
    now = 300.0
    timeout = 300.0
    assert watchdog_should_exit(last_progress, now, timeout) is False
