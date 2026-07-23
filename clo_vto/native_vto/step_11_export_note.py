"""Step 11: Export CLO simulation as GLB.

Calls the CLO REST plugin's /export endpoint, waits for the file to appear,
and sets ctx.glb_path so step_12 can locate it for texture injection.

Returns True in all cases — export failure is logged but never aborts the
pipeline, because step_12 guards against a missing GLB gracefully.
"""

from __future__ import annotations

import time
from pathlib import Path

from .helpers import print_result


# Minimum valid GLB size: the 12-byte GLB header alone makes anything < 1 KB
# almost certainly an error response or an empty write.
_MIN_GLB_BYTES = 1024


def run(ctx) -> bool:
    print("\n[11] Exporting GLB simulation ...")

    glb_path = ctx.output_dir / "simulation.glb"
    # CLO expects a forward-slash path string even on Windows.
    posix_path = glb_path.as_posix()

    print(f"  output_path : {glb_path}")

    # --- Trigger export ---
    result = ctx.client.export_garment(posix_path, format="glb")
    ok = print_result(result, "export_garment")

    if not ok:
        print("  [WARN] CLO rejected the export command — GLB will not be available.")
        print("         step_12 (texture inject) will skip gracefully.")
        return True  # non-blocking

    # --- Wait for CLO to write the file ---
    print("  Waiting for CLO to write GLB (up to 120s) ...")
    try:
        ctx.client.wait_for_queue(timeout=120)
    except Exception as exc:
        print(f"  [WARN] Queue drain timed out during export: {exc}")
        print("         CLO may still be writing — checking file anyway.")

    # --- Verify the file ---
    if not glb_path.exists():
        print(f"  [WARN] GLB not found at {glb_path}")
        print("         CLO may not have written the file — check the CLO window.")
        return True  # non-blocking

    size_bytes = glb_path.stat().st_size
    if size_bytes < _MIN_GLB_BYTES:
        print(f"  [WARN] GLB exists but is suspiciously small ({size_bytes} B) — may be corrupt.")
        return True  # non-blocking

    size_mb = size_bytes / (1024 * 1024)
    print(f"  [OK] GLB written — {size_mb:.1f} MB")

    # Publish path so step_12 can pick it up.
    ctx.glb_path = glb_path
    return True
