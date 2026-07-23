"""Helpers for the Step-1 field contract."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "schema" / "step1_field_contract.json"


@lru_cache(maxsize=1)
def load_field_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def get_v1_fields_for_gender(gender: str) -> list[dict[str, Any]]:
    contract = load_field_contract()
    fields: list[dict[str, Any]] = []
    for entry in contract.get("fields", []):
        if not entry.get("included_in_v1", False):
            continue
        genders = set(entry.get("genders", []))
        if gender not in genders:
            continue
        fields.append(entry)
    return fields


def get_v1_property_fields_for_gender(gender: str) -> list[dict[str, Any]]:
    return [
        entry
        for entry in get_v1_fields_for_gender(gender)
        if str(entry.get("property_key", "")).strip()
    ]


def get_v1_avt_patch_fields_for_gender(gender: str) -> list[dict[str, Any]]:
    return [
        entry
        for entry in get_v1_fields_for_gender(gender)
        if entry.get("avt_feature_index") is not None
    ]


def get_round_decimals() -> int:
    contract = load_field_contract()
    return int(contract.get("round_decimals", 2))


def get_default_base_avatar() -> Path:
    contract = load_field_contract()
    relative = contract.get("default_base_avatar", "clo_avatar_generation/input/base-1.avt")
    return Path(relative)


def get_measurement_bridge_template_csv() -> Path | None:
    contract = load_field_contract()
    relative = contract.get("measurement_bridge_template_csv")
    if not relative:
        return None
    return Path(relative)

