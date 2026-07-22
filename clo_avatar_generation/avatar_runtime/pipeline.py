"""Pipeline orchestrator for Step-1 CLO avatar generation."""

from __future__ import annotations

from typing import Callable

from .context import Step1Context, utc_timestamp
from .health_watchdog import POLL_INTERVAL_SECONDS, HealthWatchdog
from .logging_setup import attach_run_file_handler, configure_console_logger
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
    attach_run_file_handler(ctx.logger, ctx.run_dir)
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
        ctx.log_json("input", ctx.input_payload)


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


def _output_summary_payload(ctx: Step1Context) -> dict:
    return {
        "status": ctx.status,
        "run_id": ctx.run_identity.run_id if ctx.run_identity else None,
        "user_id": ctx.user_id,
        "artifacts": {
            "saved_project": str(ctx.exported_project_path) if ctx.exported_project_path else None,
            "saved_avatar_direct": str(ctx.direct_avatar_export_path) if ctx.direct_avatar_export_path else None,
            "saved_avatar": str(ctx.extracted_avatar_path) if ctx.extracted_avatar_path else None,
            "saved_artifacts": dict(ctx.extracted_artifacts),
        },
        "warnings": list(ctx.warnings),
    }


def _record_step_result(ctx: Step1Context, step_name: str, success: bool, error: str | None = None) -> None:
    entry = {"step": step_name, "success": success}
    if error:
        entry["error"] = error
    ctx.step_results.append(entry)
    if success:
        ctx.logger.info("Step %s: passed", step_name)
    else:
        ctx.logger.error("Step %s: failed%s", step_name, f" - {error}" if error else "")


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
        return (
            ctx.save_outputs.get("reason")
            or ctx.save_outputs.get("save_result", {}).get("error")
            or "Saving outputs failed."
        )
    return None


def run_pipeline(ctx: Step1Context) -> Step1Context:
    ctx.logger = configure_console_logger()
    ctx.logger.info(
        "Starting CLO avatar-generation pipeline: user_id=%s requested_run_number=%s "
        "apply_mode_requested=%s active_field_filters=%s",
        ctx.user_id,
        ctx.requested_run_number,
        ctx.measurement_apply_mode_input,
        ctx.active_field_filters,
    )

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
        ("step_11_save_outputs", step_11_save_outputs, True, True),
    ]

    watchdog: HealthWatchdog | None = None

    pipeline_failed = False
    for step_name, step_fn, required, always_run in steps:
        if pipeline_failed and not always_run:
            continue

        ctx.current_step = step_name
        ctx.logger.info("Step %s: starting", step_name)
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

        if watchdog is None and step_name == "step_02_run_setup" and success:
            watchdog = HealthWatchdog(ctx)
            watchdog.start()
            ctx.logger.info("Health watchdog started (polling /health every %.0fs)", POLL_INTERVAL_SECONDS)

    if watchdog is not None:
        watchdog.stop()
        ctx.logger.info("Health watchdog stopped")

    if not pipeline_failed and ctx.status != "failed":
        ctx.status = "completed"

    if ctx.run_dir is not None:
        ctx.log_json("run_summary", _run_summary_payload(ctx))
        ctx.output_payload = _output_summary_payload(ctx)
        ctx.log_json("output", ctx.output_payload)
        ctx.logger.info("Run folder: %s", ctx.run_dir)
        ctx.logger.info("run.log: %s", ctx.run_dir / "run.log")

    if ctx.status == "completed":
        ctx.logger.info("CLO avatar-generation pipeline completed.")
    else:
        failed_steps = [step for step in ctx.step_results if not step.get("success")]
        if failed_steps:
            last_failed = failed_steps[-1]
            if last_failed.get("error"):
                ctx.logger.error("Failure detail: %s -> %s", last_failed["step"], last_failed["error"])
        ctx.logger.error("CLO avatar-generation pipeline failed.")

    return ctx
