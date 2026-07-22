"""Step 7: load a fresh project and import the locked base avatar into CLO."""

from __future__ import annotations

from .context import Step1Context


def run(ctx: Step1Context) -> bool:
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path was not resolved before import")

    ctx.logger.info("Starting new CLO project")
    new_project_result = ctx.client.new_project()
    ctx.client.wait_for_queue(timeout=30)

    ctx.logger.info("Importing base avatar into CLO: %s", ctx.base_avatar_path)
    avatar_result = ctx.client.import_avatar_avt(ctx.base_avatar_path)
    ctx.client.wait_for_queue(timeout=30)

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()

    ctx.import_result = {
        "new_project_result": new_project_result,
        "avatar_result": avatar_result,
        "native_debug": native_debug,
        "status": status,
    }
    ctx.log_json("import_result", ctx.import_result)

    success = bool(avatar_result.get("success")) and bool(
        native_debug.get("native_avatar_import", {}).get("success")
    )
    ctx.logger.info("Base avatar import %s", "succeeded" if success else "failed")
    return success

