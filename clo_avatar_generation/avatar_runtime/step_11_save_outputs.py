"""Step 11: save the current CLO project and export avatar artifacts when possible."""

from __future__ import annotations

from pathlib import Path
import shutil
import time
import zipfile

from .avt_patch import verify_avatar_fields
from .context import Step1Context
from .field_contract import get_v1_avt_patch_fields_for_gender


EXTRACTABLE_SUFFIXES = {
    ".avt": "result_avatar_from_project.avt",
    ".arr": "result_avatar.arr",
    ".iks": "result_avatar.iks",
    ".avs": "result_avatar.avs",
    ".mea": "result_avatar.mea",
}

# Phase 6 (after-1-jun/plan-03.md): CLO's internal mesh rebuild after an
# avt_patch import isn't tracked by our command queue, so save-project can
# race it and capture a structurally incomplete mesh even though every API
# call reports success. These three constants are the mitigation: a settle
# delay before each save attempt, a structural size check against the base
# avatar afterward, and a small bounded retry if that check looks bad.
MESH_SETTLE_DELAY_SECONDS = 2.5
MESH_SIZE_TOLERANCE_PCT = 3.0
MAX_SAVE_ATTEMPTS = 3


def _extract_project_artifacts(zprj_path: Path, run_dir: Path) -> dict[str, str]:
    extracted: dict[str, str] = {}
    if not zipfile.is_zipfile(zprj_path):
        return extracted

    with zipfile.ZipFile(zprj_path, "r") as archive:
        seen_suffixes: set[str] = set()
        for member in archive.namelist():
            member_path = Path(member)
            suffix = member_path.suffix.lower()
            if suffix not in EXTRACTABLE_SUFFIXES or suffix in seen_suffixes:
                continue

            target_name = EXTRACTABLE_SUFFIXES[suffix]
            target_path = run_dir / target_name
            with archive.open(member) as src, target_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted[suffix.lstrip(".")] = str(target_path)
            seen_suffixes.add(suffix)
    return extracted


def _last_result_for(status: dict, command_type: str) -> dict:
    for entry in reversed(status.get("last_results", [])):
        if entry.get("type") == command_type:
            return entry
    return {}


def _build_avt_field_index_map(ctx: Step1Context) -> dict[str, int]:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    return {
        str(entry["clo_target"]): int(entry["avt_feature_index"])
        for entry in get_v1_avt_patch_fields_for_gender(gender)
        if entry.get("avt_feature_index") is not None
    }


def _extracted_avt_looks_incomplete(
    extracted_avt_path: Path | None,
    base_avt_path: Path | None,
    tolerance_pct: float,
) -> tuple[bool, float | None]:
    """Compare the extracted avatar mesh size against the base avatar's size.

    A healthy morph should land close to (or slightly above) the base
    avatar's size, since it's the same topology with different feature
    values baked in. A save that races CLO's internal mesh rebuild can
    produce a structurally incomplete, noticeably smaller file — see
    after-1-jun/plan-03.md Phase 6 for the run pair that first surfaced
    this (~8% smaller, visibly broken geometry in CLO, yet
    verification_pass: true on the old binary-only check).
    """
    if extracted_avt_path is None or base_avt_path is None:
        return False, None
    if not extracted_avt_path.exists() or not base_avt_path.exists():
        return False, None
    base_size = base_avt_path.stat().st_size
    if base_size == 0:
        return False, None
    delta_pct = (extracted_avt_path.stat().st_size - base_size) / base_size * 100.0
    return delta_pct < -tolerance_pct, delta_pct


