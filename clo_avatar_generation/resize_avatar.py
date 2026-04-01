"""Experimental convenience runner for resizing a loaded CLO-native avatar.

This does not use a public per-measurement setter API from CLO. Instead it:

1. starts from the current repo-local measurement CSV template
2. overwrites selected measurement values
3. writes a temporary CSV into clo_avatar_generation/output
4. sends that CSV to the existing /import-avatar-measurements endpoint

Status:
- experimental
- depends on the currently assumed CSV schema
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

from .adapters.clo_native_client import CLONativeClient


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_CSV = PACKAGE_ROOT / "schema" / "measurement_template_unconfirmed.csv"
OUTPUT_ROOT = PACKAGE_ROOT / "output"


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _read_single_row_csv(path: Path) -> tuple[list[str], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise ValueError(f"Measurement CSV must contain a header row and one value row: {path}")
    return rows[0], rows[1]


def _write_single_row_csv(path: Path, headers: list[str], values: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(values)
    return path


def _apply_updates(headers: list[str], values: list[str], updates: dict[str, float | None]) -> list[str]:
    updated = list(values)
    for field_name, field_value in updates.items():
        if field_value is None:
            continue
        try:
            idx = headers.index(field_name)
        except ValueError:
            continue
        updated[idx] = str(field_value)
    return updated


def build_measurement_csv(
    source_csv_path: str | Path | None = None,
    *,
    total_height: float | None = None,
    weight: float | None = None,
    waist: float | None = None,
    low_hip: float | None = None,
    inseam: float | None = None,
    bust: float | None = None,
    under_bust: float | None = None,
    neck_base: float | None = None,
    bicep: float | None = None,
    shoulder: float | None = None,
    arm: float | None = None,
) -> Path:
    """Create a temporary measurement CSV from the repo-local starter template."""

    template_path = Path(source_csv_path) if source_csv_path else DEFAULT_TEMPLATE_CSV
    headers, values = _read_single_row_csv(template_path)
    updated_values = _apply_updates(
        headers,
        values,
        {
            "Total Height": total_height,
            "Weight": weight,
            "Waist": waist,
            "Low Hip": low_hip,
            "Inseam": inseam,
            "Bust": bust,
            "Under Bust": under_bust,
            "Neck Base": neck_base,
            "Bicep": bicep,
            "Across Shoulder (Curvilinear)": shoulder,
            "Arm": arm,
        },
    )
    output_path = OUTPUT_ROOT / f"avatar_measurements__{_utc_stamp()}.csv"
    return _write_single_row_csv(output_path, headers, updated_values)


def import_measurements_into_loaded_avatar(csv_path: str | Path, template_path: str | Path | None = None) -> dict:
    client = CLONativeClient()
    result = client.import_avatar_measurements(
        csv_path=csv_path,
        template_path=template_path,
    )
    client.wait_for_queue(timeout=30)
    debug = client.get_native_avatar_debug()
    return {
        "csv_path": str(Path(csv_path)),
        "template_path": str(Path(template_path)) if template_path else None,
        "result": result,
        "native_debug": debug,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Experimental helper to resize a loaded CLO-native avatar via measurement CSV import."
    )
    parser.add_argument("--csv-template", default=None, help="Optional source CSV template.")
    parser.add_argument("--template-path", default=None, help="Optional .avt path for CLO's ImportAvatarMeasurement route.")
    parser.add_argument("--total-height", type=float, default=None)
    parser.add_argument("--weight", type=float, default=None)
    parser.add_argument("--waist", type=float, default=None)
    parser.add_argument("--low-hip", type=float, default=None)
    parser.add_argument("--inseam", type=float, default=None)
    parser.add_argument("--bust", type=float, default=None)
    parser.add_argument("--under-bust", type=float, default=None)
    parser.add_argument("--neck-base", type=float, default=None)
    parser.add_argument("--bicep", type=float, default=None)
    parser.add_argument("--shoulder", type=float, default=None)
    parser.add_argument("--arm", type=float, default=None)
    args = parser.parse_args()

    csv_path = build_measurement_csv(
        source_csv_path=args.csv_template,
        total_height=args.total_height,
        weight=args.weight,
        waist=args.waist,
        low_hip=args.low_hip,
        inseam=args.inseam,
        bust=args.bust,
        under_bust=args.under_bust,
        neck_base=args.neck_base,
        bicep=args.bicep,
        shoulder=args.shoulder,
        arm=args.arm,
    )
    print(f"Wrote temporary measurement CSV: {csv_path}")

    result = import_measurements_into_loaded_avatar(
        csv_path=csv_path,
        template_path=args.template_path,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
