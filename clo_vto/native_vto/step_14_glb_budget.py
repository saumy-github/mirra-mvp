"""Step 14: bring the shipped GLB down to a size a phone will actually download.

Measured on a finished avatar export: 23.3 MB of a 36.7 MB file is textures, in 26 images,
several of them 2048-square PNGs that have no need to be lossless. Applying a per-role
texture budget takes the same file to 16.2 MB with the face albedo untouched - the one
texture a shopper studies, and the thing the whole face pipeline exists to get right.

Separate from step_13 on purpose. That step is about correctness: without it the hair
renders as a solid helmet outside CLO. This one is about delivery, it is tuned by numbers
that will change as we learn what a shopper's connection tolerates, and it must be able to
fail on its own without taking the hair fix down with it.

Same contract as step_12 and step_13: **every failure path returns True.** A file that is
too big is a slow try-on; a pipeline that aborts is no try-on.
"""

from __future__ import annotations

import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

# Per-role maximum edge in pixels. The face keeps its full resolution; everything else is
# read at body distance or through a garment.
BUDGET = {
    'face_colour': 2048,
    'base_colour': 1024,
    'data_map': 512,
}

OUTPUT_NAME = "simulation_web.glb"

# If the budget saves less than this, the rewrite is not worth a generation of re-encoding
# and the previous file ships instead.
MIN_WORTHWHILE_SAVING = 0.05


def _source_glb(ctx) -> Path | None:
    """The newest GLB in the chain: hair opacity, else textured, else the raw export."""
    for attribute in ("final_glb_path", "textured_glb_path", "glb_path"):
        value = getattr(ctx, attribute, None)
        if value and Path(value).exists():
            return Path(value)
    return None


def run(ctx) -> bool:
    if getattr(ctx, "skip_glb_postprocess", False):
        print("  [SKIP] GLB post-processing disabled (skip_glb_postprocess=True).")
        return True

    source = _source_glb(ctx)
    if source is None:
        print("  [SKIP] No GLB available to shrink.")
        return True

    try:
        from face_fitting.optimize_glb import optimize
    except ImportError as exc:
        print(f"  [SKIP] Texture budget unavailable ({exc}).")
        return True

    out_path = Path(ctx.output_dir) / OUTPUT_NAME
    try:
        report = optimize(source, out_path, BUDGET, log=lambda message: print(f"  {message}"))
    except Exception as exc:  # noqa: BLE001 - delivery tuning never blocks a try-on
        print(f"  [WARN] Texture budget failed ({exc}); shipping the GLB as it was.")
        return True

    for warning in report.warnings:
        print(f"  [WARN] {warning}")

    if report.output is None or not out_path.exists():
        print("  [WARN] Texture budget produced no file; shipping the previous GLB.")
        return True
    if report.saved_fraction < MIN_WORTHWHILE_SAVING:
        print(f"  [SKIP] Only {report.saved_fraction:.0%} saved - not worth re-encoding; "
              "shipping the previous GLB.")
        return True

    ctx.final_glb_path = out_path
    print(f"  {report.before_bytes / 1e6:.1f} MB -> {report.after_bytes / 1e6:.1f} MB "
          f"({report.saved_fraction:.0%} smaller) -> {out_path.name}")
    return True
