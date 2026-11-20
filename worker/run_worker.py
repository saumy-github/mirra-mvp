"""Native CLO worker entrypoint.

Run this on the Windows machine that has CLO3D + the REST plugin running
(localhost:50505) — NOT inside Docker. See worker/README.md for setup and
.agent/website-launch/07-step0-worker-queue.md for the design.

Usage (from the repo root, inside the repo .venv):
    python worker/run_worker.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "website" / "backend"
for _p in (REPO_ROOT, BACKEND_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv  # noqa: E402

# Populates the process environment from worker/.env (gitignored; see
# worker/.env.example). REDIS_URL is read straight out of os.environ below
# rather than through the backend's Settings: that class validates every
# field it declares, so importing it here would make the worker depend on
# backend-only config (token secrets, OAuth, SMTP) it never uses.
load_dotenv(Path(__file__).resolve().parent / ".env")

from redis import Redis  # noqa: E402
from rq import Queue  # noqa: E402
from rq.worker import SimpleWorker  # noqa: E402

# QUEUE_NAME only — importing this module does not construct Settings
# (src/core/queue.py calls get_settings() inside functions, not at import),
# and sharing the constant keeps the queue name from drifting.
from src.core.queue import QUEUE_NAME  # noqa: E402

from worker.slots import claim_session, clo_base_url, slot_name, wait_for_session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mirra.worker")


def main() -> int:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.error(
            "REDIS_URL is not set. Add it to worker/.env (see worker/.env.example) "
            "or export it before starting the worker."
        )
        return 2

    conn = Redis.from_url(redis_url)
    queue = Queue(QUEUE_NAME, connection=conn)

    # One worker process owns one CLO session (CLO_BASE_URL). Parallelism comes
    # from running several of these, each against its own session — see
    # worker/run_workers.py. The lock stops a second worker from sharing a
    # session, which would race and corrupt whichever job's scene loses.
    base_url = clo_base_url()
    name = slot_name()
    try:
        _session_lock = claim_session(base_url)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 3
    ready_timeout = float(os.environ.get("CLO_READY_TIMEOUT", "300"))
    try:
        wait_for_session(base_url, timeout=ready_timeout)
    except TimeoutError as exc:
        logger.error("%s", exc)
        return 4

    logger.info(
        "Starting CLO worker %s: redis=%s queue=%r clo=%s (SimpleWorker, one job at a time "
        "on this CLO session — required on Windows, see worker/README.md)",
        name,
        redis_url,
        QUEUE_NAME,
        base_url,
    )
    # SimpleWorker: runs jobs in this same process/thread, no os.fork() —
    # the default rq.Worker forks a work-horse process per job, which
    # doesn't exist on Windows. Jobs inside one worker are serial because its
    # CLO session is single-threaded; more throughput = more sessions + workers.
    worker = SimpleWorker([queue], connection=conn, name=name)
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
