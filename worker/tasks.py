"""RQ task functions for the native CLO worker.

Enqueued by string path from website/backend/src/{avatars,tryon}/engine.py
("worker.tasks.run_avatar_job" / "worker.tasks.run_tryon_render") — never
imported directly by the backend, since its Docker image doesn't have
clo_avatar_generation/clo_vto's dependencies installed (see
website/backend/src/core/queue.py).

Reuses website/backend/src's Mongo models/collections directly so job,
profile, and render document shapes never drift from what the FastAPI app
itself reads/writes. Run this via worker/run_worker.py, not standalone —
that entrypoint sets up sys.path and loads worker/.env first.

Scope: Step 0 (.agent/website-launch/07-step0-worker-queue.md) plus Steps
4/5 (GLB export + live_upload/ storage) for avatars — see
.agent/website-launch/11-step4-avatar-pipeline-invocation.md and
12-step5-avatar-storage.md. Try-on rendering (run_tryon_render) is still
Step 0 scope only — no GLB export/live_upload storage for try-on results
yet (Steps 9/10, separate, later passes).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "website" / "backend"
for _p in (REPO_ROOT, BACKEND_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from clo_avatar_generation.avatar_runtime.context import Step1Context  # noqa: E402
from clo_avatar_generation.avatar_runtime.field_contract import get_default_base_avatar  # noqa: E402
from clo_avatar_generation.avatar_runtime.pipeline import run_pipeline as run_avatar_pipeline  # noqa: E402
from clo_avatar_generation.avatar_runtime.run_manifest import get_next_run_number  # noqa: E402
from clo_vto.native_vto.pipeline import run_pipeline as run_vto_pipeline  # noqa: E402
from src.avatars import service as avatars_service  # noqa: E402
from src.avatars.models import AvatarJobDocument  # noqa: E402
from src.db import avatar_jobs_col, avatar_profiles_col, tryon_renders_col  # noqa: E402
from src.tryon.models import TryonRenderDocument  # noqa: E402

from product_ingestion.run_manifest import get_latest_product_run_dir  # noqa: E402

from .live_upload import save_avatar_version, save_render_version  # noqa: E402

logger = logging.getLogger("mirra.worker")

VTO_OUTPUT_DIR = REPO_ROOT / "clo_vto" / "output"

# One event loop for the whole worker process lifetime, reused across every
# job — NOT asyncio.run() per job. src.db's AsyncMongoClient is a
# process-lifetime singleton (see src/db.py's _client global); binding it to
# a fresh event loop on every job (which per-call asyncio.run() would do,
# since each call tears its loop down when done) breaks on the second job.
_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
    return _loop


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_default_base_avatar() -> Path:
    relative = get_default_base_avatar()
    return relative if relative.is_absolute() else (REPO_ROOT / relative)


# --- Avatar job --------------------------------------------------------------


def run_avatar_job(job_id: str) -> None:
    """RQ entrypoint. Synchronous on purpose — SimpleWorker (required on
    Windows, see worker/README.md) runs one job at a time in this same
    process/thread; there's no concurrency to gain from making this async."""
    _get_loop().run_until_complete(_run_avatar_job(job_id))


