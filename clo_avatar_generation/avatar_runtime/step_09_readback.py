"""Step 9: capture the post-apply avatar state as far as the plugin exposes it."""

from __future__ import annotations

from .context import Step1Context


def run(ctx: Step1Context) -> bool:
    native_debug = ctx.client.get_native_avatar_debug()
    avatar_state = ctx.client.get_avatar_state()
    status = ctx.client.get_status()

    ctx.readback_measurements = {
        "available": bool(avatar_state.get("success")),
        "strategy": "plugin_avatar_state_plus_native_debug",
        "native_debug": native_debug,
        "avatar_state": avatar_state,
        "status": status,
        "notes": [
            "The plugin now exposes avatar count, names, genders, and avatar property maps.",
            "The current SDK/plugin still does not expose resulting body measurements field-by-field.",
            "Saved project and extracted avatar artifacts remain the fallback readback evidence for this run.",
        ],
    }
    ctx.write_json("readback_measurements.json", ctx.readback_measurements)
    return True
