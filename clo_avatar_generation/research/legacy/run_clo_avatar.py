"""Phase 4 runner scaffold for the isolated CLO-native avatar path.

This runner creates a self-contained experimental run folder and writes the
bundle metadata needed for later phases. It does not yet connect to CLO.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...avatar_setup.import_bundle import build_import_bundle_payload, write_import_bundle
from ...avatar_setup.measurement_mapping import get_family_mapping_profile
from ...avatar_setup.run_manifest import CLONativeRunIdentity, get_output_root, get_run_dir
from ...avatar_setup.template_registry import list_template_candidates


def _next_run_number(user_id: str, family: str) -> int:
    output_root = get_output_root()
    output_root.mkdir(parents=True, exist_ok=True)
    prefix = f"{user_id}__{family}__"
    numbers: list[int] = []
    for path in output_root.iterdir():
        if not path.is_dir() or not path.name.startswith(prefix):
            continue
        try:
            numbers.append(int(path.name.rsplit("__", 1)[1]))
        except Exception:
            continue
    return (max(numbers) + 1) if numbers else 1


def _resolve_template(template_id: str):
    for candidate in list_template_candidates():
        if candidate.template_id == template_id:
            return candidate
    raise ValueError(f"Unknown template_id: {template_id}")


def _build_mapping_snapshot(family: str) -> dict:
    profile = get_family_mapping_profile(family)  # type: ignore[arg-type]
    return {
        "family": profile.family,
        "mappings": [
            {
                "mirra_field": item.mirra_field,
                "clo_target": item.clo_target,
                "status": item.status,
                "confidence": item.confidence,
                "notes": item.notes,
            }
            for item in profile.mappings
        ],
        "unresolved_questions": list(profile.unresolved_questions),
    }


def run_native_avatar_setup(user_id: str, family: str, template_id: str) -> Path:
    """Create one isolated CLO-native experimental run."""

    run_id = CLONativeRunIdentity(
        user_id=user_id,
        family=family,
        number=_next_run_number(user_id, family),
    )
    run_dir = Path(get_run_dir(run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    template = _resolve_template(template_id)
    source_measurements = {
        "user_id": user_id,
        "family": family,
        "note": "Source measurements are not pulled from existing DB logic in Phase 4.",
    }
    mapped_measurements = _build_mapping_snapshot(family)

    bundle_payload = build_import_bundle_payload(
        run_id=run_id,
        template=template,
        source_measurements=source_measurements,
        mapped_measurements=mapped_measurements,
    )
    bundle_path = write_import_bundle(run_id, bundle_payload)

    summary = {
        "run_id": run_id.run_id,
        "status": "initialized",
        "template_id": template.template_id,
        "bundle_path": str(bundle_path),
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    template_resolution = {
        "template_id": template.template_id,
        "display_name": template.display_name,
        "family": template.family,
        "source_mode": template.source_mode,
        "clo_version": template.clo_version,
        "avt_path": str(template.avt_path) if template.avt_path else None,
        "notes": template.notes,
    }
    bundle_dir = run_dir / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "template_resolution.json").write_text(
        json.dumps(template_resolution, indent=2),
        encoding="utf-8",
    )

    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an isolated CLO-native experiment run.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--family", required=True, choices=["male", "female"])
    parser.add_argument("--template-id", required=True)
    args = parser.parse_args()

    run_dir = run_native_avatar_setup(
        user_id=args.user_id,
        family=args.family,
        template_id=args.template_id,
    )
    print(f"Created CLO-native run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
