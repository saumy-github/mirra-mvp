"""Helpers for canonical product_ingestion run folders."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

_HERE = Path(__file__).parent.resolve()
_RUN_RE = re.compile(r"^(c_[^-]+)-(s_[^-]+)-(\d{3})$")


def get_output_root(output_root: Optional[str | Path] = None) -> Path:
    """Return the canonical output root."""
    base = Path(output_root) if output_root else (_HERE / "output")
    return base.resolve()


def build_product_run_name(cloth_id: str, size_id: str, run_number: int) -> str:
    """Build the canonical run name: <cloth_id>-<size_id>-<run_number>."""
    return f"{cloth_id}-{size_id}-{run_number:03d}"


def parse_product_run_name(run_name: str) -> Optional[tuple[str, str, int]]:
    """Parse a canonical product-ingestion run folder name."""
    match = _RUN_RE.match(run_name)
    if not match:
        return None
    cloth_id, size_id, run_number = match.groups()
    return cloth_id, size_id, int(run_number)


def iter_product_runs(output_root: Optional[str | Path] = None) -> Iterable[Path]:
    """Yield canonical run directories under the output root."""
    base = get_output_root(output_root)
    if not base.exists():
        return []

    runs = []
    for child in base.iterdir():
        parsed = parse_product_run_name(child.name) if child.is_dir() else None
        if parsed:
            runs.append(child)
    return runs


def list_product_runs(
    cloth_id: Optional[str] = None,
    size_id: Optional[str] = None,
    output_root: Optional[str | Path] = None,
) -> list[Path]:
    """Return canonical run directories filtered by cloth_id and/or size_id."""
    runs = []
    for run_dir in iter_product_runs(output_root):
        parsed = parse_product_run_name(run_dir.name)
        if not parsed:
            continue
        run_cloth_id, run_size_id, run_number = parsed
        if cloth_id and run_cloth_id != cloth_id:
            continue
        if size_id and run_size_id != size_id:
            continue
        runs.append((run_cloth_id, run_size_id, run_number, run_dir))

    runs.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in runs]


def get_next_product_run_dir(
    cloth_id: str,
    size_id: str,
    output_root: Optional[str | Path] = None,
) -> Path:
    """Create and return the next canonical run directory."""
    base = get_output_root(output_root)
    base.mkdir(parents=True, exist_ok=True)

    existing = list_product_runs(cloth_id=cloth_id, size_id=size_id, output_root=base)
    next_number = 1
    if existing:
        parsed = parse_product_run_name(existing[-1].name)
        if parsed:
            next_number = parsed[2] + 1

    run_dir = base / build_product_run_name(cloth_id, size_id, next_number)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def get_latest_product_run_dir(
    cloth_id: Optional[str] = None,
    size_id: Optional[str] = None,
    output_root: Optional[str | Path] = None,
) -> Path:
    """Return the latest canonical run directory."""
    runs = list_product_runs(cloth_id=cloth_id, size_id=size_id, output_root=output_root)
    if not runs:
        if cloth_id and size_id:
            raise FileNotFoundError(f"No product runs found for {cloth_id} + {size_id}.")
        raise FileNotFoundError("No canonical product_ingestion runs were found.")
    return runs[-1]


def get_latest_panels_dxf_dir(
    cloth_id: Optional[str] = None,
    size_id: Optional[str] = None,
    output_root: Optional[str | Path] = None,
) -> str:
    """Return the latest canonical panels/dxf directory as a string path."""
    run_dir = get_latest_product_run_dir(cloth_id=cloth_id, size_id=size_id, output_root=output_root)
    return str(run_dir / "panels" / "dxf")
