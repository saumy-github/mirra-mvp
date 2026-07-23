"""Step 7: Arrange patterns around the avatar."""

from .helpers import print_result


def run(ctx):
    print("\n[7] Arranging patterns in 3D around avatar ...")
    if not ctx.edge_ok or not ctx.slot_ok:
        print("  Pre-arrangement gates not satisfied (edge/slot checks failed).")
        return False

    degraded_mode = (ctx.slot_fallback_mode == "pattern-arrangements-no-slots")
    if degraded_mode:
        print("  Arrangement degraded mode active - using direct offsets without slot indices.")

    avatar_scene_h = float(ctx.scale_metrics.get("scene_avatar_height_est", 0) or 0)
    spread = int(max(140, min(500, avatar_scene_h * 0.12 if avatar_scene_h > 0 else 240)))

    if degraded_mode:
        arrangement = [
            ("front_panel", -1, 0, int(spread * 0.45), 120, 0),
            ("back_panel", -1, 0, int(-spread * 0.45), 120, 180),
            ("sleeve_left", -1, -spread, 0, 80, 90),
            ("sleeve_right", -1, spread, 0, 80, -90),
        ]
    else:
        arrangement = [
            ("front_panel",  ctx.slot_map.get("front",    -1), 0, 0, 100, 0),
            ("back_panel",   ctx.slot_map.get("back",     -1), 0, 0, 100, 0),
            ("sleeve_left",  ctx.slot_map.get("sleeve_L", -1), 0, 0, 100, 0),
            ("sleeve_right", ctx.slot_map.get("sleeve_R", -1), 0, 0, 100, 0),
        ]

    for piece, slot, ox, oy, oz, ori in arrangement:
        idx = ctx.piece_to_index.get(piece)
        if idx is None:
            print(f"  Missing pattern index mapping for piece '{piece}'. Aborting.")
            return False
        if slot < 0 and not degraded_mode:
            print(f"  Invalid arrangement slot for piece '{piece}' (index {idx}). Aborting.")
            return False
        print_result(
            ctx.client.arrange_pattern(idx, slot, ox, oy, oz, ori),
            f"{piece} (pattern {idx}) -> slot {slot}",
        )

    try:
        ctx.client.wait_for_queue(timeout=15)
    except Exception as exc:
        print(f"  [WARN] Arrange drain timed out: {exc} — proceeding to verification.")

    arranged = ctx.client.get_pattern_arrangements().get("patterns", [])
    try:
        arr_resp = ctx.client.get_arrangement_list()
        dbg = ctx.client.get_arrangement_debug()
        ctx.slot_diagnostics.append(
            {
                "stage": "post-first-arrange",
                "slot_count": len(arr_resp.get("slots", [])),
                "slot_payload": arr_resp.get("slots", []),
                "pattern_arrangement_count": len(dbg.get("patterns", [])),
                "pattern_arrangements": dbg.get("patterns", []),
            }
        )
    except Exception:
        pass

    if len(arranged) < ctx.expected_pattern_count:
        print("  Arrangement verification failed - missing arrangement records.")
        return False

    missing = []
    for idx in ctx.piece_to_index.values():
        rec = next((p for p in arranged if int(p.get("pattern_index", -1)) == idx), None)
        if rec is None:
            missing.append(idx)
            continue
        blob = " ".join(str(v).lower() for v in rec.values())
        if "none" in blob:
            missing.append(idx)

    if missing:
        print(f"  Arrangement verification failed for pattern indices: {missing}")
        return False

    ctx.arrangement_ok = True
    ctx.ready_for_sewing = True
    print("  Arrangement verification passed for all 4 pieces.")
    return True
