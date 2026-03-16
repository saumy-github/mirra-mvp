"""Step 6: Read edge data and query arrangement slots."""

import time

from .helpers import apply_slot_fallbacks
from .helpers import resolve_slot_map


def run(ctx):
    print("\n[6] Reading pattern edge data ...")
    for idx in range(ctx.loaded_patterns):
        info = ctx.client.get_pattern_info(idx)
        name = info.get("info", {}).get("name", f"pattern_{idx}")
        line_count = info.get("info", {}).get("line_count", "?")
        print(f"  Pattern {idx}: {name}  ({line_count} edges)")

    print("\n[6b] Querying CLO arrangement slots ...")
    # CLO can delay arrangement slot availability; retry briefly before fallback.
    ctx.slots = []
    for _ in range(3):
        arr_resp = ctx.client.get_arrangement_list()
        slots = arr_resp.get("slots", [])
        if slots:
            ctx.slots = slots
            break
        time.sleep(1.0)

    ctx.has_live_slots = bool(ctx.slots)

    if ctx.slots:
        for slot in ctx.slots:
            print(f"  Slot {slot.get('index', '?')}: {slot}")
    else:
        print("  No slots returned - avatar may not be loaded yet or CLO version")
        print("  doesn't populate arrangement list until after first simulate.")

        # CLO 2025 sometimes populates arrangement metadata only after a frame/sim tick.
        if ctx.avatar_loaded:
            print("  Trying slot recovery: running a short simulate(1) and re-querying slots ...")
            ctx.client.simulate(steps=1)
            ctx.client.wait_for_queue(timeout=30)

            for _ in range(3):
                arr_resp = ctx.client.get_arrangement_list()
                slots = arr_resp.get("slots", [])
                if slots:
                    ctx.slots = slots
                    break
                time.sleep(1.0)

            if ctx.slots:
                print("  Slot recovery succeeded.")
                for slot in ctx.slots:
                    print(f"  Slot {slot.get('index', '?')}: {slot}")

    resolved_slot_map = resolve_slot_map(ctx.slots)
    ctx.slot_map = apply_slot_fallbacks(resolved_slot_map)

    if resolved_slot_map != ctx.slot_map:
        print("  Some slots were unresolved; using fallback indices front=0 back=1 sleeve_L=2 sleeve_R=3")
    if not ctx.has_live_slots:
        print("  ! Using fallback slot strategy; stage 7 will apply stronger per-piece offsets.")

    print(
        "  Matched slots - "
        f"front:{ctx.slot_map['front']} back:{ctx.slot_map['back']} "
        f"sleeve_L:{ctx.slot_map['sleeve_L']} sleeve_R:{ctx.slot_map['sleeve_R']}"
    )
    return True
