"""RQ tasks for the merchant pipeline: Capture → Product Ingestion → VTO.

Enqueued by string path from website/backend/src/merchant/engine.py, never
imported by the backend — its Docker image has neither `product_ingestion`
nor `clo_vto` installed. Imported here into worker/tasks.py so a single
module path (`worker.tasks.run_merchant_*`) stays the enqueue contract.

Two jobs:

    run_merchant_ingestion(run_id)   Step 2. Reads the staged input folder the
                                     backend wrote, runs the canonical runner
                                     for one (cloth, size), records where the
                                     panels landed.

    run_merchant_preview(preview_id) Step 3. Drapes those panels on Mirra's
                                     **reference avatar** — not a shopper's —
                                     and stores the GLB for QA to look at.

Why a reference avatar
----------------------
QA is approving the garment, not a fit on one particular body. Rendering
every preview against the same neutral avatar means two reviewers comparing
revisions are looking at the same variable changing. It also means a preview
can be produced before any shopper has generated an avatar at all.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "website" / "backend"
for _p in (REPO_ROOT, BACKEND_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from clo_vto.native_vto.pipeline import run_pipeline as run_vto_pipeline  # noqa: E402
from src.db import (  # noqa: E402
    merchant_garments_col,
    merchant_ingestion_runs_col,
    merchant_previews_col,
)
from src.merchant.models import (  # noqa: E402
    IngestionRunDocument,
    MerchantGarmentDocument,
    PreviewDocument,
)

from product_ingestion.run_manifest import get_latest_product_run_dir  # noqa: E402

logger = logging.getLogger("mirra.worker.merchant")

# The neutral body every merchant preview is rendered against. Overridable so
# a deployment can ship its own reference avatar without a code change.
REFERENCE_AVATAR = Path(
    os.environ.get(
        "MIRRA_REFERENCE_AVATAR",
        str(REPO_ROOT / "clo_avatar_generation" / "input" / "base-1.avt"),
    )
)

VTO_OUTPUT_DIR = REPO_ROOT / "clo_vto" / "output"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ Step 2


async def _run_ingestion(run_id: str) -> None:
    raw = await merchant_ingestion_runs_col().find_one({"_id": run_id})
    if not raw:
        logger.error("run_merchant_ingestion: run %s not found", run_id)
        return
    run = IngestionRunDocument.model_validate(raw)

    await merchant_ingestion_runs_col().update_one(
        {"_id": run_id}, {"$set": {"state": "running"}}
    )
    await _set_pipeline_state(run.garment_id, "ingesting")

    # Imported here rather than at module scope: the runner pulls in torch and
    # the segmentation models, which is a slow import to pay on worker boot
    # for a process that may only ever run avatar jobs.
    from product_ingestion.run_product_ingestion import build_parser, run_product_ingestion

    args = build_parser().parse_args(
        ["--cloth-id", run.cloth_id, "--size-id", run.size_id]
    )

    try:
        logger.info(
            "run_merchant_ingestion %s: Step 2 for cloth=%s size=%s",
            run_id, run.cloth_id, run.size_id,
        )
        code = run_product_ingestion(args)
    except Exception as exc:
        logger.exception("run_merchant_ingestion %s: unhandled error", run_id)
        await _fail_ingestion(run, str(exc))
        return

    if code != 0:
        await _fail_ingestion(run, f"product_ingestion exited with code {code}")
        return

    try:
        run_dir = get_latest_product_run_dir(cloth_id=run.cloth_id, size_id=run.size_id)
    except FileNotFoundError as exc:
        await _fail_ingestion(run, f"Ingestion reported success but wrote no run directory: {exc}")
        return

    dxf_dir = run_dir / "panels" / "dxf"
    panels = sorted(dxf_dir.glob("*.dxf")) if dxf_dir.is_dir() else []
    if len(panels) < 4:
        await _fail_ingestion(
            run,
            f"Ingestion produced {len(panels)} DXF panel(s) in {dxf_dir}; the VTO step needs 4.",
        )
        return

    product_run_id = f"{run.cloth_id}-{run.size_id}-{run_dir.name}"
    await merchant_ingestion_runs_col().update_one(
        {"_id": run_id},
        {
            "$set": {
                "state": "succeeded",
                "product_run_id": product_run_id,
                "run_dir": str(run_dir),
                "panel_count": len(panels),
                "completed_at": _now(),
                "failure_reason": "",
            }
        },
    )

    # Record the completed run on the garment, and only mark the whole garment
    # ingested once every queued size has landed.
    await merchant_garments_col().update_one(
        {"_id": run.garment_id},
        {"$set": {f"pipeline.ingested_runs.{run.size_id}": product_run_id}},
    )
    await _advance_if_all_ingested(run.garment_id)
    logger.info("run_merchant_ingestion %s: succeeded (%s)", run_id, product_run_id)


async def _fail_ingestion(run: IngestionRunDocument, reason: str) -> None:
    await merchant_ingestion_runs_col().update_one(
        {"_id": run.id},
        {"$set": {"state": "failed", "failure_reason": reason, "completed_at": _now()}},
    )
    await merchant_garments_col().update_one(
        {"_id": run.garment_id},
        {
            "$set": {
                "pipeline.state": "failed",
                "pipeline.failure_reason": f"{run.size_id}: {reason}",
                "pipeline.updated_at": _now(),
            }
        },
    )
    logger.error("run_merchant_ingestion %s failed: %s", run.id, reason)


async def _set_pipeline_state(garment_id: str, state: str) -> None:
    await merchant_garments_col().update_one(
        {"_id": garment_id},
        {"$set": {"pipeline.state": state, "pipeline.updated_at": _now()}},
    )


async def _advance_if_all_ingested(garment_id: str) -> None:
    raw = await merchant_garments_col().find_one({"_id": garment_id})
    if not raw:
        return
    garment = MerchantGarmentDocument.model_validate(raw)
    expected = set(garment.pipeline.size_ids)
    done = set(garment.pipeline.ingested_runs)
    if expected and expected.issubset(done):
        await _set_pipeline_state(garment_id, "ingested")


# ------------------------------------------------------------------ Step 3


async def _run_preview(preview_id: str) -> None:
    raw = await merchant_previews_col().find_one({"_id": preview_id})
    if not raw:
        logger.error("run_merchant_preview: preview %s not found", preview_id)
        return
    preview = PreviewDocument.model_validate(raw)

    await merchant_previews_col().update_one(
        {"_id": preview_id}, {"$set": {"state": "rendering"}}
    )

    if not REFERENCE_AVATAR.exists():
        await _fail_preview(
            preview,
            f"Reference avatar not found at {REFERENCE_AVATAR}. Set MIRRA_REFERENCE_AVATAR "
            "to a .avt exported from the installed CLO version.",
        )
        return

    try:
        ingestion_dir = get_latest_product_run_dir(
            cloth_id=preview.cloth_id, size_id=preview.size_id
        )
    except FileNotFoundError:
        await _fail_preview(
            preview,
            f"No product-ingestion run exists for {preview.cloth_id} + {preview.size_id}.",
        )
        return

    patterns_dir = ingestion_dir / "panels" / "dxf"
    if not patterns_dir.is_dir() or not any(patterns_dir.glob("*.dxf")):
        await _fail_preview(preview, f"Ingestion run {ingestion_dir.name} has no DXF panels.")
        return

    report_path = VTO_OUTPUT_DIR / f"{preview_id}__preview_report.json"
    try:
        ok, ctx = run_vto_pipeline(
            avatar_path=str(REFERENCE_AVATAR),
            patterns_dir=str(patterns_dir),
            use_default_panels=False,
            ingestion_output_dir=str(ingestion_dir),
            report_path=str(report_path),
            # The run tree is keyed by the tenant, not a shopper — a QA
            # preview must never land in a user's render directory.
            user_id=preview.tenant_id,
            cloth_id=preview.cloth_id,
            size_id=preview.size_id,
            return_context=True,
        )
    except Exception as exc:
        logger.exception("run_merchant_preview %s: unhandled error", preview_id)
        await _fail_preview(preview, str(exc))
        return

    if not ok:
        await _fail_preview(
            preview,
            f"CLO VTO pipeline failed — see {report_path} and the run directory for detail.",
        )
        return

    from .live_upload import save_preview_version

    glb = getattr(ctx, "textured_glb_path", None) or getattr(ctx, "glb_path", None)
    saved = save_preview_version(
        preview.tenant_id,
        preview.garment_id,
        preview_id,
        run_id=ctx.run_id,
        run_dir=ctx.output_dir,
        glb_path=glb,
    )
    if not saved.glb_relative_path:
        await _fail_preview(
            preview,
            "The simulation completed but CLO exported no GLB, so there is nothing to review.",
        )
        return

    await merchant_previews_col().update_one(
        {"_id": preview_id},
        {
            "$set": {
                "state": "ready",
                "glb_path": saved.glb_relative_path,
                "clo_run_id": ctx.run_id,
                "completed_at": _now(),
                "failure_reason": None,
            }
        },
    )
    await _set_pipeline_state(preview.garment_id, "preview_ready")
    logger.info("run_merchant_preview %s: ready (%s)", preview_id, saved.glb_relative_path)


async def _fail_preview(preview: PreviewDocument, reason: str) -> None:
    await merchant_previews_col().update_one(
        {"_id": preview.id},
        {"$set": {"state": "failed", "failure_reason": reason, "completed_at": _now()}},
    )
    await merchant_garments_col().update_one(
        {"_id": preview.garment_id},
        {
            "$set": {
                "pipeline.state": "failed",
                "pipeline.failure_reason": reason,
                "pipeline.updated_at": _now(),
            }
        },
    )
    logger.error("run_merchant_preview %s failed: %s", preview.id, reason)
