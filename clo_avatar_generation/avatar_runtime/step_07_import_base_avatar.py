"""Step 7: get CLO to a clean scene holding the base avatar (reuse the open session when it is clean)."""

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

# ImportAvatar always adds an avatar, so avt_patch skips the base import (it would leave two avatars).
IMPORT_BASE_AVATAR_INTO_CLO = False

BASE_IMPORT_SETTLE_SECONDS = 2.0


def _scene_is_reusable(ctx: Step1Context, native_debug: dict) -> tuple[bool, str]:
    imported = native_debug.get("native_avatar_import") or {}
    if not imported.get("success"):
        return False, "no avatar has been imported since CLO's last new project"
    if int(native_debug.get("pattern_count") or 0) > 0:
        return False, "the scene still holds garment patterns"
    last_path = str(imported.get("path", "")).replace("\\", "/").lower()
    base_path = str(ctx.base_avatar_path).replace("\\", "/").lower()
    # The plugin records an applied .avs as the last import.
    if last_path != base_path and not last_path.endswith(".avs"):
        return False, f"the loaded avatar came from another file ({last_path})"
    return True, "base avatar already loaded; the next .avs overrides every size value"


def run(ctx: Step1Context) -> bool:
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path was not resolved before import")

    use_avs = ctx.resolved_measurement_apply_mode == "avs"

    if use_avs and ctx.reuse_session:
        native_debug = ctx.client.get_native_avatar_debug()
        reusable, reason = _scene_is_reusable(ctx, native_debug)
        if reusable:
            ctx.logger.info("Reusing the open CLO session: %s", reason)
            ctx.import_result = {
                "warm_session": True,
                "reason": reason,
                "base_avatar_imported": False,
                "native_debug": native_debug,
                "status": ctx.client.get_status(),
            }
            ctx.log_json("import_result", ctx.import_result)
            return True
        ctx.logger.info("CLO session not reusable (%s); starting a new project", reason)

    import_base = IMPORT_BASE_AVATAR_INTO_CLO or use_avs

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
    if import_base:
        ctx.logger.info("Importing base avatar into CLO: %s", ctx.base_avatar_path)
        avatar_result = ctx.client.import_avatar_avt(ctx.base_avatar_path)
        ctx.client.wait_for_queue(timeout=30)
        time.sleep(BASE_IMPORT_SETTLE_SECONDS)
    else:
        ctx.logger.info(
            "Skipping base avatar import; step 8 imports the patched avatar as the only one"
        )

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()

    ctx.import_result = {
        "warm_session": False,
        "new_project_result": new_project_result,
        "base_avatar_imported": import_base,
        "avatar_result": avatar_result,
        "native_debug": native_debug,
        "status": status,
    }
    ctx.log_json("import_result", ctx.import_result)

    if not import_base:
        return bool(new_project_result.get("success", True))

    success = bool(avatar_result.get("success")) and bool(
        native_debug.get("native_avatar_import", {}).get("success")
    )
    ctx.logger.info("Base avatar import %s", "succeeded" if success else "failed")
    return success
