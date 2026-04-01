"""Step 6: build human-readable and CLO-facing payload artifacts."""

from __future__ import annotations

import csv
from pathlib import Path

from .context import Step1Context
from .field_contract import get_v1_fields_for_gender


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


def run(ctx: Step1Context) -> bool:
    headers, values = _build_bridge_headers_and_values(ctx)

    ctx.clo_payload_json = {
        "preferred_clo_payload": ctx.contract.get("preferred_clo_payload", "avs"),
        "actual_runtime_bridge": "csv",
        "base_avatar": ctx.base_avatar_metadata,
        "normalized_targets": ctx.normalized_targets,
        "files_sent_to_clo": {
            "base_avatar_avt": str(ctx.base_avatar_path) if ctx.base_avatar_path else None,
            "measurement_bridge_csv": "clo_payload.bridge.csv",
        },
        "notes": [
            "The product-side human-readable contract remains JSON.",
            "The runtime currently uses an internal CSV bridge because the plugin exposes a measurement-import endpoint for CSV, not a direct AVS-import endpoint.",
            "All outgoing linear values are rounded to two decimals. Weight remains in kg.",
        ],
    }
    ctx.clo_payload_json_path = ctx.write_json("clo_payload.json", ctx.clo_payload_json)

    bridge_path = ctx.artifact_path("clo_payload.bridge.csv")
    with bridge_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(values)
    ctx.clo_payload_bridge_path = bridge_path

    manifest_payload = {
        "headers": headers,
        "values": values,
        "bridge_path": str(bridge_path),
        "schema_status": "runtime_bridge_unverified_against_direct_clo_export",
    }
    ctx.write_json("clo_payload_manifest.json", manifest_payload)
    return True

