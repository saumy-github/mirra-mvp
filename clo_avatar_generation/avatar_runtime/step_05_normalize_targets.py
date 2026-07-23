"""Step 5: normalize Mongo measurements into the Step-1 CLO target contract."""

from __future__ import annotations

from typing import Any

from .apply_mode import resolve_apply_mode
from .context import Step1Context
from .field_contract import get_round_decimals, get_v1_fields_for_gender


def _round_number(value: float, decimals: int) -> float:
    return round(float(value), decimals)


def _normalize_field_value(entry: dict[str, Any], raw_value: Any, decimals: int) -> float:
    return _round_number(float(raw_value), decimals)


def _is_active_entry(entry: dict[str, Any], active_filters: set[str]) -> bool:
    if not active_filters:
        return True
    candidates = {
        str(entry.get("mongo_field", "")).strip(),
        str(entry.get("clo_target", "")).strip(),
    }
    return any(candidate in active_filters for candidate in candidates if candidate)


def run(ctx: Step1Context) -> bool:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    decimals = get_round_decimals()
    fields = get_v1_fields_for_gender(gender)
    active_filters = {
        value.strip()
        for value in ctx.active_field_filters
        if isinstance(value, str) and value.strip()
    }

    drivers: dict[str, Any] = {}
    detailed_fields: dict[str, Any] = {}
    flat_requested_fields: dict[str, float] = {}
    flat_requested_property_fields: dict[str, float] = {}

    for entry in fields:
        if not _is_active_entry(entry, active_filters):
            continue
        mongo_field = entry["mongo_field"]
        clo_target = entry["clo_target"]
        property_key = str(entry.get("property_key", "")).strip() or None
        raw_value = ctx.mongo_doc[mongo_field]
        normalized_value = _normalize_field_value(entry, raw_value, decimals)

        payload_entry = {
            "mongo_field": mongo_field,
            "clo_target": clo_target,
            "property_key": property_key,
            "value": normalized_value,
            "unit": entry["unit"],
            "apply_routes": list(entry.get("apply_routes", [])),
            "mapping_type": entry.get("mapping_type", "direct"),
            "notes": entry.get("notes", ""),
        }

        flat_requested_fields[clo_target] = normalized_value
        if property_key:
            flat_requested_property_fields[property_key] = normalized_value
        if clo_target in {"Weight", "Total Height"}:
            key = "width_driver" if clo_target == "Weight" else "height_driver"
            drivers[key] = payload_entry
        else:
            detailed_fields[clo_target] = payload_entry

    ignored_fields = [
        {
            "name": name,
            "reason": reason,
        }
        for name, reason in sorted(ctx.contract.get("out_of_scope_notes", {}).items())
    ]

    ctx.normalized_targets = {
        "version": ctx.contract.get("version"),
        "gender": gender,
        "unit": ctx.contract.get("unit", "cm"),
        "round_decimals": decimals,
        "active_field_filter": sorted(active_filters),
        "drivers": drivers,
        "details": detailed_fields,
        "flat_requested_fields": flat_requested_fields,
        "flat_requested_property_fields": flat_requested_property_fields,
        "ignored_fields": ignored_fields,
    }
    ctx.log_json("target_measurements", ctx.normalized_targets)
    ctx.logger.info("Normalized %d measurement field(s) for gender=%s", len(flat_requested_fields), gender)
    ctx.resolved_measurement_apply_mode = resolve_apply_mode(ctx)
    ctx.logger.info("Resolved measurement apply mode: %s", ctx.resolved_measurement_apply_mode)
    return True
