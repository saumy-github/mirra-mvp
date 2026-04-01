"""Step 11: save the current CLO project and extract avatar artifacts when possible."""

from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

from .context import Step1Context


EXTRACTABLE_SUFFIXES = {
    ".avt": "result_avatar.avt",
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
    ctx.client.wait_for_queue(timeout=30)

    extracted_artifacts = {}
    if save_result.get("success") and zprj_path.exists():
        extracted_artifacts = _extract_project_artifacts(zprj_path, run_dir)

    ctx.exported_project_path = zprj_path if zprj_path.exists() else None
    ctx.extracted_artifacts = extracted_artifacts
    if "avt" in extracted_artifacts:
        ctx.extracted_avatar_path = Path(extracted_artifacts["avt"])

    payload = {
        "save_result": save_result,
        "project_path": str(ctx.exported_project_path) if ctx.exported_project_path else None,
        "extracted_artifacts": extracted_artifacts,
    }
    ctx.write_json("save_outputs.json", payload)
    return bool(save_result.get("success"))
