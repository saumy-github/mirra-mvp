"""Phase 6 Step 1 (after-1-jun/plan-03.md): characterize the silently-broken-mesh
issue before attempting a fix.

Runs the Step-1 avatar-generation pipeline N times back-to-back for the same
user, and after each run compares the size of the extracted avatar (the
project-embedded mesh, same content CLO wrote into result_project.zprj)
against the base avatar's own file size. A healthy morph should land close to
(or slightly above) the base size, since it's the same topology with
different feature values baked in; a save that raced CLO's internal mesh
rebuild produces a noticeably smaller, structurally incomplete file.

This exists to turn "one bad run, one good run" into an actual failure rate
and a concrete size-deviation threshold, before touching any pipeline code.
Run once before a fix, and again after, for a real before/after comparison.

Usage:
    python -m clo_avatar_generation.scripts.repeat_run_check --user-id u_001 --count 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_avatar_generation.avatar_runtime.context import Step1Context
from clo_avatar_generation.avatar_runtime.field_contract import get_default_base_avatar
from clo_avatar_generation.avatar_runtime.pipeline import run_pipeline

DEFAULT_COUNT = 10
DEFAULT_THRESHOLD_PCT = 3.0


def _resolve_base_avatar_path() -> Path:
    default_relative = get_default_base_avatar()
    if default_relative.is_absolute():
        return default_relative
    return (REPO_ROOT / default_relative).resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Step-1 pipeline N times back-to-back for one user and check for "
            "the silently-incomplete-mesh issue (plan-03.md Phase 6)."
        )
    )
    parser.add_argument("--user-id", required=True, help="Mongo user_id to run repeatedly.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"Number of runs (default {DEFAULT_COUNT}).")
    parser.add_argument(
        "--threshold-pct",
        type=float,
        default=DEFAULT_THRESHOLD_PCT,
        help=(
            "Flag a run if the extracted avatar is more than this percent smaller than the "
            f"base avatar (default {DEFAULT_THRESHOLD_PCT}). Independent of the pipeline's own "
            "internal retry/threshold in step_11_save_outputs.py — this script re-checks the "
            "final result of each full run, retries included."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    base_avatar_path = _resolve_base_avatar_path()
    if not base_avatar_path.exists():
        print(f"Error: base avatar not found: {base_avatar_path}")
        return 1
    base_size = base_avatar_path.stat().st_size

    rows: list[dict[str, object]] = []
    for _ in range(args.count):
        ctx = Step1Context(
            user_id=args.user_id,
            base_avatar_path_input=str(base_avatar_path),
            measurement_apply_mode_input="avt_patch",
            interactive=False,
        )
        ctx = run_pipeline(ctx)

        run_id = ctx.run_identity.run_id if ctx.run_identity else f"{args.user_id}-?"
        if ctx.status != "completed" or ctx.extracted_avatar_path is None:
            rows.append(
                {
                    "run_id": run_id,
                    "status": ctx.status,
                    "embedded_size": None,
                    "delta_pct": None,
                    "flagged": True,
                }
            )
            continue

        embedded_size = ctx.extracted_avatar_path.stat().st_size
        delta_pct = (embedded_size - base_size) / base_size * 100.0
        flagged = delta_pct < -args.threshold_pct
        rows.append(
            {
                "run_id": run_id,
                "status": ctx.status,
                "embedded_size": embedded_size,
                "delta_pct": delta_pct,
                "flagged": flagged,
            }
        )

    print()
    print(f"Base avatar size: {base_size:,} bytes ({base_avatar_path})")
    print(f"{'run_id':<16} {'status':<10} {'embedded_size':>15} {'delta_%':>10}  verdict")
    print("-" * 70)
    flagged_count = 0
    for row in rows:
        embedded_size_str = f"{row['embedded_size']:,}" if row["embedded_size"] is not None else "n/a"
        delta_str = f"{row['delta_pct']:.2f}" if row["delta_pct"] is not None else "n/a"
        verdict = "FLAGGED" if row["flagged"] else "ok"
        if row["flagged"]:
            flagged_count += 1
        print(f"{row['run_id']:<16} {row['status']:<10} {embedded_size_str:>15} {delta_str:>10}  {verdict}")

    print("-" * 70)
    print(f"{flagged_count}/{len(rows)} runs flagged (threshold: {args.threshold_pct:.1f}% below base avatar size)")
    return 1 if flagged_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
