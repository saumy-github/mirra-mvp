"""Step 9: Create seams using seam map."""

from .helpers import print_result
from .seams import DEFAULT_SEAM_META


def _resolve_pattern_index(ctx, ref):
    """Resolve seam pattern reference to CLO scene pattern index.

    Supports:
    - piece names: front_panel/back_panel/sleeve_left/sleeve_right
    - legacy import-order indices 0..3
    - absolute indices as fallback
    """
    expected_order = ["front_panel", "back_panel", "sleeve_left", "sleeve_right"]

    if isinstance(ref, str):
        if ref in ctx.piece_to_index:
            return ctx.piece_to_index[ref]
        raise ValueError(f"Unknown seam piece reference '{ref}'")

    if isinstance(ref, int):
        if 0 <= ref < len(expected_order):
            piece = expected_order[ref]
            if piece in ctx.piece_to_index:
                return ctx.piece_to_index[piece]
        return ref

    raise ValueError(f"Unsupported seam reference type: {type(ref)}")


def run(ctx):
    print("\n[9] Creating seams ...")
    if not ctx.ready_for_sewing or not ctx.arrangement_ok:
        print("  Sewing blocked - import/edge/slot/arrangement gates were not satisfied.")
        return False

    if not ctx.seams:
        print("  No seam map provided. Skipping seam creation.")
        return True
    if ctx.using_default_seams:
        print("  NOTE: Using placeholder edge indices.")
        print("  Run plugins/discover_seam_indices.py to get real indices.")

    expected_hash = str(DEFAULT_SEAM_META.get("geometry_hash", "")).strip()
    if expected_hash:
        if expected_hash != ctx.pattern_geometry_hash:
            print(
                "  Seam map compatibility check failed - DXF geometry hash mismatch. "
                "Regenerate seam map for current panel geometry."
            )
            return False
    else:
        if ctx.pattern_geometry_hash:
            print("  Seam hash check: no baseline configured; proceeding with runtime mapping.")

    ok_count = 0
    fail_count = 0
    ctx.seam_results = []
    for seam in ctx.seams:
        try:
            pa = _resolve_pattern_index(ctx, seam["a"])
            pb = _resolve_pattern_index(ctx, seam["b"])
        except Exception as exc:
            print(f"  ! Seam '{seam.get('name', '?')}' resolution failed: {exc}")
            ctx.seam_results.append({"name": seam.get("name", "?"), "success": False, "error": str(exc)})
            fail_count += 1
            continue

        ok = print_result(
            ctx.client.create_seam(
                pa,
                seam["la"],
                pb,
                seam["lb"],
                seam.get("da", True),
                seam.get("db", True),
            ),
            f"{seam['name']} ({pa}:{seam['la']} <-> {pb}:{seam['lb']})",
        )
        if ok:
            ok_count += 1
            ctx.seam_results.append({"name": seam.get("name", "?"), "success": True, "a": pa, "b": pb})
        else:
            fail_count += 1
            ctx.seam_results.append({"name": seam.get("name", "?"), "success": False, "a": pa, "b": pb})

    ctx.client.wait_for_queue(timeout=60)

    if fail_count > 0:
        print(f"  Seam creation failed for {fail_count} seam(s) out of {ok_count + fail_count}.")
        return False

    return True
