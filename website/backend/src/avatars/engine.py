"""The CLO3D hand-off seam.

Every avatar job is handed to the native CLO worker (worker/run_worker.py,
repo root) via Redis/RQ — see .agent/website-launch/07-step0-worker-queue.md.
The worker drives clo_avatar_generation/avatar_runtime directly; this
process never imports that pipeline code.
"""

from ..core.queue import enqueue
from .models import AvatarJobDocument

AVATAR_JOB_TIMEOUT_SECONDS = 20 * 60  # generous margin over a normal run; see worker/README.md


def start_job(job: AvatarJobDocument) -> None:
    """Called at job creation — hands the job to the CLO worker queue
    (worker.tasks.run_avatar_job)."""
    enqueue("worker.tasks.run_avatar_job", job.id, job_timeout=AVATAR_JOB_TIMEOUT_SECONDS)