async def _run_avatar_job(job_id: str) -> None:
    raw = await avatar_jobs_col().find_one({"_id": job_id})
    if not raw:
        logger.error("run_avatar_job: job %s not found, nothing to do", job_id)
        return
    job = AvatarJobDocument.model_validate(raw)

    await avatar_jobs_col().update_one({"_id": job_id}, {"$set": {"state": "processing"}})

    try:
        run_number = get_next_run_number(job.user_id)
        ctx = Step1Context(
            user_id=job.user_id,
            requested_run_number=run_number,
            base_avatar_path_input=str(_resolve_default_base_avatar().resolve()),
            measurement_file_input=None,
            measurement_apply_mode_input="avt_patch",
            enable_legacy_route=False,
            active_field_filters=[],
            interactive=False,
        )
        logger.info("run_avatar_job %s: starting live pipeline (user_id=%s run=%03d)", job_id, job.user_id, run_number)
        ctx = run_avatar_pipeline(ctx)
    except Exception as exc:  # CLO unreachable, import error, anything unexpected
        logger.exception("run_avatar_job %s: unhandled error", job_id)
        await _fail_job(job_id, str(exc))
        return

    if ctx.status == "completed":
        # Reuses avatars/service.py's own profile-materialization logic
        # (same thing demo mode does on its timer-driven "ready" transition)
        # so live and demo produce identically-shaped avatar_profiles docs.
        profile = await avatars_service._materialize_profile(job)

        run_id = ctx.run_identity.run_id if ctx.run_identity else f"{job.user_id}-unknown"
        saved = save_avatar_version(
            job.user_id,
            run_id=run_id,
            run_dir=ctx.run_dir,
            zprj_path=ctx.exported_project_path,
            avt_path=ctx.extracted_avatar_path,
            glb_path=ctx.avatar_glb_path,
            step_results=ctx.step_results,
        )
        now = _now()
        await avatar_profiles_col().update_one(
            {"_id": profile.id},
            {
                "$set": {
                    "clo_avatar_avt_path": str(saved.avt_path) if saved.avt_path else None,
                    "avatar_glb_path": saved.glb_relative_path,
                    "generated_at": now,
                    "clo_run_id": run_id,
                    "updated_at": now,
                }
            },
        )
        await avatar_jobs_col().update_one(
            {"_id": job_id},
            {"$set": {"state": "ready", "avatar_profile_id": profile.id, "completed_at": now}},
        )
        logger.info(
            "run_avatar_job %s: ready (avatar_profile_id=%s, live_upload version=%03d, glb=%s)",
            job_id,
            profile.id,
            saved.version,
            saved.glb_relative_path,
        )
    else:
        await _fail_job(job_id, _pipeline_failure_reason(ctx))


def _pipeline_failure_reason(ctx: Step1Context) -> str:
    failed = [s for s in ctx.step_results if not s.get("success")]
    if not failed:
        return "CLO avatar pipeline failed with no recorded step error."
    last = failed[-1]
    detail = last.get("error") or "no error detail captured"
    return f"{last['step']}: {detail}"


async def _fail_job(job_id: str, reason: str) -> None:
    await avatar_jobs_col().update_one(
        {"_id": job_id}, {"$set": {"state": "failed", "failure_reason": reason, "completed_at": _now()}}
    )
    logger.warning("run_avatar_job %s: failed — %s", job_id, reason)


# --- Try-on render -------------------------------------------------------------


def run_tryon_render(render_id: str) -> None:
    _get_loop().run_until_complete(_run_tryon_render(render_id))