def run(ctx: Step1Context) -> bool:
    run_dir = ctx.require_run_dir()
    if not ctx.import_result:
        payload = {
            "saved": False,
            "reason": "Base avatar was never imported, so no current CLO project state could be saved.",
        }
        ctx.save_outputs = payload
        ctx.log_json("save_outputs", payload)
        ctx.logger.warning("Skipping save: base avatar was never imported")
        return True
    if ctx.apply_result is not None and not bool(ctx.apply_result.get("success")):
        payload = {
            "saved": False,
            "reason": "Skipped save because measurement apply failed and CLO state may be unstable.",
        }
        ctx.save_outputs = payload
        ctx.log_json("save_outputs", payload)
        ctx.logger.warning("Skipping save: measurement apply failed")
        return True

    zprj_path = run_dir / "result_project.zprj"
    direct_avatar_path = run_dir / "result_avatar.avt"
    # ExportAVT raises SEH exceptions on Windows that crash CLO's main thread.
    # Disabled until the plugin adds SEH handling around this CLO API call.
    direct_export_available = False

    save_result: dict = {}
    save_queue_status: dict = {}
    save_queue_error: str | None = None
    save_status: dict = {}
    save_queue_result: dict = {}
    direct_avatar_result: dict = {}
    direct_avatar_queue_status: dict = {}
    direct_avatar_queue_error: str | None = None
    direct_avatar_status: dict = {}
    direct_avatar_queue_result: dict = {}
    extracted_artifacts: dict[str, str] = {}
    mesh_incomplete = False
    mesh_delta_pct: float | None = None
    mesh_check_attempts: list[dict[str, object]] = []

    for attempt in range(1, MAX_SAVE_ATTEMPTS + 1):
        ctx.logger.info(
            "Waiting %.1fs for CLO's internal mesh rebuild to settle before saving (attempt %d/%d)",
            MESH_SETTLE_DELAY_SECONDS,
            attempt,
            MAX_SAVE_ATTEMPTS,
        )
        time.sleep(MESH_SETTLE_DELAY_SECONDS)

        ctx.logger.info("Saving CLO project: %s", zprj_path)
        save_result = ctx.client.save_project(zprj_path, thumbnail=False)
        save_queue_error = None
        try:
            save_queue_status = ctx.client.wait_for_queue(timeout=30)
        except TimeoutError as exc:
            save_queue_error = str(exc)
            save_queue_status = {"queue_drained": False, "error": save_queue_error}
        save_status = ctx.client.get_status()
        save_queue_result = _last_result_for(save_queue_status, "save-project")

        direct_avatar_result = {}
        direct_avatar_queue_status = {}
        direct_avatar_queue_error = None
        direct_avatar_status = {}
        direct_avatar_queue_result = {}
        if direct_export_available and save_queue_error is None:
            direct_avatar_result = ctx.client.export_avatar_avt(direct_avatar_path)
            try:
                direct_avatar_queue_status = ctx.client.wait_for_queue(timeout=30)
            except TimeoutError as exc:
                direct_avatar_queue_error = str(exc)
                direct_avatar_queue_status = {"queue_drained": False, "error": direct_avatar_queue_error}
            direct_avatar_status = ctx.client.get_status()
            direct_avatar_queue_result = _last_result_for(direct_avatar_queue_status, "export-avatar-avt")

        extracted_artifacts = {}
        if save_result.get("success") and zprj_path.exists():
            extracted_artifacts = _extract_project_artifacts(zprj_path, run_dir)

        ctx.exported_project_path = zprj_path if zprj_path.exists() else None
        ctx.direct_avatar_export_path = direct_avatar_path if direct_avatar_path.exists() else None
        ctx.extracted_artifacts = extracted_artifacts
        if ctx.direct_avatar_export_path is not None:
            ctx.extracted_avatar_path = ctx.direct_avatar_export_path
        elif "avt" in extracted_artifacts:
            ctx.extracted_avatar_path = Path(extracted_artifacts["avt"])
        else:
            ctx.extracted_avatar_path = None

        if save_queue_error or direct_avatar_queue_error:
            # A queue-level failure isn't a mesh-size problem - retrying via this
            # loop wouldn't address it, so stop here and let the existing
            # failure-reason logic below handle it.
            mesh_incomplete = False
            mesh_delta_pct = None
            break

        mesh_incomplete, mesh_delta_pct = _extracted_avt_looks_incomplete(
            ctx.extracted_avatar_path, ctx.base_avatar_path, MESH_SIZE_TOLERANCE_PCT
        )
        mesh_check_attempts.append(
            {
                "attempt": attempt,
                "extracted_avatar_size": (
                    ctx.extracted_avatar_path.stat().st_size
                    if ctx.extracted_avatar_path and ctx.extracted_avatar_path.exists()
                    else None
                ),
                "delta_pct_from_base": mesh_delta_pct,
                "flagged_incomplete": mesh_incomplete,
            }
        )

        if not mesh_incomplete:
            if attempt > 1:
                ctx.logger.info("Save attempt %d produced a structurally healthy mesh", attempt)
            break

        if attempt < MAX_SAVE_ATTEMPTS:
            ctx.logger.error(
                "Save attempt %d produced a suspiciously small avatar mesh (%.2f%% smaller than base "
                "avatar, threshold -%.1f%%) - retrying",
                attempt,
                abs(mesh_delta_pct) if mesh_delta_pct is not None else float("nan"),
                MESH_SIZE_TOLERANCE_PCT,
            )
        else:
            ctx.logger.error(
                "Save attempt %d produced a suspiciously small avatar mesh (%.2f%% smaller than base "
                "avatar, threshold -%.1f%%) - out of retries",
                attempt,
                abs(mesh_delta_pct) if mesh_delta_pct is not None else float("nan"),
                MESH_SIZE_TOLERANCE_PCT,
            )

    final_success = bool(ctx.exported_project_path) and bool(ctx.extracted_avatar_path)
    failure_reason = None
    if save_queue_error:
        final_success = False
        failure_reason = save_queue_error
    elif direct_avatar_queue_error:
        final_success = False
        failure_reason = direct_avatar_queue_error
    elif mesh_incomplete:
        final_success = False
        failure_reason = (
            f"Extracted avatar mesh looked structurally incomplete after {MAX_SAVE_ATTEMPTS} save "
            f"attempt(s) ({mesh_delta_pct:.2f}% smaller than the base avatar, threshold "
            f"-{MESH_SIZE_TOLERANCE_PCT:.1f}%) - see after-1-jun/plan-03.md Phase 6."
        )
    elif not final_success:
        if not ctx.exported_project_path:
            failure_reason = "CLO project save did not produce result_project.zprj."
        else:
            failure_reason = (
                "The project saved, but no avatar artifact was produced through direct AVT export or project extraction."
            )

    measurement_verification: dict | None = None
    if final_success and ctx.base_avatar_path is not None and ctx.extracted_avatar_path is not None:
        # Prefer the project-extracted AVT for verification: it has the binary-header + embedded-zip
        # format that verify_avatar_fields requires. The direct export may use a different format.
        verification_avt_path = (
            Path(extracted_artifacts["avt"])
            if "avt" in extracted_artifacts
            else ctx.extracted_avatar_path
        )
        measurement_verification = verify_avatar_fields(
            base_avt_path=ctx.base_avatar_path,
            actual_avt_path=verification_avt_path,
            requested_fields=ctx.normalized_targets.get("flat_requested_fields", {}),
            field_index_map=_build_avt_field_index_map(ctx),
        )
        ctx.log_json("measurement_verification", measurement_verification)
        if measurement_verification.get("available") and not measurement_verification.get("verification_pass"):
            final_success = False
            failure_reason = measurement_verification.get("reason") or (
                "Saved avatar did not match the requested AVT-backed measurements."
            )
            ctx.logger.error("Measurement verification failed: %s", failure_reason)
        elif measurement_verification.get("available"):
            ctx.logger.info("Measurement verification passed for all binary-checked fields")

    payload = {
        "saved": final_success,
        "save_result": save_result,
        "save_queue_status": save_queue_status,
        "save_queue_error": save_queue_error,
        "save_queue_result": save_queue_result,
        "save_status": save_status,
        "project_path": str(ctx.exported_project_path) if ctx.exported_project_path else None,
        "direct_avatar_export_available": direct_export_available,
        "direct_avatar_export_result": direct_avatar_result or None,
        "direct_avatar_export_queue_status": direct_avatar_queue_status or None,
        "direct_avatar_export_queue_error": direct_avatar_queue_error,
        "direct_avatar_export_queue_result": direct_avatar_queue_result or None,
        "direct_avatar_export_status": direct_avatar_status or None,
        "direct_avatar_path": str(ctx.direct_avatar_export_path) if ctx.direct_avatar_export_path else None,
        "extracted_artifacts": extracted_artifacts,
        "selected_avatar_path": str(ctx.extracted_avatar_path) if ctx.extracted_avatar_path else None,
        "selected_avatar_source": (
            "direct_export"
            if ctx.direct_avatar_export_path is not None
            else "project_extraction"
            if ctx.extracted_avatar_path is not None
            else None
        ),
        "mesh_integrity_check": {
            "tolerance_pct": MESH_SIZE_TOLERANCE_PCT,
            "attempts": mesh_check_attempts,
            "final_flagged_incomplete": mesh_incomplete,
        },
        "measurement_verification": measurement_verification,
        "reason": failure_reason,
    }
    ctx.save_outputs = payload
    ctx.log_json("save_outputs", payload)
    ctx.logger.info(
        "Save %s (avatar: %s)",
        "succeeded" if final_success else "failed",
        ctx.extracted_avatar_path,
    )
    return final_success
