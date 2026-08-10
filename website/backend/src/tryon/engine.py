"""The cloth-physics hand-off seam.

Every try-on render is handed to the native CLO worker (worker/run_worker.py,
repo root) via Redis/RQ — same queue as avatars, see
.agent/website-launch/07-step0-worker-queue.md.
"""

from ..core.queue import enqueue
from .models import TryonRenderDocument

TRYON_JOB_TIMEOUT_SECONDS = 25 * 60  # simulation can run longer than avatar generation; see worker/README.md


def start_render(render: TryonRenderDocument) -> None:
    enqueue("worker.tasks.run_tryon_render", render.id, job_timeout=TRYON_JOB_TIMEOUT_SECONDS)
