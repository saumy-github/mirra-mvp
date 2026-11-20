"""Step 1: check CLO/plugin health and capabilities."""

from __future__ import annotations

from .context import Step1Context


REQUIRED_CAPABILITIES = (
    "has_native_avatar_import",
    "has_avatar_measurement_import",
)


def run(ctx: Step1Context) -> bool:
    ctx.logger.info("Checking CLO plugin health and capabilities")
    ctx.health_result = ctx.client.health_check()
    ctx.capabilities = ctx.client.get_capabilities()

    health_ok = ctx.health_result.get("status") == "ok"
    capability_ok = bool(ctx.capabilities.get("success", False))
    missing = [
        name for name in REQUIRED_CAPABILITIES
        if not bool(ctx.capabilities.get(name, False))
    ]

    ctx.log_json(
        "health",
        {
            "health": ctx.health_result,
            "capabilities": ctx.capabilities,
            "missing_capabilities": missing,
        },
    )

    if not health_ok:
        ctx.logger.error("CLO plugin health check failed: %s", ctx.health_result)
        return False
    # A plugin built against another SDK than the running CLO mis-dispatches
    # calls and can crash CLO (rev-eng findings 14, 47). Refuse before any import.
    if ctx.health_result.get("host_matches_sdk") is False:
        ctx.logger.error(
            "Plugin SDK %s does not match the running CLO %s; rebuild the plugin before running.",
            ctx.health_result.get("sdk_clo_version"),
            ctx.health_result.get("host_app_version"),
        )
        return False
    if not capability_ok:
        ctx.logger.error("CLO plugin capabilities check failed: %s", ctx.capabilities)
        return False
    if missing:
        ctx.warnings.append(
            "Plugin is reachable but missing capabilities required by the Step-1 lane: "
            + ", ".join(missing)
        )
        ctx.logger.warning("Plugin missing required capabilities: %s", ", ".join(missing))
        return False
    ctx.logger.info("CLO plugin healthy; required capabilities present")
    return True

