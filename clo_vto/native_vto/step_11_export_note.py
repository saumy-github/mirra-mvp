"""Step 11: Export CLO simulation as GLB.

Calls the CLO REST plugin's /export endpoint, waits for the file to appear,
and sets ctx.glb_path so step_12 can locate it for texture injection.

Export *infrastructure* failure (command rejected, file never appears, file
suspiciously small) is logged but never aborts the pipeline, since step_12
guards against a missing GLB gracefully. Export *content* failure (avatar
mesh missing, geometry never simulated) IS blocking — see the geometry
sanity check below and .agent/clo-avatar-vto/vto-pipeline-debug-plan-26_7_24.md,
Bugs 3 and 4. Silently accepting a file that "looks done" but contains 4
flat unsewn panels with no avatar is exactly the bug this check exists to
catch.
"""

from __future__ import annotations

import time
from pathlib import Path

from .glb_inspect import mesh_is_draped
from .helpers import print_result

try:
    from pygltflib import GLTF2
    _PYGLTFLIB_OK = True
except ImportError:
    _PYGLTFLIB_OK = False


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

    # --- Geometry content check (Bugs 3 & 4) ---
    # File existence + size only proves CLO wrote *something* — not that the
    # something is a simulated, sewn, avatar-visible result rather than 4
    # flat unsown panels with no avatar. The mesh-COUNT check below blocks:
    # it's calibrated against a real confirmed-bad export (see glb_inspect.py
    # and the debug-plan doc) where 4 meshes == the 4 panels and 0 avatar
    # meshes. mesh_is_draped()'s flatness check is logged for diagnostics
    # only, NOT gated on — tested against that same real file and found
    # unreliable for this pipeline (arrange-pattern already gives panels
    # real 3D curvature before any simulation runs, so "is it planar" doesn't
    # distinguish arranged-only from arranged-and-simulated here).
    if not _PYGLTFLIB_OK:
        print("  [WARN] pygltflib not installed — skipping geometry verification.")
        print("         Run:  pip install pygltflib")
    else:
        try:
            gltf = GLTF2().load(str(glb_path))
        except Exception as exc:
            print(f"  [WARN] Could not parse GLB for geometry check: {exc} — skipping (infrastructure issue).")
            gltf = None

        if gltf is not None:
            mesh_count = len(gltf.meshes)
            expected_min = ctx.expected_min_export_meshes or (len(ctx.pattern_files) + 1)
            draped_ok, drape_reason = mesh_is_draped(gltf)
            print(f"  meshes in export : {mesh_count} (expected >= {expected_min})")
            print(f"  drape check (diagnostic only, not gated): {drape_reason}")

            if mesh_count < expected_min:
                print(f"  [FAIL] Export has only {mesh_count} mesh(es) — avatar mesh is likely missing.")
                return False
            if not draped_ok:
                print("  [WARN] Export geometry looks unsimulated by the flatness heuristic — "
                      "not blocking (heuristic unreliable for this pipeline, see glb_inspect.py).")

    # Publish path so step_12 can pick it up.
    ctx.glb_path = glb_path
    return True
