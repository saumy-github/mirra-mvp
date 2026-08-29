"""Helpers for canonical product_ingestion run folders.

Layout (doc 13, Phase 4):

    output/
      c_001/
        s_001/
          001/
          002/
        s_002/
      c_002/

Flat `c_001-s_001-001` folders predate 2026-08-23 and are deliberately not
parsed here — see doc 13 section 52. The cloth/size directory patterns below
reject any name containing a dash, so a legacy folder can never be mistaken
for a cloth directory.

The run *id* stays flat (`c_001-s_001-001`). Nesting is filesystem
ergonomics; the id is what goes into run_summary.json, logs and Mongo, and
`run_dir.name` alone ("001") would be meaningless there.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

_HERE = Path(__file__).parent.resolve()

_CLOTH_RE = re.compile(r"^c_[^-]+$")
_SIZE_RE = re.compile(r"^s_[^-]+$")
_RUN_RE = re.compile(r"^(\d{3})$")


def get_output_root(output_root: Optional[str | Path] = None) -> Path:
    """Return the canonical output root."""
    base = Path(output_root) if output_root else (_HERE / "output")
    return base.resolve()


def build_product_run_id(cloth_id: str, size_id: str, run_number: int) -> str:
    """The stable run identifier: <cloth_id>-<size_id>-<run_number>."""
    return f"{cloth_id}-{size_id}-{run_number:03d}"


# Kept under its old name for callers that still import it.
build_product_run_name = build_product_run_id


def get_product_run_dir(
    cloth_id: str,
    size_id: str,
    run_number: int,
    output_root: Optional[str | Path] = None,
) -> Path:
    """Path of one run directory under the nested tree."""
    return get_output_root(output_root) / cloth_id / size_id / f"{run_number:03d}"


def parse_product_run_dir(run_dir: Path) -> Optional[tuple[str, str, int]]:
    """Parse a nested run directory into (cloth_id, size_id, run_number)."""
    number_match = _RUN_RE.match(run_dir.name)
    if not number_match:
        return None
    size_dir = run_dir.parent
    cloth_dir = size_dir.parent
    if not _SIZE_RE.match(size_dir.name) or not _CLOTH_RE.match(cloth_dir.name):
        return None
    return cloth_dir.name, size_dir.name, int(number_match.group(1))


def iter_product_runs(output_root: Optional[str | Path] = None) -> Iterable[Path]:
    """Yield canonical run directories under the output root."""
    base = get_output_root(output_root)
    if not base.exists():
        return []

    runs: list[Path] = []
    for cloth_dir in base.iterdir():
        if not cloth_dir.is_dir() or not _CLOTH_RE.match(cloth_dir.name):
            continue
        for size_dir in cloth_dir.iterdir():
            if not size_dir.is_dir() or not _SIZE_RE.match(size_dir.name):
                continue
            for run_dir in size_dir.iterdir():
                if run_dir.is_dir() and _RUN_RE.match(run_dir.name):
                    runs.append(run_dir)
    return runs


def list_product_runs(
    cloth_id: Optional[str] = None,
    size_id: Optional[str] = None,
    output_root: Optional[str | Path] = None,
) -> list[Path]:
    """Return canonical run directories filtered by cloth_id and/or size_id."""
    runs = []
    for run_dir in iter_product_runs(output_root):
        parsed = parse_product_run_dir(run_dir)
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
    existing = list_product_runs(cloth_id=cloth_id, size_id=size_id, output_root=base)

    next_number = 1
    if existing:
        parsed = parse_product_run_dir(existing[-1])
        if parsed:
            next_number = parsed[2] + 1

    run_dir = get_product_run_dir(cloth_id, size_id, next_number, output_root=base)
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
