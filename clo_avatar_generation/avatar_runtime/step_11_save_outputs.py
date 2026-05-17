"""Step 11: save the current CLO project and export avatar artifacts when possible."""

from __future__ import annotations

from pathlib import Path
import shutil
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


def run(ctx: Step1Context) -> bool:
    run_dir = ctx.require_run_dir()
    if not ctx.import_result:
        payload = {
            "saved": False,
            "reason": "Base avatar was never imported, so no current CLO project state could be saved.",
        }
        ctx.write_json("save_outputs.json", payload)
        return True
    if ctx.apply_result is not None and not bool(ctx.apply_result.get("success")):
        payload = {
            "saved": False,
            "reason": "Skipped save because measurement apply failed and CLO state may be unstable.",
        }
        ctx.write_json("save_outputs.json", payload)
        return True

    zprj_path = run_dir / "result_project.zprj"
    save_result = ctx.client.save_project(zprj_path, thumbnail=False)
    save_queue_error: str | None = None
    try:
        save_queue_status = ctx.client.wait_for_queue(timeout=30)
    except TimeoutError as exc:
        save_queue_error = str(exc)
        save_queue_status = {"queue_drained": False, "error": save_queue_error}
    save_status = ctx.client.get_status()
    save_queue_result = _last_result_for(save_queue_status, "save-project")

    direct_avatar_result: dict = {}
    direct_avatar_queue_status: dict = {}
    direct_avatar_queue_error: str | None = None
    direct_avatar_status: dict = {}
    direct_avatar_queue_result: dict = {}
    direct_avatar_path = run_dir / "result_avatar.avt"
    # ExportAVT raises SEH exceptions on Windows that crash CLO's main thread.
    # Disabled until the plugin adds SEH handling around this CLO API call.
    direct_export_available = False

    if direct_export_available and save_queue_error is None:
        direct_avatar_result = ctx.client.export_avatar_avt(direct_avatar_path)
        try:
            direct_avatar_queue_status = ctx.client.wait_for_queue(timeout=30)
        except TimeoutError as exc:
            direct_avatar_queue_error = str(exc)
            direct_avatar_queue_status = {"queue_drained": False, "error": direct_avatar_queue_error}
        direct_avatar_status = ctx.client.get_status()
        direct_avatar_queue_result = _last_result_for(direct_avatar_queue_status, "export-avatar-avt")

    extracted_artifacts: dict[str, str] = {}
    if save_result.get("success") and zprj_path.exists():
        extracted_artifacts = _extract_project_artifacts(zprj_path, run_dir)

    ctx.exported_project_path = zprj_path if zprj_path.exists() else None
    ctx.direct_avatar_export_path = direct_avatar_path if direct_avatar_path.exists() else None
    ctx.extracted_artifacts = extracted_artifacts
    if ctx.direct_avatar_export_path is not None:
        ctx.extracted_avatar_path = ctx.direct_avatar_export_path
    elif "avt" in extracted_artifacts:
        ctx.extracted_avatar_path = Path(extracted_artifacts["avt"])

    final_success = bool(ctx.exported_project_path) and bool(ctx.extracted_avatar_path)
    failure_reason = None
    if save_queue_error:
        final_success = False
        failure_reason = save_queue_error
    elif direct_avatar_queue_error:
        final_success = False
        failure_reason = direct_avatar_queue_error
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
        ctx.write_json("measurement_verification.json", measurement_verification)
        if measurement_verification.get("available") and not measurement_verification.get("verification_pass"):
            final_success = False
            failure_reason = measurement_verification.get("reason") or (
                "Saved avatar did not match the requested AVT-backed measurements."
            )

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
        "measurement_verification": measurement_verification,
        "reason": failure_reason,
    }
    ctx.write_json("save_outputs.json", payload)
    return final_success
