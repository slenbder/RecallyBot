from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Provide stub values so pydantic Settings doesn't raise on import.
# Use setdefault so a real .env doesn't get clobbered when tests run locally.
for _k, _v in {
    "IMAP_HOST": "test.example.com",
    "IMAP_USER": "test",
    "IMAP_PASSWORD": "test",
    "TELEGRAM_BOT_TOKEN": "stub_token",
    "TELEGRAM_CHAT_ID": "-100111",
}.items():
    os.environ.setdefault(_k, _v)

import bot.notifier as notifier  # noqa: E402  (must follow env setup above)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(status: int, body: dict) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.is_success = 200 <= status < 300
    r.json.return_value = body
    r.text = str(body)
    if not r.is_success:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=r
        )
    return r


class _FakeSettings:
    telegram_bot_token = "stub_token"
    telegram_chat_id = "-100111"
    display_timezone = "UTC"


@pytest.fixture(autouse=True)
def _reset_override():
    """Isolate _chat_id_override between tests."""
    notifier._chat_id_override = None
    yield
    notifier._chat_id_override = None


# ---------------------------------------------------------------------------
# Supergroup migration
# ---------------------------------------------------------------------------

def test_migration_retries_against_new_chat_id_and_succeeds():
    old_id = "-100111"
    new_id = -100222  # Telegram returns an integer in parameters

    migration_400 = _resp(400, {"parameters": {"migrate_to_chat_id": new_id}})
    success_200 = _resp(200, {"ok": True})

    with patch("bot.notifier.settings", _FakeSettings()), \
         patch("httpx.post", side_effect=[migration_400, success_200]) as mock_post:

        notifier.send_text("hello")  # must not raise

    assert mock_post.call_count == 2
    first_chat_id = mock_post.call_args_list[0].kwargs["json"]["chat_id"]
    second_chat_id = mock_post.call_args_list[1].kwargs["json"]["chat_id"]
    assert first_chat_id == old_id
    assert second_chat_id == str(new_id)
    assert notifier._chat_id_override == str(new_id)


def test_migration_override_persists_for_subsequent_sends():
    """Once migrated, the next independent send() uses the new id without a 400."""
    new_id = -100333

    migration_400 = _resp(400, {"parameters": {"migrate_to_chat_id": new_id}})
    success_200 = _resp(200, {"ok": True})
    second_send_200 = _resp(200, {"ok": True})

    with patch("bot.notifier.settings", _FakeSettings()), \
         patch("httpx.post", side_effect=[migration_400, success_200, second_send_200]) as mock_post:

        notifier.send_text("first")
        notifier.send_text("second")

    assert mock_post.call_count == 3
    assert mock_post.call_args_list[2].kwargs["json"]["chat_id"] == str(new_id)


def test_non_migration_400_raises():
    """A plain 400 (not a migration error) must still raise."""
    plain_400 = _resp(400, {"description": "Bad Request: chat not found"})

    with patch("bot.notifier.settings", _FakeSettings()), \
         patch("httpx.post", return_value=plain_400):

        with pytest.raises(httpx.HTTPStatusError):
            notifier.send_text("hello")


def test_migration_body_missing_parameters_raises():
    """A 400 with no migrate_to_chat_id in parameters must still raise."""
    weird_400 = _resp(400, {"parameters": {}})

    with patch("bot.notifier.settings", _FakeSettings()), \
         patch("httpx.post", return_value=weird_400):

        with pytest.raises(httpx.HTTPStatusError):
            notifier.send_text("hello")
