"""Step 7: Arrange patterns around the avatar."""

from .helpers import print_result


def run(ctx):
    print("\n[7] Arranging patterns in 3D around avatar ...")
    arrangement = [
        (0, ctx.slot_map.get("front", -1), 0, 0, 100, 0),
        (1, ctx.slot_map.get("back", -1), 0, 0, 100, 0),
        (2, ctx.slot_map.get("sleeve_L", -1), 0, 0, 100, 0),
        (3, ctx.slot_map.get("sleeve_R", -1), 0, 0, 100, 0),
    ]

    for idx, slot, ox, oy, oz, ori in arrangement:
        if idx < ctx.loaded_patterns:
            print_result(
                ctx.client.arrange_pattern(idx, slot, ox, oy, oz, ori),
                f"pattern {idx} -> slot {slot}",
            )

    ctx.client.wait_for_queue(timeout=15)
    return True
