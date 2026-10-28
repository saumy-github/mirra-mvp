"""The photo-measurement hand-off seam: enqueue by string path onto the `measure`
queue (worker/run_worker.py --queues measure). This process never imports
photo_measurement/ — the API image has no torch or MediaPipe."""

from ..core.queue import MEASURE_QUEUE_NAME, enqueue

PHOTO_JOB_TIMEOUT_SECONDS = 5 * 60  # a run is seconds; the margin covers a cold model load


def start_capture(capture_id: str) -> None:
    enqueue(
        "worker.tasks.run_photo_measurement",
        capture_id,
        job_timeout=PHOTO_JOB_TIMEOUT_SECONDS,
        queue=MEASURE_QUEUE_NAME,
    )
