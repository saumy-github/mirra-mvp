"""All env configuration in one place (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
# /app in the Docker image, which is where compose mounts the upload roots.
REPO_ROOT = BACKEND_DIR.parent.parent


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

    # Mirrors the frontend's VITE_APP_ENV. Read directly by the worker
    # process (os.environ, via worker/.env — see worker/live_upload.py) to
    # pick dev_upload/ vs live_upload/, and here by avatars_upload_root below.
    app_env: Literal["development", "production"] = "development"

    # Redis/RQ hand-off to the native CLO worker (worker/, repo root) — see
    # .agent/website-launch/07-step0-worker-queue.md. Native/local default;
    # the Dockerized backend overrides this to redis://redis:6379/0 via
    # website/backend/.env.docker.dev (compose service name, not localhost).
    redis_url: str = "redis://localhost:6379/0"

    # Google OAuth (03-backend-behavior-plan.md, "Google OAuth plan"). Empty
    # client id/secret means Google sign-in is treated as unconfigured.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_auth_success_url: str = "http://localhost:3000/auth/callback"
    frontend_auth_failure_url: str = "http://localhost:3000/auth/login"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def avatars_upload_root(self) -> Path:
        """Excludes the trailing "avatars" segment — avatar_glb_path already supplies it."""
        root_name = "live_upload" if self.app_env == "production" else "dev_upload"
        return REPO_ROOT / root_name


@lru_cache
def get_settings() -> Settings:
    return Settings()
