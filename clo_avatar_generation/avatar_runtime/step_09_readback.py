"""Step 9: capture the post-apply avatar state as far as the plugin exposes it."""

from __future__ import annotations

from .context import Step1Context


def run(ctx: Step1Context) -> bool:
    ctx.logger.info("Reading back avatar/native/property debug state")
    native_debug = ctx.client.get_native_avatar_debug()
    property_debug = ctx.client.get_avatar_property_debug()
    # /avatars/state calls CLO API (GetAvatarCount etc.) from the HTTP thread on Windows,
    # which causes a SEH crash that kills the server. Skipped until the plugin routes
    # those calls through the main-thread command queue.
    avatar_state: dict = {"success": False, "error": "skipped: unsafe CLO API call from HTTP thread on Windows"}
    status = ctx.client.get_status()

    ctx.readback_measurements = {
        "available": False,
        "strategy": "plugin_avatar_state_plus_native_debug",
        "measurement_apply_mode_resolved": ctx.resolved_measurement_apply_mode,
        "native_debug": native_debug,
        "property_debug": property_debug,
        "avatar_state": avatar_state,
        "status": status,
        "notes": [
            "The plugin now exposes avatar count, names, genders, and avatar property maps.",
            "The avatar-property debug endpoint is useful for route validation, but it is not yet a trustworthy body-measurement readback source.",
            "Saved project and extracted avatar artifacts remain the fallback readback evidence for this run.",
            "avatar_state readback is disabled: /avatars/state calls CLO API from the HTTP thread on Windows, causing a server crash.",
        ],
    }
    ctx.log_json("readback_measurements", ctx.readback_measurements)
    ctx.logger.info("Readback complete (avatar_state readback disabled)")
    return True
