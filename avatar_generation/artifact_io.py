"""Write pipeline artifacts to JSON files with deterministic formatting."""

import json
import os
from typing import Any
from datetime import datetime, timezone
from functools import singledispatch
import numpy as np

from avatar_generation.run_manifest import RunIdentity, get_inputs_json_path, get_values_json_path, get_run_dir
from avatar_generation.artifact_schema import InputsSchema, ValuesSchema


@singledispatch
def _normalize_for_json(value: Any) -> Any:
    return value


@_normalize_for_json.register(dict)
def _(value: dict) -> dict:
    return {k: _normalize_for_json(v) for k, v in value.items()}


@_normalize_for_json.register(list)
def _(value: list) -> list:
    return [_normalize_for_json(v) for v in value]


@_normalize_for_json.register(tuple)
def _(value: tuple) -> list:
    return [_normalize_for_json(v) for v in value]


@_normalize_for_json.register(np.ndarray)
def _(value: np.ndarray) -> list:
    return value.tolist()


@_normalize_for_json.register(np.generic)
def _(value: np.generic) -> Any:
    return value.item()


# Write input.json artifact to avatar_generation/output/<run_id>/
def write_inputs_json(run_id: RunIdentity, inputs_data: InputsSchema) -> str:
    os.makedirs(get_run_dir(run_id), exist_ok=True)

    file_path = get_inputs_json_path(run_id)
    normalized_inputs = _normalize_for_json(inputs_data)

    with open(file_path, 'w', encoding='utf-8') as file_handle:
        json.dump(normalized_inputs, file_handle, indent=2, sort_keys=True, ensure_ascii=False)
        file_handle.write('\n')

    return file_path


# Write output.json artifact to avatar_generation/output/<run_id>/
def write_values_json(run_id: RunIdentity, values_data: ValuesSchema) -> str:
    os.makedirs(get_run_dir(run_id), exist_ok=True)

    if values_data['status'] not in ['passed', 'failed']:
        raise ValueError(f"Invalid status: {values_data['status']}. Must be 'passed' or 'failed'.")

    file_path = get_values_json_path(run_id)
    normalized_values = _normalize_for_json(values_data)

    with open(file_path, 'w', encoding='utf-8') as file_handle:
        json.dump(normalized_values, file_handle, indent=2, sort_keys=True, ensure_ascii=False)
        file_handle.write('\n')

    return file_path


def get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
