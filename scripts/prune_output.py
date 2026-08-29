"""Prune the pipelines' debug output trees.

    python scripts/prune_output.py --dry-run
    python scripts/prune_output.py --apply

What this touches, and what it must never touch
-----------------------------------------------
`clo_avatar_generation/output/`, `product_ingestion/output/` and
`clo_vto/output/` are debug trails. `dev_upload/` and `live_upload/` are the
product — that is what the website serves and what
`avatar_profiles.avatar_glb_path` and `tryon_renders.render_glb_path` point
into. This script never touches them.

Policy (doc 13, Phase 8)
------------------------
* Keep the newest KEEP_PER_KEY runs per key, where a key is the user for
  avatars, (cloth, size) for ingestion, and (user, cloth, size) for VTO.
* Never delete the newest run for a key, whatever its age.
* Never delete a run younger than MIN_AGE_DAYS.
* Tiered: runs that fall out of the window lose their heavy files
  (.zprj/.avt, about two thirds of a run) but keep run.log, the JSON reports
  and the .glb, so "what happened on run 42" stays answerable.

Manual on purpose. Pruning while CLO or the worker may be mid-read is how you
lose the run you needed, so this never runs automatically at the end of a
pipeline run.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

KEEP_PER_KEY = 3
MIN_AGE_DAYS = 7

# Removed from runs that fall out of the keep window.
HEAVY_SUFFIXES = {".zprj", ".avt", ".arr", ".iks", ".avs", ".mea", ".bin"}
# Always kept, whatever the tier.
PROTECTED_NAMES = {"run.log", "run_report.json", "run_summary.json", "run_manifest.json"}


def _age_days(path: Path) -> float:
    return (time.time() - path.stat().st_mtime) / 86400.0


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _avatar_runs() -> dict[tuple, list[Path]]:
    """clo_avatar_generation/output/<user_id>-<NNN>/ — still a flat layout."""
    from clo_avatar_generation.avatar_runtime.run_manifest import (
        list_run_dirs,
        parse_run_dir_name,
    )

    groups: dict[tuple, list[Path]] = {}
    for run_dir in list_run_dirs():
        parsed = parse_run_dir_name(run_dir.name)
        if parsed is None:
            continue
        groups.setdefault((parsed.user_id,), []).append(run_dir)
    return groups


def _ingestion_runs() -> dict[tuple, list[Path]]:
    from product_ingestion.run_manifest import iter_product_runs, parse_product_run_dir

    groups: dict[tuple, list[Path]] = {}
    for run_dir in iter_product_runs():
        parsed = parse_product_run_dir(run_dir)
        if parsed is None:
            continue
        cloth_id, size_id, _ = parsed
        groups.setdefault((cloth_id, size_id), []).append(run_dir)
    return groups


def _vto_runs() -> dict[tuple, list[Path]]:
    from clo_vto.native_vto.run_manifest import iter_vto_runs, parse_vto_run_dir

    groups: dict[tuple, list[Path]] = {}
    for run_dir in iter_vto_runs():
        parsed = parse_vto_run_dir(run_dir)
        if parsed is None:
            continue
        user_id, cloth_id, size_id, _ = parsed
        groups.setdefault((user_id, cloth_id, size_id), []).append(run_dir)
    return groups


def _strip_heavy(run_dir: Path, apply: bool) -> int:
    """Delete the heavy files in one run, returning the bytes freed."""
    freed = 0
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in PROTECTED_NAMES:
            continue
        if path.suffix.lower() not in HEAVY_SUFFIXES:
            continue
        freed += path.stat().st_size
        if apply:
            path.unlink()
    return freed


def prune(label: str, groups: dict[tuple, list[Path]], apply: bool) -> tuple[int, int]:
    print(f"\n{label}")
    print("-" * len(label))
    if not groups:
        print("  no runs found")
        return 0, 0

    touched = 0
    freed_total = 0
    for key in sorted(groups):
        runs = sorted(groups[key], key=lambda p: p.stat().st_mtime)
        # The newest KEEP_PER_KEY are always kept whole.
        candidates = runs[:-KEEP_PER_KEY] if len(runs) > KEEP_PER_KEY else []
        for run_dir in candidates:
            age = _age_days(run_dir)
            if age < MIN_AGE_DAYS:
                continue
            before = _dir_size(run_dir)
            freed = _strip_heavy(run_dir, apply)
            if not freed:
                continue
            touched += 1
            freed_total += freed
            print(
                f"  {'stripped' if apply else 'would strip'} "
                f"{'/'.join(key)}/{run_dir.name}  "
                f"{before / 1e6:.1f}MB -> {(before - freed) / 1e6:.1f}MB  (age {age:.0f}d)"
            )

    if not touched:
        print(f"  nothing to prune (keeping {KEEP_PER_KEY} per key, min age {MIN_AGE_DAYS}d)")
    return touched, freed_total


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune pipeline debug output.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Report what would be removed.")
    group.add_argument("--apply", action="store_true", help="Actually remove the files.")
    args = parser.parse_args()

    apply = bool(args.apply)
    print("Pruning pipeline debug output" + ("" if apply else "  (DRY RUN)"))
    print(f"Keeping {KEEP_PER_KEY} runs per key; never touching runs younger than {MIN_AGE_DAYS} days.")
    print("dev_upload/ and live_upload/ are never touched.")

    total_touched = 0
    total_freed = 0
    for label, loader in (
        ("Avatar runs", _avatar_runs),
        ("Ingestion runs", _ingestion_runs),
        ("VTO runs", _vto_runs),
    ):
        try:
            groups = loader()
        except Exception as exc:
            print(f"\n{label}\n  [WARN] could not scan: {exc}")
            continue
        touched, freed = prune(label, groups, apply)
        total_touched += touched
        total_freed += freed

    print(
        f"\n{'Freed' if apply else 'Would free'} {total_freed / 1e9:.2f} GB "
        f"across {total_touched} run(s)."
    )
    if not apply and total_touched:
        print("Re-run with --apply to remove them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
