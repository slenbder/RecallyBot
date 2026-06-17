from __future__ import annotations

import html
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from .config import settings
from .models import Review

log = logging.getLogger(__name__)

_SOURCE_NAMES: dict[str, str] = {
    "yandex": "Яндекс Карты",
    "dgis": "2ГИС",
    "google": "Google Maps",
}

_MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def _escape(text: str) -> str:
    return html.escape(text)


def _polarity(rating: int | None) -> str:
    if rating is None:
        return "◽"
    if rating >= 4:
        return "🟢"
    if rating == 3:
        return "🟡"
    return "🔴"


def _stars(rating: int | None) -> str:
    if rating is None:
        return ""
    return "★" * rating + "☆" * (5 - rating)


def _human_date(date_str: str) -> str | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        local = dt.astimezone(ZoneInfo(settings.display_timezone))
        return f"{local.day} {_MONTHS[local.month - 1]} {local.year}, {local.strftime('%H:%M')}"
    except Exception:
        log.warning("Could not format date %r", date_str)
        return None


def send_review(review: Review) -> None:
    source_name = _SOURCE_NAMES.get(review.source, _escape(review.source))
    polarity = _polarity(review.rating)

    if review.rating is None:
        line1 = f"{polarity} <b>{source_name}</b>  оценка не распознана"
    else:
        line1 = f"{polarity} <b>{source_name}</b>  {_stars(review.rating)}"

    parts = [line1]

    if review.author:
        parts.append(f"👤 <b>{_escape(review.author)}</b>")

    hdate = _human_date(review.date)
    if hdate:
        parts.append(f"🕐 {hdate}")

    if review.text:
        parts.append("")
        parts.append(f"«{_escape(review.text)}»")

    if review.url:
        parts.append("")
        parts.append(f'🔗 <a href="{_escape(review.url)}">Открыть отзыв</a>')

    send_text("\n".join(parts))


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
