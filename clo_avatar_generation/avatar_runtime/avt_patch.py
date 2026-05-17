"""Helpers for patching and verifying CLO avatar measurements inside .avt files."""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path


LIST_FEATURE_VALUES_MARKER = b"listFeatureValues"
LIST_FEATURE_VALUES_OFFSET = 273
LIST_FEATURE_VALUES_COUNT = 57
VALUE_TOLERANCE = 0.05


def _split_avt_payload(avt_path: Path) -> tuple[bytes, list[tuple[zipfile.ZipInfo, bytes]]]:
    raw = avt_path.read_bytes()
    zip_start = raw.find(b"PK\x03\x04")
    if zip_start < 0:
        raise ValueError(f"Embedded zip header not found in AVT: {avt_path}")

    members: list[tuple[zipfile.ZipInfo, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(raw[zip_start:]), "r") as archive:
        for info in archive.infolist():
            members.append((info, archive.read(info.filename)))
    return raw[:zip_start], members


def _write_avt_payload(
    output_path: Path,
    prefix: bytes,
    members: list[tuple[zipfile.ZipInfo, bytes]],
) -> None:
    out_buffer = io.BytesIO()
    with zipfile.ZipFile(out_buffer, "w") as archive:
        for info, data in members:
            new_info = zipfile.ZipInfo(info.filename)
            new_info.date_time = info.date_time
            new_info.compress_type = info.compress_type
            new_info.comment = info.comment
            new_info.extra = info.extra
            new_info.create_system = info.create_system
            new_info.external_attr = info.external_attr
            new_info.internal_attr = info.internal_attr
            new_info.flag_bits = info.flag_bits
            archive.writestr(new_info, data)
    output_path.write_bytes(prefix + out_buffer.getvalue())


def _find_dan_member_index(members: list[tuple[zipfile.ZipInfo, bytes]]) -> int:
    for index, (info, _) in enumerate(members):
        if info.filename.endswith(".dan"):
            return index
    raise ValueError("No .dan payload found inside AVT archive")


def _feature_block_start(dan_bytes: bytes) -> int:
    marker_index = dan_bytes.find(LIST_FEATURE_VALUES_MARKER)
    if marker_index < 0:
        raise ValueError("listFeatureValues marker not found in AVT .dan payload")
    return marker_index + len(LIST_FEATURE_VALUES_MARKER) + LIST_FEATURE_VALUES_OFFSET


def read_feature_values(avt_path: Path) -> list[float]:
    _, members = _split_avt_payload(avt_path)
    dan_index = _find_dan_member_index(members)
    _, dan_bytes = members[dan_index]
    start = _feature_block_start(dan_bytes)
    return [
        struct.unpack_from("<f", dan_bytes, start + feature_index * 4)[0]
        for feature_index in range(LIST_FEATURE_VALUES_COUNT)
    ]


def read_field_values(avt_path: Path, field_index_map: dict[str, int]) -> dict[str, float]:
    feature_values = read_feature_values(avt_path)
    return {
        field_name: feature_values[feature_index]
        for field_name, feature_index in field_index_map.items()
        if 0 <= int(feature_index) < len(feature_values)
    }


def build_patched_avatar(
    base_avt_path: Path,
    output_avt_path: Path,
    field_targets: dict[str, float],
    field_index_map: dict[str, int],
) -> dict[str, object]:
    supported_targets = {
        field_name: float(field_targets[field_name])
        for field_name in field_targets
        if field_name in field_index_map
    }
    unsupported_fields = sorted(
        field_name for field_name in field_targets if field_name not in field_index_map
    )
    if not supported_targets:
        raise ValueError("No AVT-patch-supported fields were requested")

    prefix, members = _split_avt_payload(base_avt_path)
    dan_index = _find_dan_member_index(members)
    dan_info, dan_bytes = members[dan_index]
    dan_buffer = bytearray(dan_bytes)
    feature_block_start = _feature_block_start(dan_buffer)

    base_values = read_field_values(
        base_avt_path,
        {field_name: field_index_map[field_name] for field_name in supported_targets},
    )

    for field_name, target_value in supported_targets.items():
        feature_index = int(field_index_map[field_name])
        struct.pack_into("<f", dan_buffer, feature_block_start + feature_index * 4, target_value)

    members[dan_index] = (dan_info, bytes(dan_buffer))
    _write_avt_payload(output_avt_path, prefix, members)

    patched_values = read_field_values(
        output_avt_path,
        {field_name: field_index_map[field_name] for field_name in supported_targets},
    )

    return {
        "base_avatar_path": str(base_avt_path),
        "output_avatar_path": str(output_avt_path),
        "supported_requested_field_count": len(supported_targets),
        "supported_requested_fields": supported_targets,
        "unsupported_requested_fields": unsupported_fields,
        "field_indexes_used": {
            field_name: int(field_index_map[field_name]) for field_name in supported_targets
        },
        "base_values": base_values,
        "patched_values": patched_values,
    }


def verify_avatar_fields(
    *,
    base_avt_path: Path,
    actual_avt_path: Path,
    requested_fields: dict[str, float],
    field_index_map: dict[str, int],
    tolerance: float = VALUE_TOLERANCE,
) -> dict[str, object]:
    supported_requested = {
        field_name: float(requested_fields[field_name])
        for field_name in requested_fields
        if field_name in field_index_map
    }
    unsupported_requested = sorted(
        field_name for field_name in requested_fields if field_name not in field_index_map
    )

    if not supported_requested:
        return {
            "available": False,
            "verification_pass": False,
            "reason": "No requested fields have verified AVT feature indexes yet.",
            "supported_requested_fields": {},
            "unsupported_requested_fields": unsupported_requested,
            "per_field": {},
        }

    relevant_index_map = {
        field_name: int(field_index_map[field_name]) for field_name in supported_requested
    }
    base_values = read_field_values(base_avt_path, relevant_index_map)
    achieved_values = read_field_values(actual_avt_path, relevant_index_map)

    per_field: dict[str, object] = {}
    matched_requested_fields: list[str] = []
    changed_from_base_fields: list[str] = []

    for field_name, requested_value in supported_requested.items():
        base_value = float(base_values[field_name])
        achieved_value = float(achieved_values[field_name])
        changed_from_base = abs(achieved_value - base_value) > tolerance
        matches_requested = abs(achieved_value - requested_value) <= tolerance
        if changed_from_base:
            changed_from_base_fields.append(field_name)
        if matches_requested:
            matched_requested_fields.append(field_name)
        per_field[field_name] = {
            "feature_index": int(relevant_index_map[field_name]),
            "base_value": base_value,
            "requested_value": requested_value,
            "achieved_value": achieved_value,
            "changed_from_base": changed_from_base,
            "matches_requested": matches_requested,
            "delta_from_base": achieved_value - base_value,
            "delta_from_requested": achieved_value - requested_value,
        }

    verification_pass = all(
        field_result["changed_from_base"] and field_result["matches_requested"]
        for field_result in per_field.values()
    )

    return {
        "available": True,
        "verification_pass": verification_pass,
        "base_avatar_path": str(base_avt_path),
        "actual_avatar_path": str(actual_avt_path),
        "tolerance": tolerance,
        "supported_requested_fields": supported_requested,
        "unsupported_requested_fields": unsupported_requested,
        "matched_requested_fields": matched_requested_fields,
        "changed_from_base_fields": changed_from_base_fields,
        "per_field": per_field,
        "reason": None
        if verification_pass
        else "Saved avatar measurements did not fully match the requested AVT-backed targets.",
    }
