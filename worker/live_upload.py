"""Copies a completed avatar pipeline run's final artifacts into
dev_upload/avatars/ or live_upload/avatars/ — the stable, versioned,
production-facing location. See
.agent/website-launch/12-step5-avatar-storage.md and
.agent/website-launch/22-remove-demo-live-mode-and-upload-split.md.

Which root is used is driven by APP_ENV (read from the worker process's own
environment, same mechanism as MONGODB_URI/REDIS_URL — set via
worker/.env): "production" writes to live_upload/, anything else
(including unset) defaults to dev_upload/. live_upload/ is reserved for
real production data once a Render-hosted backend has a way to receive it
(not built yet) — local/dev testing always lands in dev_upload/.

Does not touch clo_avatar_generation/output/ (the pipeline's own dev/debug
trail, with the full step-by-step log) — this only copies out the handful
of final files a production consumer (Step 6's serving route) needs, plus
a run_manifest.json pointer back to the source run for tracing a broken
result to its full debug log.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_UPLOAD_ROOT = REPO_ROOT / "dev_upload"
LIVE_UPLOAD_ROOT = REPO_ROOT / "live_upload"
DEV_UPLOAD_AVATARS_ROOT = DEV_UPLOAD_ROOT / "avatars"
LIVE_UPLOAD_AVATARS_ROOT = LIVE_UPLOAD_ROOT / "avatars"


def _upload_root() -> Path:
    app_env = os.environ.get("APP_ENV", "development")
    return LIVE_UPLOAD_ROOT if app_env == "production" else DEV_UPLOAD_ROOT


def _avatars_root() -> Path:
    return _upload_root() / "avatars"


def _renders_root() -> Path:
    return _upload_root() / "renders"


@dataclass
class SavedAvatarVersion:
    version: int
    version_dir: Path
    avt_path: Path | None
    zprj_path: Path | None
    glb_path: Path | None
    # Relative to whichever upload root was used — what
    # avatar_profiles.avatar_glb_path stores, since Step 6's serving route
    # resolves paths against that same root, not an absolute
    # worker-machine path.
    glb_relative_path: str | None


def _next_version(avatars_root: Path, user_id: str) -> int:
    user_root = avatars_root / user_id
    if not user_root.exists():
        return 1
    existing = [int(p.name) for p in user_root.iterdir() if p.is_dir() and p.name.isdigit()]
    return (max(existing) + 1) if existing else 1


def _copy(src: Path | None, dest: Path) -> Path | None:
    if src is None or not src.exists():
        return None
    shutil.copyfile(src, dest)
    return dest


def save_avatar_version(
    user_id: str,
    *,
    run_id: str,
    run_dir: Path,
    zprj_path: Path | None,
    avt_path: Path | None,
    glb_path: Path | None,
    step_results: list[dict],
) -> SavedAvatarVersion:
    """Copy one completed run's artifacts into a new
    <dev_upload|live_upload>/avatars/<user_id>/<version>/ folder (which root
    depends on APP_ENV — see module docstring). Never overwrites an earlier
    version — <version> is the next integer under that user's folder,
    matching clo_avatar_generation's own run-numbering convention."""
    avatars_root = _avatars_root()
    version = _next_version(avatars_root, user_id)
    version_dir = avatars_root / user_id / f"{version:03d}"
    version_dir.mkdir(parents=True, exist_ok=True)

    saved_zprj = _copy(zprj_path, version_dir / "avatar.zprj")
    saved_avt = _copy(avt_path, version_dir / "avatar.avt")
    saved_glb = _copy(glb_path, version_dir / "avatar.glb")
    _copy(run_dir / "run.log", version_dir / "run.log")

    manifest = {
        "user_id": user_id,
        "version": version,
        "source_run_id": run_id,
        "source_run_dir": str(run_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": step_results,
    }
    (version_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    glb_relative = f"avatars/{user_id}/{version:03d}/avatar.glb" if saved_glb else None

    return SavedAvatarVersion(
        version=version,
        version_dir=version_dir,
        avt_path=saved_avt,
        zprj_path=saved_zprj,
        glb_path=saved_glb,
        glb_relative_path=glb_relative,
    )


@dataclass
class SavedRenderVersion:
    render_dir: Path
    glb_path: Path | None
    # Relative to the upload root — what tryon_renders.render_glb_path stores,
    # since the serving route resolves against that same root.
    glb_relative_path: str | None


def save_render_version(
    user_id: str,
    render_id: str,
    *,
    run_id: str,
    run_dir: Path,
    glb_path: Path | None,
    step_results: list[dict],
) -> SavedRenderVersion:
    """Copy one finished try-on render's shipped artifacts into
    <dev_upload|live_upload>/renders/<user_id>/<render_id>/.

    Keyed by render_id rather than a version counter: a render is already
    unique and the frontend polls it by that id. Mirrors save_avatar_version
    otherwise, including the run_manifest.json pointer back to the debug run.
    """
    render_dir = _renders_root() / user_id / render_id
    render_dir.mkdir(parents=True, exist_ok=True)

    saved_glb = _copy(glb_path, render_dir / "tryon.glb")
    _copy(run_dir / "run.log", render_dir / "run.log")
    _copy(run_dir / "run_report.json", render_dir / "run_report.json")

    manifest = {
        "user_id": user_id,
        "render_id": render_id,
        "source_run_id": run_id,
        "source_run_dir": str(run_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": step_results,
    }
    (render_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    glb_relative = f"renders/{user_id}/{render_id}/tryon.glb" if saved_glb else None

    return SavedRenderVersion(
        render_dir=render_dir,
        glb_path=saved_glb,
        glb_relative_path=glb_relative,
    )
