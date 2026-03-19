"""Step 7: Arrange patterns around the avatar."""

import os
from .helpers import print_result


def run(ctx):
    print("\n[7] Arranging patterns in 3D around avatar ...")
    
    # Hard-fail gate: if live slots are unavailable, fail by default to prevent
    # false-positive success runs. Use ALLOW_DEGRADED_PLACEMENT env var to override.
    allow_degraded = os.getenv("ALLOW_DEGRADED_PLACEMENT", "").lower() in ("1", "true", "yes")
    
    if not ctx.has_live_slots and not allow_degraded:
        print("  ✗ PLACEMENT FAILURE: Live arrangement slots are unavailable in CLO.")
        print("     This typically means the avatar is not properly loaded or CLO's")
        print("     arrangement metadata is not yet available.")
        print("     Pipeline stopping to prevent silent false-positive placement.")
        print("     To force degraded-mode placement (not recommended), set:")
        print("     ALLOW_DEGRADED_PLACEMENT=1")
        return False
    
    # Offsets are mm. When CLO does not provide live slot metadata, use
    # stronger per-piece separation so all panels do not stack at one point.
    if ctx.has_live_slots:
        arrangement = [
            (0, ctx.slot_map.get("front", 0), 0, 0, 120, 0),
            (1, ctx.slot_map.get("back", 1), 0, 0, 120, 0),
            (2, ctx.slot_map.get("sleeve_L", 2), -220, 30, 120, 0),
            (3, ctx.slot_map.get("sleeve_R", 3), 220, 30, 120, 0),
        ]
    else:
        # Fallback does not trust slot binding; apply position-only placement
        # with bounded values to avoid CLO clamping everything to one default.
        arrangement = [
            (0, -1, 10, 80, 80, 0),
            (1, -1, 90, 80, 80, 180),
            (2, -1, 15, 25, 70, 270),
            (3, -1, 85, 25, 70, 90),
        ]
        print("  ! DEGRADED MODE: Live arrangement slots unavailable; applying fallback spread offsets.")

    arranged_ok = True
    requested = {}
    for idx, slot, ox, oy, oz, ori in arrangement:
        if idx < ctx.loaded_patterns:
            position_only = slot < 0
            requested[idx] = {"slot": slot, "x": ox, "y": oy, "z": oz, "orientation": ori, "position_only": position_only}
            ok = print_result(
                ctx.client.arrange_pattern(
                    idx,
                    slot,
                    ox,
                    oy,
                    oz,
                    ori,
                    position_only=position_only,
                ),
                f"pattern {idx} -> slot {slot}",
            )
            arranged_ok = arranged_ok and ok

    ctx.client.wait_for_queue(timeout=15)

    # Read back arrangement state so failures are visible immediately.
    verify = ctx.client.get_pattern_arrangements()
    patterns = verify.get("patterns", []) if isinstance(verify, dict) else []
    if patterns:
        print("  Arrangement verify:")
        for row in patterns:
            pidx = row.get("pattern_index", -1)
            req = requested.get(pidx, {})
            print(f"    pattern {pidx}: requested={req} reported={row}")

        # If all pieces report identical arrangement metadata, CLO likely
        # stacked them at one point; fail fast so the pipeline does not hide it.
        fingerprints = {
            (
                row.get("ArrangementName"),
                row.get("ArrangementOffsetX"),
                row.get("ArrangementOffsetY"),
                row.get("ArrangementOffsetZ"),
            )
            for row in patterns
        }
        if len(patterns) >= 4 and len(fingerprints) == 1:
            print("  ! Arrangement check failed: all pattern placements look identical (stacking likely).")
            return False
    else:
        print("  ! Could not verify pattern arrangements from CLO.")
        return False

    return arranged_ok
