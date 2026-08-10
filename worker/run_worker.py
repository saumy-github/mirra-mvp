"""Native CLO worker entrypoint.

Run this on the Windows machine that has CLO3D + the REST plugin running
(localhost:50505) — NOT inside Docker. See worker/README.md for setup and
.agent/website-launch/07-step0-worker-queue.md for the design.

Usage (from the repo root, inside the repo .venv):
    python worker/run_worker.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "website" / "backend"
for _p in (REPO_ROOT, BACKEND_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv  # noqa: E402

# Must run before `from src.config import get_settings` below — Settings()
# reads MONGODB_URI/REDIS_URL from the process environment, which this
# populates from worker/.env (gitignored; see worker/.env.example).
load_dotenv(Path(__file__).resolve().parent / ".env")

from redis import Redis  # noqa: E402
from rq import Queue  # noqa: E402
from rq.worker import SimpleWorker  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.core.queue import QUEUE_NAME  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mirra.worker")


def main() -> int:
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    queue = Queue(QUEUE_NAME, connection=conn)

    logger.info(
        "Starting CLO worker: redis=%s queue=%r (SimpleWorker, concurrency=1 — "
        "required on Windows, see worker/README.md)",
        settings.redis_url,
        QUEUE_NAME,
    )
    # SimpleWorker: runs jobs in this same process/thread, no os.fork() —
    # the default rq.Worker forks a work-horse process per job, which
    # doesn't exist on Windows. This is also correct for us independent of
    # platform: CLO3D's plugin is itself single-threaded, so there's no
    # parallelism to gain from a forking worker anyway.
    worker = SimpleWorker([queue], connection=conn)
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
