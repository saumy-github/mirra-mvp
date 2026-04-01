"""Step 5: normalize Mongo measurements into the Step-1 CLO target contract."""

from __future__ import annotations

from typing import Any

from .context import Step1Context
from .field_contract import get_round_decimals, get_v1_fields_for_gender


def _round_number(value: float, decimals: int) -> float:
    return round(float(value), decimals)


def _normalize_field_value(entry: dict[str, Any], raw_value: Any, decimals: int) -> float:
    return _round_number(float(raw_value), decimals)


def run(ctx: Step1Context) -> bool:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    decimals = get_round_decimals()
    fields = get_v1_fields_for_gender(gender)

    drivers: dict[str, Any] = {}
    detailed_fields: dict[str, Any] = {}
    flat_requested_fields: dict[str, float] = {}

    for entry in fields:
        mongo_field = entry["mongo_field"]
        clo_target = entry["clo_target"]
        raw_value = ctx.mongo_doc[mongo_field]
        normalized_value = _normalize_field_value(entry, raw_value, decimals)

        payload_entry = {
            "mongo_field": mongo_field,
            "clo_target": clo_target,
            "value": normalized_value,
            "unit": entry["unit"],
            "mapping_type": entry.get("mapping_type", "direct"),
            "notes": entry.get("notes", ""),
        }

        flat_requested_fields[clo_target] = normalized_value
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
        "drivers": drivers,
        "details": detailed_fields,
        "flat_requested_fields": flat_requested_fields,
        "ignored_fields": ignored_fields,
    }
    ctx.write_json("target_measurements.json", ctx.normalized_targets)
    return True
