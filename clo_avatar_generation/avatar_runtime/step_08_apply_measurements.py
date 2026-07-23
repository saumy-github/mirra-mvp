"""Step 8: send the measurement payload to CLO."""

from __future__ import annotations

from .apply_mode import resolve_apply_mode
from .avt_patch import build_patched_avatar
from .context import Step1Context


def _last_result_for(status: dict, command_type: str) -> dict:
    for entry in reversed(status.get("last_results", [])):
        if entry.get("type") == command_type:
            return entry
    return {}


def _apply_via_csv(ctx: Step1Context) -> dict:
    if ctx.clo_payload_bridge_path is None:
        raise RuntimeError("CLO CSV bridge payload was not built before apply")
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path is missing during apply step")

    status_before = ctx.client.get_status()
    native_debug_before = ctx.client.get_native_avatar_debug()
    request_result = ctx.client.import_avatar_measurements(
        ctx.clo_payload_bridge_path,
        template_path=ctx.base_avatar_path,
    )
    queue_status = ctx.client.wait_for_queue(timeout=30)

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()
    queue_result = _last_result_for(queue_status, "import-avatar-measurements")
    bridge_preview = ctx.clo_payload_bridge_path.read_text(encoding="utf-8").splitlines()[:2]
    measurement_ok = bool(native_debug.get("measurement_import", {}).get("success"))

    return {
        "measurement_source": ctx.measurement_source,
        "measurement_source_path": str(ctx.measurement_source_path) if ctx.measurement_source_path else None,
        "active_field_filter": list(ctx.normalized_targets.get("active_field_filter", [])),
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "measurement_apply_mode_resolved": "csv",
        "request_mode": "import-avatar-measurements",
        "template_path_used": str(ctx.base_avatar_path),
        "status_before": status_before,
        "native_debug_before": native_debug_before,
        "request_result": request_result,
        "queue_status": queue_status,
        "queue_result": queue_result,
        "native_debug": native_debug,
        "status": status,
        "bridge_path": str(ctx.clo_payload_bridge_path),
        "bridge_size_bytes": ctx.clo_payload_bridge_path.stat().st_size,
        "bridge_preview_lines": bridge_preview,
        "success": bool(request_result.get("success")) and bool(queue_result.get("success")) and measurement_ok,
    }


def _apply_via_avatar_properties(ctx: Step1Context) -> dict:
    if not ctx.clo_payload_property_json:
        raise RuntimeError("Avatar-property payload was not built before apply")

    property_payload = ctx.clo_payload_property_json
    requested_properties = property_payload.get("properties", {})
    if not requested_properties:
        raise RuntimeError(
            "Avatar-property apply mode was selected, but there are no property-backed measurement fields in "
            "the current payload. Adjust the field filter or use --apply-mode csv."
        )

    status_before = ctx.client.get_status()
    property_debug_before = ctx.client.get_avatar_property_debug()
    request_result = ctx.client.set_avatar_properties(
        requested_properties,
        avatar_index=int(property_payload.get("avatar_index", 0)),
        unit=str(property_payload.get("unit", ctx.contract.get("unit", "cm"))),
    )
    queue_status = ctx.client.wait_for_queue(timeout=30)

    property_debug = ctx.client.get_avatar_property_debug()
    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()
    queue_result = _last_result_for(queue_status, "avatar-set-properties")
    changed_keys = list(property_debug.get("changed_keys", []))
    missing_after_keys = list(property_debug.get("missing_after_keys", []))

    notes: list[str] = []
    if not changed_keys:
        notes.append(
            "SetAvatarProperties completed, but GetAvatarProperties did not confirm any requested key change. "
            "Visual validation in CLO is still required."
        )
    if missing_after_keys:
        notes.append(
            "Some requested property keys did not appear in GetAvatarProperties after apply: "
            + ", ".join(missing_after_keys)
        )

    return {
        "measurement_source": ctx.measurement_source,
        "measurement_source_path": str(ctx.measurement_source_path) if ctx.measurement_source_path else None,
        "active_field_filter": list(ctx.normalized_targets.get("active_field_filter", [])),
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "measurement_apply_mode_resolved": "avatar_properties",
        "request_mode": "avatar/set-properties",
        "template_path_used": None,
        "status_before": status_before,
        "property_debug_before": property_debug_before,
        "request_result": request_result,
        "queue_status": queue_status,
        "queue_result": queue_result,
        "property_debug": property_debug,
        "native_debug": native_debug,
        "status": status,
        "bridge_path": str(ctx.clo_payload_bridge_path) if ctx.clo_payload_bridge_path else None,
        "property_payload": property_payload,
        "requested_property_count": len(requested_properties),
        "confirmed_changed_property_count": len(changed_keys),
        "notes": notes,
        "success": (
            bool(request_result.get("success"))
            and bool(queue_result.get("success"))
            and bool(property_debug.get("apply_success"))
        ),
    }


