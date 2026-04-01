"""Step 2: resolve run identity and create the run folder."""

from __future__ import annotations

from .context import Step1Context, utc_timestamp
from .run_manifest import RunIdentity, get_next_run_number, get_run_dir


def run(ctx: Step1Context) -> bool:
    run_number = ctx.requested_run_number or get_next_run_number(ctx.user_id)
    ctx.run_identity = RunIdentity(user_id=ctx.user_id, number=run_number)
    ctx.run_dir = get_run_dir(ctx.run_identity)
    ctx.run_dir.mkdir(parents=True, exist_ok=True)

    ctx.input_payload = {
        "run_id": ctx.run_identity.run_id,
        "user_id": ctx.user_id,
        "requested_run_number": run_number,
        "base_avatar_path_input": ctx.base_avatar_path_input,
        "created_at": utc_timestamp(),
        "workflow": "clo_avatar_generation.step1",
        "contract_version": ctx.contract.get("version"),
        "notes": [
            "JSON is the human-readable run contract.",
            "If direct AVS application is unavailable through the plugin, an internal bridge payload may be generated.",
        ],
    }

    ctx.write_json("input.json", ctx.input_payload)
    return True

