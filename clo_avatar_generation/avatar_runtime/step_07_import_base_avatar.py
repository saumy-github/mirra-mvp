"""Step 7: load a fresh project and import the locked base avatar into CLO."""

from __future__ import annotations

import time

from .context import Step1Context

# CLO keeps working internally after a command returns — wait_for_queue only
# proves the SDK call returned, not that the engine finished. Without a pause
# here, new-project runs while the previous run is still writing its GLB and
# silently fails to clear the scene: five back-to-back runs left 3,4,1,1,2
# avatars, the same five with a 25s gap left 3,1,1,1,1 (2026-08-23).
# Same class of race step_11 already handles with MESH_SETTLE_DELAY_SECONDS.
CLO_SETTLE_SECONDS = 4.0

# ImportAvatar always ADDS an avatar — the SDK exposes no replace flag — so
# importing the base here and the patched copy in step 8 left two avatars in
# every scene, and step 11 was exporting the wrong one. The patched file is a
# full standalone avatar built from base-1.avt on disk, so CLO never needs the
# base loaded. Set True to restore the old two-import behaviour.
IMPORT_BASE_AVATAR_INTO_CLO = False


def run(ctx: Step1Context) -> bool:
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path was not resolved before import")

    # Let whatever ran before us finish before asking CLO to clear the scene.
    ctx.client.wait_for_queue(timeout=30)
    ctx.logger.info("Settling %.1fs before new project", CLO_SETTLE_SECONDS)
    time.sleep(CLO_SETTLE_SECONDS)

    ctx.logger.info("Starting new CLO project")
    new_project_result = ctx.client.new_project()
    ctx.client.wait_for_queue(timeout=30)
    # And let the clear itself complete before anything is imported.
    time.sleep(CLO_SETTLE_SECONDS)

    avatar_result: dict = {}
    if IMPORT_BASE_AVATAR_INTO_CLO:
        ctx.logger.info("Importing base avatar into CLO: %s", ctx.base_avatar_path)
        avatar_result = ctx.client.import_avatar_avt(ctx.base_avatar_path)
        ctx.client.wait_for_queue(timeout=30)
    else:
        ctx.logger.info(
            "Skipping base avatar import; step 8 imports the patched avatar as the only one"
        )

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()

    ctx.import_result = {
        "new_project_result": new_project_result,
        "base_avatar_imported": IMPORT_BASE_AVATAR_INTO_CLO,
        "avatar_result": avatar_result,
        "native_debug": native_debug,
        "status": status,
    }
    ctx.log_json("import_result", ctx.import_result)

    if not IMPORT_BASE_AVATAR_INTO_CLO:
        return bool(new_project_result.get("success", True))

    success = bool(avatar_result.get("success")) and bool(
        native_debug.get("native_avatar_import", {}).get("success")
    )
    ctx.logger.info("Base avatar import %s", "succeeded" if success else "failed")
    return success

