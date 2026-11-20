"""Build CLO avatar-size (.avs) files: template plus six measurement floats and predicted derived floats."""

from __future__ import annotations

import json
import struct
from pathlib import Path


INPUT_DIR = Path(__file__).resolve().parents[1] / "input"
TEMPLATE_PATH = INPUT_DIR / "CLO_Male_Default.avs"
DERIVED_MODEL_PATH = INPUT_DIR / "avs_derived_model.json"
FEATURE_COUNT = 57
FEATURE_MARKER = b"listFeatureValues"


def _float_block_offset(data: bytes) -> int:
    """Byte offset of the 57-float block (height first), found after the marker."""
    marker = data.find(FEATURE_MARKER)
    if marker < 0:
        raise ValueError("listFeatureValues marker not found in .avs")
    for offset in range(marker, min(marker + 400, len(data) - 8)):
        height = struct.unpack_from("<f", data, offset)[0]
        second = struct.unpack_from("<f", data, offset + 4)[0]
        if 100.0 < height < 250.0 and 30.0 < second < 200.0:
            return offset
    raise ValueError("Could not locate the feature float block in .avs")


def read_avs_features(avs_path: Path) -> list[float]:
    data = Path(avs_path).read_bytes()
    offset = _float_block_offset(data)
    return [struct.unpack_from("<f", data, offset + 4 * i)[0] for i in range(FEATURE_COUNT)]


def load_derived_model() -> dict | None:
    if not DERIVED_MODEL_PATH.exists():
        return None
    return json.loads(DERIVED_MODEL_PATH.read_text(encoding="utf-8"))


def _predict_derived(model: dict, input_values: list[float]) -> list[float]:
    mean, std = model["mean"], model["std"]
    scaled = [(value - m) / s for value, m, s in zip(input_values, mean, std)]
    features = [1.0] + scaled
    weights = model["weights"]  # (1 + n_inputs) rows x n_derived columns
    return [
        sum(features[row] * weights[row][col] for row in range(len(features)))
        for col in range(len(model["derived_indexes"]))
    ]


def build_avs(
    template_path: Path,
    output_path: Path,
    field_targets: dict[str, float],
    field_indexes: dict[str, int],
    use_derived_model: bool = True,
) -> dict[str, object]:
    """Write an .avs from the template with the requested fields patched in (cm)."""
    supported = {name: float(value) for name, value in field_targets.items() if name in field_indexes}
    unsupported = sorted(name for name in field_targets if name not in field_indexes)
    if not supported:
        raise ValueError("No avs-supported fields were requested")

    data = bytearray(Path(template_path).read_bytes())
    offset = _float_block_offset(bytes(data))
    base_values = [struct.unpack_from("<f", data, offset + 4 * i)[0] for i in range(FEATURE_COUNT)]

    model = load_derived_model() if use_derived_model else None
    derived_applied = 0
    if model is not None:
        # Inputs the request doesn't cover keep the template value.
        by_index = {int(field_indexes[name]): value for name, value in supported.items()}
        inputs = [by_index.get(int(i), base_values[int(i)]) for i in model["input_indexes"]]
        for index, value in zip(model["derived_indexes"], _predict_derived(model, inputs)):
            struct.pack_into("<f", data, offset + 4 * int(index), float(value))
            derived_applied += 1

    for name, value in supported.items():
        struct.pack_into("<f", data, offset + 4 * int(field_indexes[name]), value)

    Path(output_path).write_bytes(bytes(data))
    patched_values = read_avs_features(output_path)

    return {
        "template_path": str(template_path),
        "output_path": str(output_path),
        "float_block_offset": offset,
        "supported_requested_fields": supported,
        "unsupported_requested_fields": unsupported,
        "field_indexes_used": {name: int(field_indexes[name]) for name in supported},
        "base_values": {name: base_values[int(field_indexes[name])] for name in supported},
        "patched_values": {name: patched_values[int(field_indexes[name])] for name in supported},
        "derived_model_used": model is not None,
        "derived_floats_predicted": derived_applied,
        "derived_model_training": model.get("training") if model else None,
    }
