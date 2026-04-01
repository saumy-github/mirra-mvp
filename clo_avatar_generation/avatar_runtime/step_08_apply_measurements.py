"""Step 8: send the measurement payload to CLO."""

from __future__ import annotations

from .context import Step1Context


def run(ctx: Step1Context) -> bool:
    if ctx.clo_payload_bridge_path is None:
        raise RuntimeError("CLO bridge payload was not built before apply")
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path is missing during apply step")

    request_result = ctx.client.import_avatar_measurements(
        ctx.clo_payload_bridge_path,
        template_path=ctx.base_avatar_path,
    )
    ctx.client.wait_for_queue(timeout=30)

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()

    measurement_ok = bool(
        native_debug.get("measurement_import", {}).get("success")
    )
    ctx.apply_result = {
        "request_result": request_result,
        "native_debug": native_debug,
        "status": status,
        "bridge_path": str(ctx.clo_payload_bridge_path),
        "success": bool(request_result.get("success")) and measurement_ok,
    }
    ctx.write_json("apply_result.json", ctx.apply_result)
    return bool(ctx.apply_result["success"])
