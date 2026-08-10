"""Redis/RQ hand-off to the native CLO worker (worker/, repo root).

The backend only ever enqueues jobs by string path ("worker.tasks.run_...")
— it never imports worker.tasks directly. worker/'s CLO pipeline
dependencies (clo_avatar_generation, clo_vto) aren't installed in this
container (see website/backend/Dockerfile — only website/backend is
COPYed in), so a direct import would break the image. RQ resolves the
string in the worker process instead, which does have those deps.

See .agent/website-launch/07-step0-worker-queue.md.
"""

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue

from ..config import get_settings
from .errors import ServiceUnavailable

QUEUE_NAME = "clo"

_redis: Redis | None = None
_queue: Queue | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url)
    return _redis


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        _queue = Queue(QUEUE_NAME, connection=_get_redis())
    return _queue


def enqueue(func_path: str, *args, job_timeout: int) -> None:
    """Hand a job off to the worker. Raises ServiceUnavailable (not a raw
    redis exception) if Redis itself is unreachable, so callers get the same
    error contract as the old "engine not wired yet" refusal.

    job_timeout is required, not defaulted: a stuck/unresponsive CLO
    instance needs to fail the job instead of leaving it in
    processing/rendering forever (07-step0-worker-queue.md item 6) — RQ's
    default 180s is too short for a real CLO run, so every call site must
    pick a deliberate value rather than silently inheriting that default.
    """
    try:
        get_queue().enqueue(func_path, *args, job_timeout=job_timeout)
    except RedisError as exc:
        raise ServiceUnavailable(
            "Live engine queue is unreachable (Redis down?)", code="engine_unavailable"
        ) from exc
