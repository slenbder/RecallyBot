from __future__ import annotations

import html
import logging

import httpx

from .config import settings
from .models import Review

log = logging.getLogger(__name__)

_SOURCE_NAMES: dict[str, str] = {
    "yandex": "Яндекс Карты",
    "dgis": "2ГИС",
    "google": "Google Maps",
}

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def _stars(rating: int | None) -> str:
    if rating is None:
        return ""
    filled = "★" * rating
    empty = "☆" * (5 - rating)
    return f"{filled}{empty}  "


def _escape(text: str) -> str:
    return html.escape(text)


def send_review(review: Review) -> None:
    source_name = _SOURCE_NAMES.get(review.source, _escape(review.source))
    stars = _stars(review.rating)
    lines = [
        f"<b>{source_name}</b>  {stars}",
        f"<b>Автор:</b> {_escape(review.author)}",
        f"<b>Дата:</b> {_escape(review.date)}",
        "",
        _escape(review.text),
    ]
    if review.url:
        lines.append(f'\n<a href="{_escape(review.url)}">Открыть отзыв</a>')

    send_text("\n".join(lines))


def send_raw(source_hint: str, subject: str) -> None:
    text = (
        f"⚠️ <b>Новый отзыв (не распознан)</b>\n"
        f"<b>Источник:</b> {_escape(source_hint)}\n"
        f"<b>Тема письма:</b> {_escape(subject)}"
    )
    send_text(text)


def send_text(msg: str) -> None:
    url = _API_BASE.format(token=settings.telegram_bot_token)
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = httpx.post(url, json=payload, timeout=15)
    if not resp.is_success:
        log.error("Telegram send failed: %s %s", resp.status_code, resp.text)
    resp.raise_for_status()
