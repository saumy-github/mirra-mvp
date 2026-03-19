"""Step 4: Import DXF pattern pieces."""

import json

from .helpers import print_result


def _compute_dynamic_pattern_scale(ctx):
    """Estimate import scale so garment height tracks avatar size in current CLO unit context."""
    try:
        # Read avatar OBJ bounds (raw STAR export units).
        min_y = float("inf")
        max_y = float("-inf")
        with open(ctx.avatar_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith("v "):
                    continue
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                y = float(parts[2])
                min_y = min(min_y, y)
                max_y = max(max_y, y)

        if min_y == float("inf") or max_y == float("-inf"):
            return None

        avatar_height_raw = max_y - min_y
        if avatar_height_raw <= 0:
            return None

        # Load generator metadata for intended garment dimensions.
        meta_path = ctx.patterns_dir.parent / "pattern_metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        garment_length_cm = float(meta["garment_measurements"]["garment_length"])
        if garment_length_cm <= 0:
            return None

        # Current plugin imports avatar with scale=100.
        avatar_import_scale = 100.0
        avatar_height_clo_units = avatar_height_raw * avatar_import_scale

        # Target a shirt body length around 40% of avatar height.
        target_panel_height = avatar_height_clo_units * 0.40

        # DXF units are cm and CLO tends to consume them as 10x larger display units.
        base_panel_height = garment_length_cm * 10.0
        if base_panel_height <= 0:
            return None

        scale = target_panel_height / base_panel_height

        # Keep scale in safe operating range.
        scale = max(0.05, min(2.0, scale))
        return scale
    except Exception:
        return None


def run(ctx):
    print("\n[4] Importing patterns ...")
    import_failures = []

    dynamic_scale = _compute_dynamic_pattern_scale(ctx)
    if dynamic_scale is not None:
        print(f"  Dynamic import scale (avatar-matched): {dynamic_scale:.4f}")
    else:
        print("  Dynamic import scale unavailable; using plugin default/env scale.")

    for fname in ctx.pattern_files:
        path = ctx.patterns_dir / fname
        if not path.exists():
            print(f"  ! Pattern not found: {path}")
            import_failures.append((fname, "Pattern file missing"))
            continue
        result = ctx.client.import_pattern(str(path), scale=dynamic_scale)
        ok = print_result(result, fname)
        if not ok:
            import_failures.append((fname, result.get("message", result.get("error", "Import failed"))))

    print("     Waiting for CLO to finish imports ...")
    ctx.client.wait_for_queue(timeout=60)

    # import-pattern is queued; real SDK failures appear only in last_results.
    status = ctx.client.get_status()
    for row in status.get("last_results", []):
        if row.get("type") == "import-pattern" and not row.get("success", False):
            import_failures.append(("import-pattern", row.get("message", "Import failed in CLO")))

    if import_failures:
        print("\n  Import failures detected:")
        for fname, reason in import_failures:
            print(f"  - {fname}: {reason}")
        print("  Hint: CLO may reject oversized DXF panels when units are mismatched.")
        print("  Verify DXF header has $INSUNITS set to centimeters (5) and regenerate patterns.")
        return False

    return True
