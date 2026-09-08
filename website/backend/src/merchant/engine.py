"""Hand-off seam to the native CLO worker for merchant-side jobs.

Same Redis/RQ queue as avatars and try-on renders (`clo`), because the CLO
plugin is single-threaded and one queue is what serialises against it — see
worker/README.md on why concurrency is 1.

Jobs are enqueued by string path and never imported: the backend image does
not have `product_ingestion`/`clo_vto` installed (website/backend/Dockerfile
copies only website/backend), so a direct import would break the image. RQ
resolves the path inside the worker process, which does have them.
"""

from ..core.queue import enqueue

# Step 2 runs SAM 2 / U^2-Net segmentation and then the CLO block draft. On a
# cold model load the first run is minutes, not seconds.
INGESTION_JOB_TIMEOUT_SECONDS = 30 * 60

# A preview is a full CLO simulation: import, arrange, sew, simulate, export.
# Matched to the try-on render timeout, which is sized from real runs.
PREVIEW_JOB_TIMEOUT_SECONDS = 25 * 60


def start_ingestion(run_id: str) -> None:
    """Run Step 2 for one (cloth, size) pair."""
    enqueue(
        "worker.tasks.run_merchant_ingestion",
        run_id,
        job_timeout=INGESTION_JOB_TIMEOUT_SECONDS,
    )


def start_preview(preview_id: str) -> None:
    """Run Step 3 against the reference avatar, for QA and merchant preview."""
    enqueue(
        "worker.tasks.run_merchant_preview",
        preview_id,
        job_timeout=PREVIEW_JOB_TIMEOUT_SECONDS,
    )
