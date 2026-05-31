"""Server settings, loaded from .env via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # CORS for the Next.js dev server (frontend reaches the API via same-origin
    # rewrites in prod, but allow direct :3000 calls in dev).
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Sponsor keys (read from the same .env the bot uses).
    gradium_api_key: str | None = None
    cekura_api_key: str | None = None

    # WebRTC ICE. STUN is enough for localhost; TURN needed for remote peers.
    stun_url: str = "stun:stun.l.google.com:19302"
    turn_url: str | None = None
    turn_username: str | None = None
    turn_credential: str | None = None

    host: str = "0.0.0.0"
    port: int = 8000


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
