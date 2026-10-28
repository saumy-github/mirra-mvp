"""Hand-off seam: enqueue by string path onto the `measure` queue (the same
worker as photo measurement — MediaPipe, no CLO)."""

from ..core.queue import MEASURE_QUEUE_NAME, enqueue

FACE_JOB_TIMEOUT_SECONDS = 5 * 60


def start_capture(capture_id: str) -> None:
    enqueue(
        "worker.tasks.run_face_reconstruction",
        capture_id,
        job_timeout=FACE_JOB_TIMEOUT_SECONDS,
        queue=MEASURE_QUEUE_NAME,
    )
