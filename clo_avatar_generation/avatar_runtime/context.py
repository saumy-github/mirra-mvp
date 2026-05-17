"""Shared context object for the Step-1 CLO avatar pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import CLORestClient
from .field_contract import load_field_contract
from .run_manifest import RunIdentity


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class Step1Context:
    """Shared mutable state for the Step-1 avatar-generation workflow."""

    user_id: str
    requested_run_number: int | None = None
    base_avatar_path_input: str | None = None
    measurement_file_input: str | None = None
    measurement_apply_mode_input: str = "auto"
    active_field_filters: list[str] = field(default_factory=list)
    interactive: bool = True
    client: CLORestClient = field(default_factory=CLORestClient)
    contract: dict[str, Any] = field(default_factory=load_field_contract)

    run_identity: RunIdentity | None = None
    run_dir: Path | None = None
    status: str = "initialized"

    health_result: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    input_payload: dict[str, Any] = field(default_factory=dict)

    measurement_source: str | None = None
    measurement_source_path: Path | None = None
    mongo_doc: dict[str, Any] = field(default_factory=dict)
    mongo_snapshot: dict[str, Any] = field(default_factory=dict)
    base_avatar_path: Path | None = None
    base_avatar_metadata: dict[str, Any] = field(default_factory=dict)
    normalized_targets: dict[str, Any] = field(default_factory=dict)
    resolved_measurement_apply_mode: str | None = None

    clo_payload_json: dict[str, Any] = field(default_factory=dict)
    clo_payload_json_path: Path | None = None
    clo_payload_bridge_path: Path | None = None
    clo_payload_property_json: dict[str, Any] = field(default_factory=dict)
    clo_payload_property_path: Path | None = None
    clo_payload_avt_patch_json: dict[str, Any] = field(default_factory=dict)
    clo_payload_avt_patch_path: Path | None = None

    import_result: dict[str, Any] = field(default_factory=dict)
    apply_result: dict[str, Any] = field(default_factory=dict)
    readback_measurements: dict[str, Any] = field(default_factory=dict)
    error_report: dict[str, Any] = field(default_factory=dict)
    output_payload: dict[str, Any] = field(default_factory=dict)

    exported_project_path: Path | None = None
    direct_avatar_export_path: Path | None = None
    extracted_avatar_path: Path | None = None
    extracted_artifacts: dict[str, str] = field(default_factory=dict)

    step_results: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def require_run_dir(self) -> Path:
        if self.run_dir is None:
            raise RuntimeError("Run directory is not initialized yet")
        return self.run_dir

    def artifact_path(self, name: str) -> Path:
        return self.require_run_dir() / name

    def write_json(self, name: str, payload: dict[str, Any]) -> Path:
        out_path = self.artifact_path(name)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out_path
