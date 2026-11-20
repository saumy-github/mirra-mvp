"""Step 3: load and validate measurements from the job snapshot, an explicit file, or MongoDB."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .context import Step1Context
from .field_contract import get_v1_fields_for_gender


MEASUREMENT_RANGES = {
    "height_cm": (120, 230),
    "weight_kg": (30, 250),
    "shoulder_width_cm": (20, 80),
    "chest_circumference_cm": (50, 180),
    "waist_circumference_cm": (40, 220),
    "hip_circumference_cm": (50, 220),
    "leg_length_cm": (40, 140),
    "bust_circumference_cm": (50, 180),
    "under_bust_circumference_cm": (45, 170),
}


def _sanitize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        out[key] = value.isoformat() if isinstance(value, datetime) else value
    return out


def _load_measurement_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Measurement JSON is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Measurement JSON must contain an object at the top level: {path}")
    return payload


def _fetch_from_mongo(ctx: Step1Context) -> tuple[dict[str, Any], str]:
    try:
        from mirra_measurements.db import (
            get_measurements_collection,
            get_user_measurements_collection,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MongoDB dependencies are not available in this Python environment. Run the pipeline "
            "inside the repo virtual environment, or pass --measurement-file."
        ) from exc

    try:
        doc = get_user_measurements_collection().find_one({"user_id": ctx.user_id})
        if doc is not None:
            return doc, "mongodb:user_measurements"
        doc = get_measurements_collection().find_one({"user_id": ctx.user_id})
    except Exception as exc:
        raise RuntimeError(
            f"Could not read measurements for user_id={ctx.user_id} from MongoDB: {exc}"
        ) from exc

    if doc is None:
        raise ValueError(f"No measurements found for user_id: {ctx.user_id}")
    ctx.warnings.append(
        f"Measurements for {ctx.user_id} came from the legacy `measurements` collection, "
        "not `user_measurements`."
    )
    ctx.logger.warning("Using the legacy `measurements` collection for user_id=%s", ctx.user_id)
    return doc, "mongodb:measurements"


def _validate_required_fields(doc: dict[str, Any]) -> None:
    gender = str(doc.get("gender", "")).strip().lower()
    if gender != "male":
        raise ValueError(
            f"Step-1 CLO avatar generation currently supports male only, got gender={gender!r}"
        )

    missing = [
        field["mongo_field"]
        for field in get_v1_fields_for_gender(gender)
        if field.get("mongo_field") and doc.get(field["mongo_field"]) is None
    ]
    if missing:
        raise ValueError(f"Missing required measurement fields: {', '.join(sorted(missing))}")


def _validate_ranges(doc: dict[str, Any]) -> None:
    out_of_range: list[str] = []
    for field_name, (minimum, maximum) in MEASUREMENT_RANGES.items():
        value = doc.get(field_name)
        if value is None:
            continue
        numeric_value = float(value)
        if numeric_value < minimum or numeric_value > maximum:
            out_of_range.append(f"{field_name}={numeric_value:.2f} (expected {minimum}-{maximum})")
    if out_of_range:
        raise ValueError(
            "Measurement values are outside the current sanity-check ranges: " + "; ".join(out_of_range)
        )


def run(ctx: Step1Context) -> bool:
    ctx.logger.info("Fetching measurements for user_id=%s", ctx.user_id)
    source_path: Path | None = None

    if ctx.measurement_doc_input is not None:
        doc, source = dict(ctx.measurement_doc_input), "job_snapshot"
    elif ctx.measurement_file_input:
        source_path = Path(ctx.measurement_file_input).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Measurement JSON file not found: {source_path}")
        doc, source = _load_measurement_json(source_path), "json_file"
        ctx.warnings.append(f"Measurements came from an explicit file, not the database: {source_path}")
        ctx.logger.warning("Using an explicit measurement file: %s", source_path)
    else:
        doc, source = _fetch_from_mongo(ctx)

    ctx.logger.info("Measurement source: %s%s", source, f" ({source_path})" if source_path else "")

    ctx.measurement_source = source
    ctx.measurement_source_path = source_path
    ctx.mongo_doc = doc
    ctx.mongo_snapshot = _sanitize_doc(doc)
    ctx.mongo_snapshot["_source"] = source
    if source_path is not None:
        ctx.mongo_snapshot["_source_path"] = str(source_path)

    ctx.input_payload["measurement_source"] = source
    ctx.input_payload["measurement_source_path"] = str(source_path) if source_path else None
    # Logged before validation so a rejected document is still recorded.
    ctx.log_json("mongo_snapshot", ctx.mongo_snapshot)

    _validate_required_fields(doc)
    _validate_ranges(doc)
    ctx.logger.info("Measurement validation passed (gender=%s)", str(doc.get("gender", "")).strip().lower())
    return True
