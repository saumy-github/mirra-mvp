"""All env configuration in one place (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "mirratest"

    # ≥32 bytes so HS256 HMAC meets RFC 7518's minimum key length even in dev
    access_token_secret: str = "dev-only-secret-change-me-before-going-live-0000"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cookie_secure: bool = False

    # The frontend dev server runs on 3000 (vite --port=3000, package.json)
    cors_origins: str = "http://localhost:3000"

    avatar_engine_mode: str = "demo"  # demo | live
    tryon_engine_mode: str = "demo"  # demo | live

    uploads_dir: str = "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def uploads_path(self) -> Path:
        p = Path(self.uploads_dir)
        return p if p.is_absolute() else BACKEND_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
