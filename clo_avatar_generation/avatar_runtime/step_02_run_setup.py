"""Step 2: resolve run identity and create the run folder."""

from __future__ import annotations

from .context import Step1Context, utc_timestamp
from .logging_setup import attach_run_file_handler
from .run_manifest import RunIdentity, get_next_run_number, get_run_dir


def run(ctx: Step1Context) -> bool:
    run_number = ctx.requested_run_number or get_next_run_number(ctx.user_id)
    ctx.run_identity = RunIdentity(user_id=ctx.user_id, number=run_number)
    ctx.run_dir = get_run_dir(ctx.run_identity)
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    attach_run_file_handler(ctx.logger, ctx.run_dir)
    ctx.logger.info("Run directory created: %s", ctx.run_dir)

    ctx.input_payload = {
        "run_id": ctx.run_identity.run_id,
        "user_id": ctx.user_id,
        "requested_run_number": run_number,
        "base_avatar_path_input": ctx.base_avatar_path_input,
        "measurement_source_requested": "json_file" if ctx.measurement_file_input else "auto",
        "measurement_file_input": ctx.measurement_file_input,
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "active_field_filters": list(ctx.active_field_filters),
        "created_at": utc_timestamp(),
        "workflow": "clo_avatar_generation.step1",
        "contract_version": ctx.contract.get("version"),
        "notes": [
            "JSON is the human-readable run contract.",
            "Phase-2 uses a JSON-first measurement source so the CLO-facing schema can be iterated before Mongo is updated.",
            "If direct AVS application is unavailable through the plugin, an internal bridge payload may be generated.",
            "Apply mode auto prefers the Windows avatar-property route when the plugin advertises it, then falls back to CSV.",
        ],
    }

    return True

