"""Helpers for canonical VTO run folders.

Layout (doc 13, Phase 5):

    output/
      u_011/
        c_001/
          s_001/
            001/
            002/
          s_002/
        c_002/
      u_012/

Before this, every run wrote `simulation.glb` into a single shared
`clo_vto/output/`, so each render silently overwrote the previous one
(doc 13 section 42). A per-run directory is the whole fix.

Files written directly under `output/` by older runs are left alone; the
patterns below only match the nested tree.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

_USER_RE = re.compile(r"^u_[^-]+$")
_CLOTH_RE = re.compile(r"^c_[^-]+$")
_SIZE_RE = re.compile(r"^s_[^-]+$")
_RUN_RE = re.compile(r"^(\d{3})$")


def get_output_root(output_root: Optional[str | Path] = None) -> Path:
    base = Path(output_root) if output_root else (PACKAGE_ROOT / "output")
    return base.resolve()


def build_vto_run_id(user_id: str, cloth_id: str, size_id: str, run_number: int) -> str:
    """The stable run identifier: <user>-<cloth>-<size>-<run_number>."""
    return f"{user_id}-{cloth_id}-{size_id}-{run_number:03d}"


def get_vto_run_dir(
    user_id: str,
    cloth_id: str,
    size_id: str,
    run_number: int,
    output_root: Optional[str | Path] = None,
) -> Path:
    return get_output_root(output_root) / user_id / cloth_id / size_id / f"{run_number:03d}"


def parse_vto_run_dir(run_dir: Path) -> Optional[tuple[str, str, str, int]]:
    number_match = _RUN_RE.match(run_dir.name)
    if not number_match:
        return None
    size_dir = run_dir.parent
    cloth_dir = size_dir.parent
    user_dir = cloth_dir.parent
    if not (
        _SIZE_RE.match(size_dir.name)
        and _CLOTH_RE.match(cloth_dir.name)
        and _USER_RE.match(user_dir.name)
    ):
        return None
    return user_dir.name, cloth_dir.name, size_dir.name, int(number_match.group(1))


def iter_vto_runs(output_root: Optional[str | Path] = None) -> Iterable[Path]:
    base = get_output_root(output_root)
    if not base.exists():
        return []

    runs: list[Path] = []
    for user_dir in base.iterdir():
        if not user_dir.is_dir() or not _USER_RE.match(user_dir.name):
            continue
        for cloth_dir in user_dir.iterdir():
            if not cloth_dir.is_dir() or not _CLOTH_RE.match(cloth_dir.name):
                continue
            for size_dir in cloth_dir.iterdir():
                if not size_dir.is_dir() or not _SIZE_RE.match(size_dir.name):
                    continue
                for run_dir in size_dir.iterdir():
                    if run_dir.is_dir() and _RUN_RE.match(run_dir.name):
                        runs.append(run_dir)
    return runs


def list_vto_runs(
    user_id: Optional[str] = None,
    cloth_id: Optional[str] = None,
    size_id: Optional[str] = None,
    output_root: Optional[str | Path] = None,
) -> list[Path]:
    runs = []
    for run_dir in iter_vto_runs(output_root):
        parsed = parse_vto_run_dir(run_dir)
        if not parsed:
            continue
        run_user, run_cloth, run_size, run_number = parsed
        if user_id and run_user != user_id:
            continue
        if cloth_id and run_cloth != cloth_id:
            continue
        if size_id and run_size != size_id:
            continue
        runs.append((run_user, run_cloth, run_size, run_number, run_dir))

    runs.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [item[4] for item in runs]


def get_next_vto_run_dir(
    user_id: str,
    cloth_id: str,
    size_id: str,
    output_root: Optional[str | Path] = None,
) -> Path:
    """Create and return the next run directory for this user/cloth/size."""
    base = get_output_root(output_root)
    existing = list_vto_runs(
        user_id=user_id, cloth_id=cloth_id, size_id=size_id, output_root=base
    )

    next_number = 1
    if existing:
        parsed = parse_vto_run_dir(existing[-1])
        if parsed:
            next_number = parsed[3] + 1

    run_dir = get_vto_run_dir(user_id, cloth_id, size_id, next_number, output_root=base)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
