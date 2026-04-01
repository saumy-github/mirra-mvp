"""Step 3: fetch and validate the user measurement snapshot from MongoDB."""

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

REPO_ROOT = Path(__file__).resolve().parents[2]
AVATAR_GENERATION_OUTPUT_ROOT = REPO_ROOT / "avatar_generation" / "output"


def _sanitize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _load_latest_local_snapshot(user_id: str) -> dict[str, Any] | None:
    if not AVATAR_GENERATION_OUTPUT_ROOT.exists():
        return None

    candidates = sorted(
        [
            path for path in AVATAR_GENERATION_OUTPUT_ROOT.iterdir()
            if path.is_dir() and path.name.startswith(f"{user_id}-")
        ]
    )
    for path in reversed(candidates):
        input_json_path = path / "input.json"
        if not input_json_path.exists():
            continue
        try:
            payload = json.loads(input_json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        mongo_snapshot = payload.get("mongo_snapshot")
        if isinstance(mongo_snapshot, dict):
            return mongo_snapshot
    return None


def _validate_required_fields(doc: dict[str, Any]) -> None:
    gender = str(doc.get("gender", "")).strip().lower()
    if gender != "male":
        raise ValueError(
            f"Step-1 CLO avatar generation currently supports male only, got gender={gender!r}"
        )

    missing: list[str] = []
    for field in get_v1_fields_for_gender(gender):
        mongo_field = field.get("mongo_field")
        if not mongo_field:
            continue
        if doc.get(mongo_field) is None:
            missing.append(mongo_field)

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
            out_of_range.append(
                f"{field_name}={numeric_value:.2f} (expected {minimum}-{maximum})"
            )
    if out_of_range:
        raise ValueError(
            "Measurement values are outside the current sanity-check ranges: "
            + "; ".join(out_of_range)
        )


def run(ctx: Step1Context) -> bool:
    try:
        from mirra_measurements.db import get_measurements_collection
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MongoDB dependencies are not available in this Python environment. "
            "Run the pipeline inside the repo virtual environment."
        ) from exc

    doc: dict[str, Any] | None = None
    source = "mongodb"
    try:
        collection = get_measurements_collection()
        doc = collection.find_one({"user_id": ctx.user_id})
    except Exception as exc:
        local_snapshot = _load_latest_local_snapshot(ctx.user_id)
        if local_snapshot is None:
            raise RuntimeError(
                "Failed to fetch measurements from MongoDB and no local snapshot fallback was found."
            ) from exc
        ctx.warnings.append(
            "MongoDB fetch failed; using the latest avatar_generation input.json snapshot "
            f"for user {ctx.user_id} instead."
        )
        doc = local_snapshot
        source = "avatar_generation_snapshot"

    if doc is None:
        local_snapshot = _load_latest_local_snapshot(ctx.user_id)
        if local_snapshot is None:
            raise ValueError(f"No measurements found for user_id: {ctx.user_id}")
        ctx.warnings.append(
            "No live MongoDB document was found; using the latest avatar_generation input.json snapshot "
            f"for user {ctx.user_id} instead."
        )
        doc = local_snapshot
        source = "avatar_generation_snapshot"

    _validate_required_fields(doc)
    _validate_ranges(doc)

    ctx.mongo_doc = doc
    ctx.mongo_snapshot = _sanitize_doc(doc)
    ctx.mongo_snapshot["_source"] = source
    ctx.write_json("mongo_snapshot.json", ctx.mongo_snapshot)
    return True
