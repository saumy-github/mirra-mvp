"""Step 3: Import avatar mesh."""

import json

from .helpers import print_result


def _resolve_avatar_import_scale(avatar_obj_path):
    """Infer CLO import scale from avatar export metadata units.

    Current avatar exporter writes OBJ vertices in centimeters. CLO OBJ import
    behaves in millimeter-like scene units in this workflow, so cm -> mm needs x10.
    """
    meta_path = avatar_obj_path.parent / "measurements.json"
    default_scale = 10.0

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        units = str(meta.get("units", "")).strip().lower()
        if units in ("centimeter", "centimeters", "cm"):
            return 10.0
        if units in ("millimeter", "millimeters", "mm"):
            return 1.0
        if units in ("meter", "meters", "m"):
            return 1000.0
    except Exception:
        pass

    return default_scale


def run(ctx):
    print("\n[3] Importing avatar ...")
    if not ctx.avatar_path.exists():
        print(f"  ! Avatar not found: {ctx.avatar_path}")
        print("  ! Simulation will be SKIPPED - CLO crashes without a body mesh.")
        print("  ! Generate an avatar OBJ via avatar_generation/run_avatar.py first.")
        ctx.avatar_loaded = False
    else:
        avatar_scale = _resolve_avatar_import_scale(ctx.avatar_path)
        print(f"  Avatar import scale selected: {avatar_scale:.3f}")
        print_result(
            ctx.client.import_avatar(str(ctx.avatar_path), scale=avatar_scale),
            "import-avatar",
        )
        ctx.avatar_loaded = True

    ctx.client.wait_for_queue(timeout=30)
    return True
