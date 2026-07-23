"""Step 6: build the Step-1 payload artifacts for both apply routes."""

from __future__ import annotations

import csv
from pathlib import Path

from .context import Step1Context
from .field_contract import (
    get_v1_avt_patch_fields_for_gender,
    get_measurement_bridge_template_csv,
    get_v1_fields_for_gender,
    get_v1_property_fields_for_gender,
)


def _format_value(value: float) -> str:
    return f"{float(value):.2f}"


def _build_bridge_headers_and_values(ctx: Step1Context) -> tuple[list[str], list[str]]:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    fields = get_v1_fields_for_gender(gender)

    headers: list[str] = []
    values: list[str] = []
    requested = ctx.normalized_targets.get("flat_requested_fields", {})
    for entry in fields:
        clo_target = entry["clo_target"]
        if clo_target not in requested:
            continue
        headers.append(clo_target)
        values.append(_format_value(requested[clo_target]))
    return headers, values


def _build_property_payload(
    ctx: Step1Context,
) -> tuple[dict[str, object], list[str], list[str]]:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    fields = get_v1_property_fields_for_gender(gender)
    requested = ctx.normalized_targets.get("flat_requested_property_fields", {})

    properties: dict[str, str] = {}
    property_keys_in_order: list[str] = []
    supported_targets: set[str] = set()

    for entry in fields:
        property_key = str(entry.get("property_key", "")).strip()
        clo_target = str(entry.get("clo_target", "")).strip()
        if not property_key:
            continue
        supported_targets.add(clo_target)
        if property_key not in requested:
            continue
        property_keys_in_order.append(property_key)
        properties[property_key] = _format_value(requested[property_key])

    skipped_requested_fields = [
        field_name
        for field_name in ctx.normalized_targets.get("flat_requested_fields", {})
        if field_name not in supported_targets
    ]

    payload: dict[str, object] = {
        "avatar_index": 0,
        "unit": ctx.contract.get("unit", "cm"),
        "properties": properties,
    }
    return payload, property_keys_in_order, skipped_requested_fields


def _build_avt_patch_payload(
    ctx: Step1Context,
) -> tuple[dict[str, object], list[str], list[str]]:
    gender = str(ctx.mongo_doc.get("gender", "")).strip().lower()
    fields = get_v1_avt_patch_fields_for_gender(gender)
    requested = ctx.normalized_targets.get("flat_requested_fields", {})

    field_indexes: dict[str, int] = {}
    field_values: dict[str, float] = {}
    supported_targets: set[str] = set()
    field_names_in_order: list[str] = []

    for entry in fields:
        clo_target = str(entry.get("clo_target", "")).strip()
        feature_index = entry.get("avt_feature_index")
        if not clo_target or feature_index is None:
            continue
        supported_targets.add(clo_target)
        if clo_target not in requested:
            continue
        field_names_in_order.append(clo_target)
        field_indexes[clo_target] = int(feature_index)
        field_values[clo_target] = float(requested[clo_target])

    skipped_requested_fields = [
        field_name for field_name in requested if field_name not in supported_targets
    ]

    payload: dict[str, object] = {
        "unit": ctx.contract.get("unit", "cm"),
        "field_indexes": field_indexes,
        "field_values": {
            field_name: _format_value(field_values[field_name]) for field_name in field_names_in_order
        },
    }
    return payload, field_names_in_order, skipped_requested_fields


def _resolve_template_path() -> Path | None:
    template_relative = get_measurement_bridge_template_csv()
    if template_relative is None:
        return None
    if template_relative.is_absolute():
        return template_relative
    return (Path(__file__).resolve().parents[2] / template_relative).resolve()


