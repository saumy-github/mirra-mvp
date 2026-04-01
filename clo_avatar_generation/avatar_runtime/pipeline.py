"""Pipeline orchestrator for Step-1 CLO avatar generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .context import Step1Context, utc_timestamp
from .run_manifest import get_next_run_number, get_run_dir, RunIdentity
from .step_01_health import run as step_01_health
from .step_02_run_setup import run as step_02_run_setup
from .step_03_fetch_measurements import run as step_03_fetch_measurements
from .step_04_resolve_base_avatar import run as step_04_resolve_base_avatar
from .step_05_normalize_targets import run as step_05_normalize_targets
from .step_06_build_payloads import run as step_06_build_payloads
from .step_07_import_base_avatar import run as step_07_import_base_avatar
from .step_08_apply_measurements import run as step_08_apply_measurements
from .step_09_readback import run as step_09_readback
from .step_10_compute_error import run as step_10_compute_error
from .step_11_save_outputs import run as step_11_save_outputs


StepFn = Callable[[Step1Context], bool]


def _bootstrap_failure_run_dir(ctx: Step1Context) -> None:
    if ctx.run_dir is not None:
        return
    run_number = ctx.requested_run_number or get_next_run_number(ctx.user_id)
    ctx.run_identity = RunIdentity(user_id=ctx.user_id, number=run_number)
    ctx.run_dir = get_run_dir(ctx.run_identity)
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    if not ctx.input_payload:
        ctx.input_payload = {
            "run_id": ctx.run_identity.run_id,
            "user_id": ctx.user_id,
            "requested_run_number": run_number,
            "base_avatar_path_input": ctx.base_avatar_path_input,
            "created_at": utc_timestamp(),
            "workflow": "clo_avatar_generation.step1",
            "bootstrapped_after_failure": True,
        }
        ctx.write_json("input.json", ctx.input_payload)
    if ctx.health_result or ctx.capabilities:
        ctx.write_json(
            "health.json",
            {
                "health": ctx.health_result,
                "capabilities": ctx.capabilities,
            },
        )


def _run_summary_payload(ctx: Step1Context) -> dict:
    return {
        "status": ctx.status,
        "run_id": ctx.run_identity.run_id if ctx.run_identity else None,
        "user_id": ctx.user_id,
        "created_at": ctx.input_payload.get("created_at"),
        "updated_at": utc_timestamp(),
        "warnings": list(ctx.warnings),
        "steps": list(ctx.step_results),
    }


def _write_run_summary(ctx: Step1Context) -> None:
    if ctx.run_dir is None:
        return
    ctx.write_json("run_summary.json", _run_summary_payload(ctx))


def _write_output_json(ctx: Step1Context) -> None:
    if ctx.run_dir is None:
        return

    ctx.output_payload = {
        "status": ctx.status,
        "run_id": ctx.run_identity.run_id if ctx.run_identity else None,
        "user_id": ctx.user_id,
        "artifacts": {
            "input_json": str(ctx.artifact_path("input.json")),
            "mongo_snapshot": str(ctx.artifact_path("mongo_snapshot.json")) if (ctx.artifact_path("mongo_snapshot.json")).exists() else None,
            "target_measurements": str(ctx.artifact_path("target_measurements.json")) if (ctx.artifact_path("target_measurements.json")).exists() else None,
            "clo_payload_json": str(ctx.clo_payload_json_path) if ctx.clo_payload_json_path else None,
            "clo_payload_bridge": str(ctx.clo_payload_bridge_path) if ctx.clo_payload_bridge_path else None,
            "import_result": str(ctx.artifact_path("import_result.json")) if (ctx.artifact_path("import_result.json")).exists() else None,
            "apply_result": str(ctx.artifact_path("apply_result.json")) if (ctx.artifact_path("apply_result.json")).exists() else None,
            "readback_measurements": str(ctx.artifact_path("readback_measurements.json")) if (ctx.artifact_path("readback_measurements.json")).exists() else None,
            "error_report": str(ctx.artifact_path("error_report.json")) if (ctx.artifact_path("error_report.json")).exists() else None,
            "run_summary": str(ctx.artifact_path("run_summary.json")),
            "saved_project": str(ctx.exported_project_path) if ctx.exported_project_path else None,
            "saved_avatar": str(ctx.extracted_avatar_path) if ctx.extracted_avatar_path else None,
            "saved_artifacts": dict(ctx.extracted_artifacts),
        },
        "warnings": list(ctx.warnings),
    }
    ctx.write_json("output.json", ctx.output_payload)


def _record_step_result(ctx: Step1Context, step_name: str, success: bool, error: str | None = None) -> None:
    entry = {"step": step_name, "success": success}
    if error:
        entry["error"] = error
    ctx.step_results.append(entry)
    _write_run_summary(ctx)


def _derive_step_error(ctx: Step1Context, step_name: str) -> str | None:
    if step_name == "step_01_health":
        return (
            ctx.health_result.get("error")
            or ctx.capabilities.get("error")
            or "CLO health/capability check failed."
        )
    if step_name == "step_07_import_base_avatar":
        return (
            ctx.import_result.get("native_debug", {}).get("last_message")
            or ctx.import_result.get("avatar_result", {}).get("error")
            or "Base avatar import failed."
        )
    if step_name == "step_08_apply_measurements":
        return (
            ctx.apply_result.get("native_debug", {}).get("last_message")
            or ctx.apply_result.get("request_result", {}).get("error")
            or "Measurement application failed."
        )
    if step_name == "step_11_save_outputs":
        save_outputs_path = ctx.artifact_path("save_outputs.json") if ctx.run_dir else None
        if save_outputs_path and save_outputs_path.exists():
            try:
                payload = json.loads(save_outputs_path.read_text(encoding="utf-8"))
                return payload.get("reason") or payload.get("save_result", {}).get("error")
            except Exception:
                return "Saving outputs failed."
        return "Saving outputs failed."
    return None


def run_pipeline(ctx: Step1Context) -> Step1Context:
    steps: list[tuple[str, StepFn, bool, bool]] = [
        ("step_01_health", step_01_health, True, False),
        ("step_02_run_setup", step_02_run_setup, True, False),
        ("step_03_fetch_measurements", step_03_fetch_measurements, True, False),
        ("step_04_resolve_base_avatar", step_04_resolve_base_avatar, True, False),
        ("step_05_normalize_targets", step_05_normalize_targets, True, False),
        ("step_06_build_payloads", step_06_build_payloads, True, False),
        ("step_07_import_base_avatar", step_07_import_base_avatar, True, False),
        ("step_08_apply_measurements", step_08_apply_measurements, True, False),
        ("step_09_readback", step_09_readback, False, False),
        ("step_10_compute_error", step_10_compute_error, False, False),
        ("step_11_save_outputs", step_11_save_outputs, False, True),
    ]

    pipeline_failed = False
    for step_name, step_fn, required, always_run in steps:
        if pipeline_failed and not always_run:
            continue

        try:
            success = bool(step_fn(ctx))
            error = None
        except Exception as exc:  # pragma: no cover - exercised at runtime
            success = False
            error = str(exc)

        if step_name == "step_01_health" and not success and ctx.run_dir is None:
            _bootstrap_failure_run_dir(ctx)

        if not success and error is None:
            error = _derive_step_error(ctx, step_name)
        _record_step_result(ctx, step_name, success, error)

        if required and not success:
            pipeline_failed = True
            ctx.status = "failed"

    if not pipeline_failed and ctx.status != "failed":
        ctx.status = "completed"
    _write_run_summary(ctx)
    _write_output_json(ctx)
    return ctx
