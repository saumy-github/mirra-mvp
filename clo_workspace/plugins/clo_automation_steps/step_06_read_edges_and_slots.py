"""Step 6: Read edge data and query arrangement slots."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

from .helpers import apply_slot_fallbacks
from .helpers import resolve_slot_map


def run(ctx):
    print("\n[6] Reading pattern edge data ...")
    
    # Check for debug mode flag
    debug_mode = os.getenv("DEBUG_STAGE6_RAW", "").lower() in ("1", "true", "yes")
    raw_payloads = {}
    
    for idx in range(ctx.loaded_patterns):
        info = ctx.client.get_pattern_info(idx)
        raw_payloads[idx] = info
        
        # Core parsing with graceful fallback
        pattern_info_block = info.get("info", {})
        name = pattern_info_block.get("name", f"pattern_{idx}")
        line_count = pattern_info_block.get("line_count", "?")
        print(f"  Pattern {idx}: {name}  ({line_count} edges)")
        
        # Debug output
        if debug_mode:
            print(f"    [DEBUG] Raw payload for pattern {idx}:")
            print(f"    {json.dumps(info, indent=6)}")

    print("\n[6b] Querying CLO arrangement slots ...")
    # CLO can delay arrangement slot availability; retry briefly before fallback.
    ctx.slots = []
    arr_payloads = {}
    for retry_idx in range(3):
        arr_resp = ctx.client.get_arrangement_list()
        arr_payloads[f"attempt_{retry_idx}"] = arr_resp
        slots = arr_resp.get("slots", [])
        if slots:
            ctx.slots = slots
            break
        time.sleep(1.0)

    ctx.has_live_slots = bool(ctx.slots)

    if debug_mode:
        print("    [DEBUG] Arrangement list payloads:")
        for key, payload in arr_payloads.items():
            print(f"    {key}: {json.dumps(payload, indent=6)}")

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

            for retry_idx in range(3, 6):
                arr_resp = ctx.client.get_arrangement_list()
                arr_payloads[f"attempt_{retry_idx}"] = arr_resp
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
    
    # Optional: save raw payloads to file for offline analysis
    if debug_mode and (raw_payloads or arr_payloads):
        debug_dir = Path("stage_6_payloads")
        debug_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"stage6_payloads_{timestamp}.json"
        debug_data = {
            "timestamp": timestamp,
            "pattern_info": raw_payloads,
            "arrangement_list": arr_payloads,
            "has_live_slots": ctx.has_live_slots,
        }
        with open(debug_file, "w") as f:
            json.dump(debug_data, f, indent=2)
        print(f"  [DEBUG] Payloads saved to {debug_file}")

    return True