async def _run_tryon_render(render_id: str) -> None:
    raw = await tryon_renders_col().find_one({"_id": render_id})
    if not raw:
        logger.error("run_tryon_render: render %s not found, nothing to do", render_id)
        return
    render = TryonRenderDocument.model_validate(raw)

    await tryon_renders_col().update_one({"_id": render_id}, {"$set": {"state": "rendering"}})

    profile_raw = await avatar_profiles_col().find_one({"_id": render.avatar_profile_id})
    avt_path_str = profile_raw.get("clo_avatar_avt_path") if profile_raw else None
    if not avt_path_str:
        await _fail_render(
            render_id,
            "No CLO-generated avatar found for this profile — generate your avatar via the live "
            "pipeline before requesting a try-on.",
        )
        return
    avt_path = Path(avt_path_str)
    if not avt_path.exists():
        await _fail_render(render_id, f"Avatar file no longer exists on disk ({avt_path}) — regenerate your avatar.")
        return

    if not render.cloth_id:
        await _fail_render(
            render_id,
            "This render predates cloth/size tracking and cannot be resolved to a garment. "
            "Request the try-on again.",
        )
        return

    # The garment the shopper actually picked. Falling back to default panels
    # here is what made every try-on render the same untextured t-shirt, so a
    # missing ingestion run fails the render instead (doc 13, Phase 6).
    try:
        ingestion_dir = get_latest_product_run_dir(
            cloth_id=render.cloth_id, size_id=render.size_id
        )
    except FileNotFoundError:
        await _fail_render(
            render_id,
            f"No product-ingestion run exists for {render.cloth_id} + {render.size_id}. "
            "Run product_ingestion for that cloth and size first.",
        )
        return

    patterns_dir = ingestion_dir / "panels" / "dxf"
    if not patterns_dir.is_dir() or not any(patterns_dir.glob("*.dxf")):
        await _fail_render(
            render_id,
            f"Ingestion run {ingestion_dir.name} has no DXF panels at {patterns_dir}.",
        )
        return

    report_path = VTO_OUTPUT_DIR / f"{render_id}__native_vto_report.json"
    ctx = None
    try:
        logger.info(
            "run_tryon_render %s: starting live VTO pipeline (avatar=%s cloth=%s size=%s panels=%s)",
            render_id,
            avt_path,
            render.cloth_id,
            render.size_id,
            patterns_dir,
        )
        ok, ctx = run_vto_pipeline(
            avatar_path=str(avt_path),
            patterns_dir=str(patterns_dir),
            use_default_panels=False,
            ingestion_output_dir=str(ingestion_dir),
            report_path=str(report_path),
            user_id=render.user_id,
            cloth_id=render.cloth_id,
            size_id=render.size_id,
            return_context=True,
        )
    except Exception as exc:
        logger.exception("run_tryon_render %s: unhandled error", render_id)
        await _fail_render(render_id, str(exc))
        return

    if not ok:
        await _fail_render(
            render_id,
            f"CLO VTO pipeline failed — see {report_path} and the run directory for detail.",
        )
        return

    # Prefer the textured GLB; step_12 leaves it unset when it had nothing to inject.
    shipped_glb = getattr(ctx, "textured_glb_path", None) or getattr(ctx, "glb_path", None)
    saved = save_render_version(
        render.user_id,
        render_id,
        run_id=ctx.run_id,
        run_dir=ctx.output_dir,
        glb_path=shipped_glb,
        step_results=ctx.step_results,
    )
    await tryon_renders_col().update_one(
        {"_id": render_id},
        {
            "$set": {
                "state": "ready",
                "completed_at": _now(),
                "render_glb_path": saved.glb_relative_path,
                "clo_run_id": ctx.run_id,
            }
        },
    )
    logger.info(
        "run_tryon_render %s: ready (run=%s, glb=%s)",
        render_id,
        ctx.run_id,
        saved.glb_relative_path,
    )


async def _fail_render(render_id: str, reason: str) -> None:
    await tryon_renders_col().update_one(
        {"_id": render_id}, {"$set": {"state": "failed", "failure_reason": reason, "completed_at": _now()}}
    )
    logger.warning("run_tryon_render %s: failed — %s", render_id, reason)


# --- Merchant pipeline: Capture → Product Ingestion → VTO -------------------
#
# Enqueued by website/backend/src/merchant/engine.py. The bodies live in
# worker/merchant_tasks.py; these thin entrypoints exist so every job the
# backend enqueues resolves under one module path, and so both share the
# process-lifetime event loop above rather than opening their own.


def run_merchant_ingestion(run_id: str) -> None:
    """Step 2 for one (cloth, size) pair of a merchant garment."""
    from .merchant_tasks import _run_ingestion

    _get_loop().run_until_complete(_run_ingestion(run_id))


def run_merchant_preview(preview_id: str) -> None:
    """Step 3 against the reference avatar, for QA and merchant preview."""
    from .merchant_tasks import _run_preview

    _get_loop().run_until_complete(_run_preview(preview_id))
