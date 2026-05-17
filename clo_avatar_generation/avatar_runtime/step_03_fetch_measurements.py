"""Step 3: fetch and validate the user measurement snapshot from JSON or MongoDB."""

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
CLO_AVATAR_GENERATION_OUTPUT_ROOT = REPO_ROOT / "clo_avatar_generation" / "output"
CLO_AVATAR_GENERATION_INPUT_ROOT = REPO_ROOT / "clo_avatar_generation" / "input"


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
    if not CLO_AVATAR_GENERATION_OUTPUT_ROOT.exists():
        return None

    candidates = sorted(
        [
            path for path in CLO_AVATAR_GENERATION_OUTPUT_ROOT.iterdir()
            if path.is_dir() and path.name.startswith(f"{user_id}-")
        ]
    )
    for path in reversed(candidates):
        mongo_snapshot_path = path / "mongo_snapshot.json"
        if mongo_snapshot_path.exists():
            try:
                payload = json.loads(mongo_snapshot_path.read_text(encoding="utf-8"))
            except Exception:
                payload = None
            if isinstance(payload, dict):
                return payload

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


def _default_measurement_json_path(user_id: str) -> Path:
    return CLO_AVATAR_GENERATION_INPUT_ROOT / f"{user_id}.measurements.json"


def _load_measurement_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Measurement JSON is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Measurement JSON must contain an object at the top level: {path}")
    return payload


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
    doc: dict[str, Any] | None = None
    source = "mongodb"
    source_path: Path | None = None

    measurement_json_path: Path | None = None
    if ctx.measurement_file_input:
        measurement_json_path = Path(ctx.measurement_file_input).expanduser().resolve()
        if not measurement_json_path.exists():
            raise FileNotFoundError(f"Measurement JSON file not found: {measurement_json_path}")
    else:
        default_json_path = _default_measurement_json_path(ctx.user_id)
        if default_json_path.exists():
            measurement_json_path = default_json_path.resolve()

    if measurement_json_path is not None:
        doc = _load_measurement_json(measurement_json_path)
        source = "json_file"
        source_path = measurement_json_path
    else:
        try:
            from mirra_measurements.db import get_measurements_collection
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "MongoDB dependencies are not available in this Python environment and no JSON measurement "
                "file was supplied. Run the pipeline inside the repo virtual environment or pass "
                "--measurement-file."
            ) from exc

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
                "MongoDB fetch failed; using the latest clo_avatar_generation snapshot "
                f"for user {ctx.user_id} instead."
            )
            doc = local_snapshot
            source = "clo_avatar_generation_snapshot"

        if doc is None:
            local_snapshot = _load_latest_local_snapshot(ctx.user_id)
            if local_snapshot is None:
                raise ValueError(f"No measurements found for user_id: {ctx.user_id}")
            ctx.warnings.append(
                "No live MongoDB document was found; using the latest clo_avatar_generation snapshot "
                f"for user {ctx.user_id} instead."
            )
            doc = local_snapshot
            source = "clo_avatar_generation_snapshot"

    _validate_required_fields(doc)
    _validate_ranges(doc)

    ctx.measurement_source = source
    ctx.measurement_source_path = source_path
    ctx.mongo_doc = doc
    ctx.mongo_snapshot = _sanitize_doc(doc)
    ctx.mongo_snapshot["_source"] = source
    if source_path is not None:
        ctx.mongo_snapshot["_source_path"] = str(source_path)

    ctx.input_payload["measurement_source"] = source
    ctx.input_payload["measurement_source_path"] = str(source_path) if source_path else None
    ctx.write_json("input.json", ctx.input_payload)
    ctx.write_json("mongo_snapshot.json", ctx.mongo_snapshot)
    return True
