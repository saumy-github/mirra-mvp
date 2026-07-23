"""Step 10: write a structured error report for requested vs achieved values."""

from __future__ import annotations

from .context import Step1Context


def run(ctx: Step1Context) -> bool:
    requested_fields = ctx.normalized_targets.get("flat_requested_fields", {})
    measurement_import = ctx.apply_result.get("native_debug", {}).get("measurement_import", {})
    property_apply_success = bool(ctx.apply_result.get("property_debug", {}).get("apply_success"))
    avatar_state = ctx.readback_measurements.get("avatar_state", {})
    avatar_state_available = bool(avatar_state.get("success"))

    per_field = {}
    for field_name, requested_value in requested_fields.items():
        per_field[field_name] = {
            "requested": requested_value,
            "achieved": None,
            "error": None,
            "status": "not_read_back",
        }

    ctx.error_report = {
        "available": False,
        "preferred_strategy": ctx.contract.get("preferred_error_source"),
        "fallback_strategy": ctx.contract.get("fallback_error_source"),
        "apply_success": bool(ctx.apply_result.get("success")),
        "measurement_apply_mode_resolved": ctx.resolved_measurement_apply_mode,
        "measurement_import_success": bool(measurement_import.get("success")),
        "property_apply_success": property_apply_success,
        "avatar_state_readback_available": avatar_state_available,
        "reason": (
            "The current plugin now exposes avatar-state metadata and avatar-property debug details, but it "
            "still does not expose resulting body measurements field-by-field. This report preserves the "
            "requested values and marks direct measurement error computation as unavailable."
        ),
        "requested_fields": requested_fields,
        "per_field": per_field,
        "warnings": list(ctx.warnings),
    }
    ctx.log_json("error_report", ctx.error_report)
    ctx.logger.info(
        "Error report written (%d field(s) tracked, direct measurement error unavailable)", len(per_field)
    )
    return True