def _read_single_row_csv(path: Path) -> tuple[list[str], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise ValueError(
            f"Measurement bridge template must contain one header row and one value row: {path}"
        )
    headers = rows[0]
    values = list(rows[1])
    if len(values) < len(headers):
        values.extend([""] * (len(headers) - len(values)))
    elif len(values) > len(headers):
        values = values[: len(headers)]
    return headers, values


def _build_csv_bridge(ctx: Step1Context) -> dict[str, object]:
    requested_headers, requested_values = _build_bridge_headers_and_values(ctx)
    requested_map = dict(zip(requested_headers, requested_values, strict=False))

    template_path = _resolve_template_path()
    bridge_strategy = "requested_fields_only_csv"
    overridden_headers: list[str] = []
    seeded_template_headers: list[str] = []
    unmatched_requested_fields: list[str] = []

    if template_path and template_path.exists():
        template_headers, template_values = _read_single_row_csv(template_path)
        headers = list(template_headers)
        values = list(template_values)
        bridge_strategy = "template_seeded_csv"

        header_index = {header: idx for idx, header in enumerate(headers)}
        for field_name, field_value in requested_map.items():
            idx = header_index.get(field_name)
            if idx is None:
                unmatched_requested_fields.append(field_name)
                continue
            values[idx] = field_value
            overridden_headers.append(field_name)

        seeded_template_headers = [
            header for idx, header in enumerate(headers) if header not in overridden_headers and bool(values[idx])
        ]
    else:
        headers = requested_headers
        values = requested_values

    bridge_path = ctx.artifact_path("clo_payload.bridge.csv")
    with bridge_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(values)
    ctx.clo_payload_bridge_path = bridge_path

    return {
        "bridge_strategy": bridge_strategy,
        "template_path": str(template_path) if template_path and template_path.exists() else None,
        "requested_headers": requested_headers,
        "requested_values": requested_values,
        "headers": headers,
        "values": values,
        "overridden_headers": overridden_headers,
        "seeded_template_headers": seeded_template_headers,
        "unmatched_requested_fields": unmatched_requested_fields,
        "bridge_path": str(bridge_path),
        "csv_schema_status": (
            "runtime_bridge_built_from_unconfirmed_template_seed_values"
            if bridge_strategy == "template_seeded_csv"
            else "runtime_bridge_unverified_against_direct_clo_export"
        ),
    }


def run(ctx: Step1Context) -> bool:
    apply_mode = ctx.resolved_measurement_apply_mode or "avt_patch"
    ctx.logger.info("Building payload for apply mode: %s", apply_mode)

    ctx.clo_payload_json = {
        "preferred_clo_payload": ctx.contract.get("preferred_clo_payload", "avs"),
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "measurement_apply_mode_resolved": apply_mode,
        "measurement_source": ctx.measurement_source,
        "measurement_source_path": str(ctx.measurement_source_path) if ctx.measurement_source_path else None,
        "active_field_filter": list(ctx.normalized_targets.get("active_field_filter", [])),
        "base_avatar": ctx.base_avatar_metadata,
        "normalized_targets": ctx.normalized_targets,
        "notes": [
            "The measurement source for Phase-2 is JSON-first so the CLO schema can be iterated safely.",
            "All outgoing linear body-measurement values are rounded to two decimals and written in cm.",
            "Only the payload for the resolved apply mode is built. csv and avatar_properties are legacy "
            "routes requiring --apply-mode <route> --enable-legacy-route; see "
            "clo_avatar_generation/schema/legacy_routes.md.",
        ],
    }

    manifest_payload: dict[str, object] = {
        "measurement_source": ctx.measurement_source,
        "measurement_source_path": str(ctx.measurement_source_path) if ctx.measurement_source_path else None,
        "active_field_filter": list(ctx.normalized_targets.get("active_field_filter", [])),
        "measurement_apply_mode_requested": ctx.measurement_apply_mode_input,
        "measurement_apply_mode_resolved": apply_mode,
    }

    if apply_mode == "avt_patch":
        avt_patch_payload, avt_patch_fields, skipped_avt_patch_fields = _build_avt_patch_payload(ctx)
        ctx.clo_payload_avt_patch_json = avt_patch_payload

        ctx.clo_payload_json["avt_patch_payload"] = {
            "unit": avt_patch_payload["unit"],
            "field_count": len(avt_patch_payload["field_values"]),
            "field_names": avt_patch_fields,
            "skipped_requested_fields": skipped_avt_patch_fields,
        }
        manifest_payload.update({
            "avt_patch_unit": avt_patch_payload["unit"],
            "avt_patch_field_names": avt_patch_fields,
            "avt_patch_field_indexes": avt_patch_payload["field_indexes"],
            "avt_patch_field_values": avt_patch_payload["field_values"],
            "skipped_avt_patch_fields": skipped_avt_patch_fields,
            "avt_patch_status": "avt_patch_payload_uses_verified_feature_indexes_for_supported_fields_only",
        })
        ctx.logger.info("Built AVT patch payload with %d field(s)", len(avt_patch_fields))
    elif apply_mode == "avatar_properties":
        property_payload, property_keys, skipped_property_fields = _build_property_payload(ctx)
        ctx.clo_payload_property_json = property_payload

        ctx.clo_payload_json["property_payload"] = {
            "avatar_index": property_payload["avatar_index"],
            "unit": property_payload["unit"],
            "property_count": len(property_payload["properties"]),
            "property_keys": property_keys,
            "skipped_requested_fields": skipped_property_fields,
        }
        manifest_payload.update({
            "property_unit": property_payload["unit"],
            "property_keys": property_keys,
            "property_values": property_payload["properties"],
            "skipped_property_fields": skipped_property_fields,
            "property_schema_status": (
                "property_payload_uses_contract_property_keys_and_cm_values_for_supported_fields_only"
            ),
        })
        ctx.logger.info("Built avatar-properties payload with %d propert(y/ies)", len(property_keys))
    else:
        # clo_payload.bridge.csv stays a real file: CLO's /import-avatar-measurements
        # endpoint reads it from disk by path, unlike the avt_patch/properties payloads
        # above, which are passed to CLO by value (inline JSON body / patched into the
        # .avt binary), never by a file path CLO itself opens.
        csv_manifest = _build_csv_bridge(ctx)
        ctx.clo_payload_json["bridge_payload"] = {
            "path": "clo_payload.bridge.csv",
            "bridge_strategy": csv_manifest["bridge_strategy"],
        }
        manifest_payload.update(csv_manifest)
        ctx.logger.info("Wrote clo_payload.bridge.csv (strategy=%s)", csv_manifest["bridge_strategy"])

    ctx.log_json("clo_payload", ctx.clo_payload_json)
    ctx.log_json("clo_payload_manifest", manifest_payload)
    return True
