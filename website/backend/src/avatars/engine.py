"""The CLO3D hand-off seam (AVATAR_ENGINE_MODE=demo|live).

demo: no real work — the job's state is derived from elapsed time on read
(queued → processing → ready), so the frontend can integrate against real
endpoints before the worker/queue exists.

live: will hand the job to the clo_avatar_generation/avatar_runtime pipeline
via the (not-yet-decided) worker queue — backend-implementation-plan.md,
Phase 0 item 3. Until then it refuses cleanly instead of pretending.
"""

from datetime import datetime, timezone

from ..config import get_settings
from ..core.errors import ServiceUnavailable
from .models import DEMO_PROCESSING_SECONDS, DEMO_QUEUE_SECONDS


def engine_mode() -> str:
    return get_settings().avatar_engine_mode


def start_job(job: dict) -> None:
    """Called at job creation. Demo mode needs nothing; live mode is the
    future enqueue-to-CLO3D-worker call."""
    if engine_mode() == "live":
        raise ServiceUnavailable(
            "Live avatar engine is not wired yet (CLO3D worker queue pending)",
            code="engine_unavailable",
        )


def derive_demo_state(job: dict) -> str:
    """Time-staged progression for demo jobs."""
    elapsed = (datetime.now(timezone.utc) - job["created_at"]).total_seconds()
    if elapsed < DEMO_QUEUE_SECONDS:
        return "queued"
    if elapsed < DEMO_QUEUE_SECONDS + DEMO_PROCESSING_SECONDS:
        return "processing"
    return "ready"
