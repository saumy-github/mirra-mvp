"""Step 6: Read edge data and query arrangement slots."""

from .helpers import find_slot


def run(ctx):
    print("\n[6] Reading pattern edge data ...")
    for idx in range(ctx.loaded_patterns):
        info = ctx.client.get_pattern_info(idx)
        name = info.get("info", {}).get("name", f"pattern_{idx}")
        line_count = info.get("info", {}).get("line_count", "?")
        print(f"  Pattern {idx}: {name}  ({line_count} edges)")

    print("\n[6b] Querying CLO arrangement slots ...")
    arr_resp = ctx.client.get_arrangement_list()
    ctx.slots = arr_resp.get("slots", [])

    if ctx.slots:
        for slot in ctx.slots:
            print(f"  Slot {slot.get('index', '?')}: {slot}")
    else:
        print("  No slots returned - avatar may not be loaded yet or CLO version")
        print("  doesn't populate arrangement list until after first simulate.")

    ctx.slot_map = {
        "front": find_slot(ctx.slots, ["front"]),
        "back": find_slot(ctx.slots, ["back"]),
        "sleeve_L": find_slot(ctx.slots, ["left", "sleeve"]),
        "sleeve_R": find_slot(ctx.slots, ["right", "sleeve"]),
    }

    print(
        "  Matched slots - "
        f"front:{ctx.slot_map['front']} back:{ctx.slot_map['back']} "
        f"sleeve_L:{ctx.slot_map['sleeve_L']} sleeve_R:{ctx.slot_map['sleeve_R']}"
    )
    return True
