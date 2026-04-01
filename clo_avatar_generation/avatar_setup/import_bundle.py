"""Phase 4 import-bundle assembly for the CLO-native avatar experiment.

This module prepares a self-contained run folder describing:

1. the chosen CLO avatar template candidate
2. the source Mirra measurement payload
3. the mapped CLO measurement payload placeholder
4. the future file paths expected for CSV and related native-avatar inputs

It does not yet create the real CLO CSV or call the plugin.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .contracts import TemplateIdentity
from .run_manifest import CLONativeRunIdentity, get_run_dir


def _normalize(value: Any) -> Any:
    """Convert dataclasses and paths into JSON-safe values."""

    if is_dataclass(value):
        return {k: _normalize(v) for k, v in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def build_import_bundle_payload(
    run_id: CLONativeRunIdentity,
    template: TemplateIdentity,
    source_measurements: dict[str, Any],
    mapped_measurements: dict[str, Any],
) -> dict[str, Any]:
    """Create the JSON payload for one isolated CLO-native run bundle."""

    run_dir = Path(get_run_dir(run_id))

    return {
        "run_id": run_id.run_id,
        "template": _normalize(template),
        "source_measurements": _normalize(source_measurements),
        "mapped_measurements": _normalize(mapped_measurements),
        "planned_outputs": {
            "measurement_csv": str(run_dir / "bundle" / "avatar_measurements.csv"),
            "native_run_summary": str(run_dir / "run_summary.json"),
            "resolved_template_metadata": str(run_dir / "bundle" / "template_resolution.json"),
        },
        "status": "initialized",
    }


def write_import_bundle(
    run_id: CLONativeRunIdentity,
    payload: dict[str, Any],
) -> Path:
    """Write the import-bundle JSON into the run folder."""

    run_dir = Path(get_run_dir(run_id))
    bundle_dir = run_dir / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    out_path = bundle_dir / "import_bundle.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path

