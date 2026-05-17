"""Step 8: send the measurement payload to CLO."""

from __future__ import annotations

import json

from .avt_patch import build_patched_avatar
from .context import Step1Context


def _load_json_artifact(ctx: Step1Context, name: str) -> dict:
    path = ctx.artifact_path(name)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _last_result_for(status: dict, command_type: str) -> dict:
    for entry in reversed(status.get("last_results", [])):
        if entry.get("type") == command_type:
            return entry
    return {}


def _resolve_apply_mode(ctx: Step1Context) -> str:
    requested = (ctx.measurement_apply_mode_input or "auto").strip().lower() or "auto"
    if requested not in {"auto", "csv", "avatar_properties", "avt_patch"}:
        raise ValueError(f"Unsupported measurement apply mode: {requested}")

    has_property_route = bool(ctx.capabilities.get("has_avatar_property_set"))
    avt_patch_field_count = len((ctx.clo_payload_avt_patch_json or {}).get("field_values", {}))
    has_avt_patch_route = avt_patch_field_count > 0 and bool(ctx.capabilities.get("has_native_avatar_import", True))
    if requested == "avt_patch":
        if not has_avt_patch_route:
            raise RuntimeError(
                "Apply mode avt_patch was requested, but no AVT-patch-supported fields were present in the "
                "current payload."
            )
        return "avt_patch"
    if requested == "avatar_properties":
        if not has_property_route:
            raise RuntimeError(
                "Apply mode avatar_properties was requested, but the running plugin does not advertise "
                "has_avatar_property_set. Install the rebuilt Windows plugin or use --apply-mode csv."
            )
        return "avatar_properties"
    if requested == "csv":
        return "csv"
    if has_avt_patch_route:
        return "avt_patch"
    if has_property_route:
        return "avatar_properties"
    return "csv"


def _apply_via_csv(ctx: Step1Context, bridge_manifest: dict) -> dict:
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
        "bridge_manifest": bridge_manifest,
        "bridge_path": str(ctx.clo_payload_bridge_path),
        "bridge_size_bytes": ctx.clo_payload_bridge_path.stat().st_size,
        "bridge_preview_lines": bridge_preview,
        "property_payload_path": str(ctx.clo_payload_property_path) if ctx.clo_payload_property_path else None,
        "success": bool(request_result.get("success")) and bool(queue_result.get("success")) and measurement_ok,
    }


def _apply_via_avatar_properties(ctx: Step1Context, bridge_manifest: dict) -> dict:
    if ctx.clo_payload_property_path is None:
        raise RuntimeError("Avatar-property payload was not built before apply")

    property_payload = ctx.clo_payload_property_json or _load_json_artifact(ctx, "clo_payload.properties.json")
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
        "bridge_manifest": bridge_manifest,
        "bridge_path": str(ctx.clo_payload_bridge_path) if ctx.clo_payload_bridge_path else None,
        "property_payload_path": str(ctx.clo_payload_property_path),
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


def _apply_via_avt_patch(ctx: Step1Context, bridge_manifest: dict) -> dict:
    if ctx.base_avatar_path is None:
        raise RuntimeError("Base avatar path is missing during AVT patch apply")

    patch_payload = ctx.clo_payload_avt_patch_json or _load_json_artifact(ctx, "clo_payload.avt_patch.json")
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
        "bridge_manifest": bridge_manifest,
        "bridge_path": str(ctx.clo_payload_bridge_path) if ctx.clo_payload_bridge_path else None,
        "property_payload_path": str(ctx.clo_payload_property_path) if ctx.clo_payload_property_path else None,
        "avt_patch_payload_path": str(ctx.clo_payload_avt_patch_path) if ctx.clo_payload_avt_patch_path else None,
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
    bridge_manifest = _load_json_artifact(ctx, "clo_payload_manifest.json")
    apply_mode = _resolve_apply_mode(ctx)
    ctx.resolved_measurement_apply_mode = apply_mode

    if apply_mode == "avt_patch":
        ctx.apply_result = _apply_via_avt_patch(ctx, bridge_manifest)
    elif apply_mode == "avatar_properties":
        ctx.apply_result = _apply_via_avatar_properties(ctx, bridge_manifest)
    else:
        ctx.apply_result = _apply_via_csv(ctx, bridge_manifest)

    ctx.write_json("apply_result.json", ctx.apply_result)
    return bool(ctx.apply_result["success"])