def _apply_via_avt_patch(ctx: Step1Context) -> dict:
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path is missing during AVT patch apply")

    patch_payload = ctx.clo_payload_avt_patch_json
    patch_targets = {
        field_name: float(value)
        for field_name, value in (patch_payload.get("field_values", {}) or {}).items()
    }
    patch_indexes = {
        field_name: int(value)
        for field_name, value in (patch_payload.get("field_indexes", {}) or {}).items()
    }
    if not patch_targets:
        raise RuntimeError(
            "AVT patch apply mode was selected, but there are no AVT-backed measurement fields in the "
            "current payload. Adjust the field filter or use a different apply mode."
        )

    patched_avatar_path = ctx.require_run_dir() / "clo_payload.patched.avt"
    patch_report = build_patched_avatar(
        ctx.base_avatar_path,
        patched_avatar_path,
        patch_targets,
        patch_indexes,
    )

    status_before = ctx.client.get_status()
    native_debug_before = ctx.client.get_native_avatar_debug()
    request_result = ctx.client.import_avatar_avt(patched_avatar_path)
    queue_status = ctx.client.wait_for_queue(timeout=30)

    native_debug = ctx.client.get_native_avatar_debug()
    status = ctx.client.get_status()
    queue_result = _last_result_for(queue_status, "import-avatar-avt")

    notes: list[str] = []
    unsupported_fields = list(patch_report.get("unsupported_requested_fields", []))
    if unsupported_fields:
        notes.append(
            "The AVT patch route currently skips requested fields without verified feature indexes: "
            + ", ".join(unsupported_fields)
        )

    return {
        "measurement_source": ctx.measurement_source,
        "measurement_source_path": str(ctx.measurement_source_path) if ctx.measurement_source_path else None,
        "active_field_filter": list(ctx.normalized_targets.get("active_field_filter", [])),
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "measurement_apply_mode_resolved": "avt_patch",
        "request_mode": "import-avatar-avt(patched)",
        "template_path_used": str(ctx.base_avatar_path),
        "status_before": status_before,
        "native_debug_before": native_debug_before,
        "request_result": request_result,
        "queue_status": queue_status,
        "queue_result": queue_result,
        "native_debug": native_debug,
        "status": status,
        "patched_avatar_path": str(patched_avatar_path),
        "patch_report": patch_report,
        "notes": notes,
        "success": (
            bool(request_result.get("success"))
            and bool(queue_result.get("success"))
            and bool(patch_report.get("supported_requested_field_count"))
        ),
    }


def run(ctx: Step1Context) -> bool:
    apply_mode = ctx.resolved_measurement_apply_mode or resolve_apply_mode(ctx)
    ctx.resolved_measurement_apply_mode = apply_mode
    ctx.logger.info("Applying measurements via %s route", apply_mode)

    if apply_mode == "avt_patch":
        ctx.apply_result = _apply_via_avt_patch(ctx)
    elif apply_mode == "avatar_properties":
        ctx.apply_result = _apply_via_avatar_properties(ctx)
    else:
        ctx.apply_result = _apply_via_csv(ctx)

    ctx.log_json("apply_result", ctx.apply_result)
    success = bool(ctx.apply_result["success"])
    ctx.logger.info("Measurement apply %s", "succeeded" if success else "failed")
    return success
