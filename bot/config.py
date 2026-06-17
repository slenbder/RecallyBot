from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # IMAP
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: str
    imap_mailbox: str = "INBOX"

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Behaviour
    poll_fallback_seconds: int = 60
    silence_alert_hours: int = 168

    # Display
    display_timezone: str = "Europe/Moscow"

    # Internal
    db_path: str = "reviews.db"


settings = Settings()  # type: ignore[call-arg]
