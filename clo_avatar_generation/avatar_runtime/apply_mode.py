"""Shared measurement apply-mode resolution logic.

Used by both step 5 (to decide which payload to build) and step 8 (to decide
how to apply it), so the decision is made exactly once per run.
"""

from __future__ import annotations

from .context import Step1Context
from .field_contract import get_v1_avt_patch_fields_for_gender


def _avt_patch_supported_field_count(ctx: Step1Context) -> int:
    """Count requested fields with a verified AVT feature index.

    Computed directly from `ctx.normalized_targets` (set earlier in step 5)
    rather than `ctx.clo_payload_avt_patch_json`, which is not populated
    until step 6 runs.
    """
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    fields = get_v1_avt_patch_fields_for_gender(gender)
    requested = ctx.normalized_targets.get("flat_requested_fields", {})

    count = 0
    for entry in fields:
        clo_target = str(entry.get("clo_target", "")).strip()
        feature_index = entry.get("avt_feature_index")
        if not clo_target or feature_index is None:
            continue
        if clo_target in requested:
            count += 1
    return count


_LEGACY_MODES = {"csv", "avatar_properties"}


def resolve_apply_mode(ctx: Step1Context) -> str:
    requested = (ctx.measurement_apply_mode_input or "auto").strip().lower() or "auto"
    if requested not in {"auto", "csv", "avatar_properties", "avt_patch"}:
        raise ValueError(f"Unsupported measurement apply mode: {requested}")

    has_property_route = bool(ctx.capabilities.get("has_avatar_property_set"))
    has_avt_patch_route = (
        _avt_patch_supported_field_count(ctx) > 0
        and bool(ctx.capabilities.get("has_native_avatar_import", True))
    )

    if requested == "avt_patch":
        if not has_avt_patch_route:
            raise RuntimeError(
                "Apply mode avt_patch was requested, but no AVT-patch-supported fields were present in the "
                "current payload."
            )
        resolved = "avt_patch"
    elif requested == "avatar_properties":
        if not has_property_route:
            raise RuntimeError(
                "Apply mode avatar_properties was requested, but the running plugin does not advertise "
                "has_avatar_property_set. Install the rebuilt Windows plugin or use --apply-mode csv."
            )
        resolved = "avatar_properties"
    elif requested == "csv":
        resolved = "csv"
    elif has_avt_patch_route:
        resolved = "avt_patch"
    elif has_property_route:
        resolved = "avatar_properties"
    else:
        resolved = "csv"

    if resolved in _LEGACY_MODES and not ctx.enable_legacy_route:
        raise RuntimeError(
            f"Apply mode resolved to '{resolved}', a legacy/unsupported route, but --enable-legacy-route was "
            "not set. See clo_avatar_generation/schema/legacy_routes.md, or use --apply-mode avt_patch."
        )

    return resolved
