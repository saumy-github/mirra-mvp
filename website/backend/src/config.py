"""All env configuration in one place (pydantic-settings).

Values come from the process environment only. The backend runs in Docker,
where compose injects them from website/backend/.env.docker.dev (see
docker-compose.yml). There is deliberately no env_file fallback: the old
`BACKEND_DIR / ".env"` never existed in the image, so it silently did
nothing while making it look as though a local file were being read.

Fields below split into two groups:

  * No default -> REQUIRED. Missing means Settings() raises at startup.
    These are the ones where quietly falling back to a dev value is a
    security or data-integrity bug (wrong database, a known token secret,
    cookies without Secure).
  * With a default -> genuinely optional, where the default is a real,
    intended state rather than a placeholder. An empty SMTP host means
    "email not configured" and an empty Google client id means "Google
    sign-in not configured"; both are supported ways to run.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
# /app in the Docker image, which is where compose mounts the upload roots.
REPO_ROOT = BACKEND_DIR.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str
    database_name: str

    # min_length=32 so HS256 HMAC meets RFC 7518's minimum key length. This
    # used to carry a committed dev default, which meant a missing env var
    # booted a working-looking backend signing tokens with a public secret.
    access_token_secret: str = Field(min_length=32)
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    cookie_secure: bool

    # Comma-separated. The frontend dev server runs on 3000
    # (vite --port=3000, package.json).
    cors_origins: str

    # Mirrors the frontend's VITE_APP_ENV. Read directly by the worker
    # process (os.environ, via worker/.env — see worker/live_upload.py) to
    # pick dev_upload/ vs live_upload/, and here by avatars_upload_root below.
    app_env: Literal["development", "production"] = "development"

    # Redis/RQ hand-off to the native CLO worker (worker/, repo root) — see
    # .agent/website-launch/07-step0-worker-queue.md. In Docker this is
    # redis://redis:6379/0 (compose service name, not localhost) via
    # website/backend/.env.docker.dev. The worker reads its own REDIS_URL
    # straight from worker/.env and does not use this class.
    redis_url: str

    # Google OAuth (03-backend-behavior-plan.md, "Google OAuth plan"). Empty
    # client id/secret means Google sign-in is treated as unconfigured.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_auth_success_url: str = "http://localhost:3000/auth/callback"
    frontend_auth_failure_url: str = "http://localhost:3000/auth/login"

    # Optional transactional email for early-access confirmations. The form
    # still persists applications when SMTP is intentionally not configured.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Mirra"
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    join_notification_email: str = ""

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
