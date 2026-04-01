"""Step 6: Read edge data and query arrangement slots."""

from pathlib import Path

try:
    import ezdxf
except Exception:
    ezdxf = None

from .helpers import score_slots
from .seams import validate_edge_counts


SLOT_WARMUP_RETRIES = 3
SLOT_WARMUP_SIM_STEPS = 1


def _slot_name(slot: dict) -> str:
    return str(
        slot.get("ArrangementName")
        or slot.get("name")
        or slot.get("description")
        or ""
    )


def _exact_name_candidates(slots: list[dict], preferred_names: list[str]) -> list[dict]:
    ranked = []
    for slot in slots:
        name = _slot_name(slot)
        if name in preferred_names:
            idx = int(slot.get("index", -1))
            if idx >= 0:
                ranked.append(
                    {
                        "index": idx,
                        "score": 1000 - preferred_names.index(name),
                        "slot": slot,
                    }
                )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def _name_fragment_candidates(slots: list[dict], required_fragments: list[str]) -> list[dict]:
    ranked = []
    for slot in slots:
        name = _slot_name(slot).lower()
        if all(fragment in name for fragment in required_fragments):
            idx = int(slot.get("index", -1))
            if idx >= 0:
                ranked.append({"index": idx, "score": 100, "slot": slot})
    return ranked


def _resolve_front_candidates(slots: list[dict]) -> list[dict]:
    preferred = [
        "Body_Front_Center_2",
        "Body_Front_Center_3",
        "Body_Front_Center_1",
        "Body_Front_2_L",
        "Body_Front_2_R",
        "Body_Front_3_L",
        "Body_Front_3_R",
        "Body_Front_1_L",
        "Body_Front_1_R",
        "Body_Front_Waist",
    ]
    return (
        _exact_name_candidates(slots, preferred)
        or score_slots(slots, ["body", "front"], optional_keywords=["torso", "chest"])
        or score_slots(slots, ["front"], optional_keywords=["body", "torso", "chest"])
    )


def _resolve_back_candidates(slots: list[dict]) -> list[dict]:
    preferred = [
        "Body_Back_Center_2",
        "Body_Back_Center_3",
        "Body_Back_Center_1",
        "Body_Back_2_L",
        "Body_Back_2_R",
        "Body_Back_3_L",
        "Body_Back_3_R",
        "Body_Back_1_L",
        "Body_Back_1_R",
        "Body_Back_Waist",
    ]
    return (
        _exact_name_candidates(slots, preferred)
        or score_slots(slots, ["body", "back"], optional_keywords=["torso"])
        or score_slots(slots, ["back"], optional_keywords=["body", "torso"])
    )


def _resolve_left_sleeve_candidates(slots: list[dict]) -> list[dict]:
    preferred = [
        "Shoulder_L",
        "Arm_Outside_1_L",
        "Arm_Outside_2_L",
        "Arm_Front_1_L",
        "Arm_Back_1_L",
        "Arm_Outside_3_L",
    ]
    return (
        _exact_name_candidates(slots, preferred)
        or _name_fragment_candidates(slots, ["arm", "_l"])
        or _name_fragment_candidates(slots, ["shoulder", "_l"])
        or score_slots(slots, ["left", "sleeve"], optional_keywords=["arm"])
    )


def _resolve_right_sleeve_candidates(slots: list[dict]) -> list[dict]:
    preferred = [
        "Shoulder_R",
        "Arm_Outside_1_R",
        "Arm_Outside_2_R",
        "Arm_Front_1_R",
        "Arm_Back_1_R",
        "Arm_Outside_3_R",
    ]
    return (
        _exact_name_candidates(slots, preferred)
        or _name_fragment_candidates(slots, ["arm", "_r"])
        or _name_fragment_candidates(slots, ["shoulder", "_r"])
        or score_slots(slots, ["right", "sleeve"], optional_keywords=["arm"])
    )


def _record_slot_snapshot(ctx, stage: str, arr_resp: dict, dbg: dict):
    slots = arr_resp.get("slots", []) if isinstance(arr_resp, dict) else []
    patterns = dbg.get("patterns", []) if isinstance(dbg, dict) else []
    snapshot = {
        "stage": stage,
        "slot_count": len(slots),
        "slot_payload": slots,
        "pattern_arrangement_count": len(patterns),
        "pattern_arrangements": patterns,
    }
    ctx.slot_diagnostics.append(snapshot)


def _query_slots(ctx, stage: str):
    arr_resp = ctx.client.get_arrangement_list()
    dbg = ctx.client.get_arrangement_debug()
    if (
        isinstance(arr_resp, dict)
        and not arr_resp.get("success", True)
        and isinstance(dbg, dict)
        and dbg.get("success")
        and dbg.get("slots")
    ):
        arr_resp = {
            "success": True,
            "count": len(dbg.get("slots", [])),
            "slots": dbg.get("slots", []),
            "source": "arrangement-debug-fallback",
        }
    elif (
        isinstance(arr_resp, dict)
        and not arr_resp.get("slots")
        and isinstance(dbg, dict)
        and dbg.get("success")
        and dbg.get("slots")
    ):
        arr_resp = {
            "success": True,
            "count": len(dbg.get("slots", [])),
            "slots": dbg.get("slots", []),
            "source": "arrangement-debug-fallback",
        }
    _record_slot_snapshot(ctx, stage=stage, arr_resp=arr_resp, dbg=dbg)
    return arr_resp, dbg


def _dxf_edge_count(dxf_path: Path):
    """Return the number of seam edges in a DXF pattern file.

    Current format: one closed LWPOLYLINE on the CutLine layer.  The vertex
    count is returned as an upper-bound estimate; CLO's own line-length probe
    (used in the primary path above) gives the authoritative count.

    Legacy format (POLYLINE): vertex count returned for backwards compat.
    """
    if ezdxf is None:
        return None
    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        # --- Current format: single closed LWPOLYLINE on CutLine ---
        lw = next(
            (e for e in msp
             if e.dxftype() == "LWPOLYLINE"
             and str(getattr(e.dxf, "layer", "")).lower() == "cutline"),
            None,
        )
        if lw is not None:
            n = len(list(lw.get_points("xy")))
            return n if n > 0 else None

        # --- Legacy format: single closed POLYLINE ---
        pl = next((e for e in msp if e.dxftype() == "POLYLINE"), None)
        if pl is not None:
            n = len(list(pl.vertices))
            return n if n > 0 else None

    except Exception:
        return None
    return None


def run(ctx):
    print("\n[6] Reading pattern edge data ...")
    edge_ok = True
    edge_capability_missing = False
    ctx.slot_fallback_mode = ""
    ctx.slot_diagnostics = []
    ctx.edge_counts = {}
    ctx.edge_sources = {}

    avatar_dbg = ctx.client.get_avatar_debug()
    if isinstance(avatar_dbg, dict) and avatar_dbg.get("success"):
        ctx.avatar_debug = avatar_dbg

    for idx in range(ctx.loaded_patterns):
        info = ctx.client.get_pattern_info(idx)
        name = info.get("info", {}).get("name", f"pattern_{idx}")
        line_count = info.get("info", {}).get("line_count")
        resolved_count = None
        source = ""

        if line_count is not None:
            try:
                resolved_count = int(line_count)
                source = "pattern_info"
            except Exception:
                resolved_count = None

        if resolved_count is None:
            probe = ctx.client.get_pattern_line_lengths(idx)
            probe_count = int(probe.get("line_count", 0)) if probe.get("success") else 0
            if probe_count > 0:
                resolved_count = probe_count
                source = "sdk_probe"

        if resolved_count is None:
            edge_capability_missing = True
            piece = ctx.index_to_piece.get(idx)
            if piece:
                dxf_count = _dxf_edge_count(ctx.patterns_dir / f"{piece}.dxf")
                if dxf_count and dxf_count > 0:
                    resolved_count = int(dxf_count)
                    source = "dxf_fallback"

        if resolved_count is None:
            print(f"  Pattern {idx}: {name}  (unknown edges)")
            ctx.edge_counts[str(idx)] = 0
            ctx.edge_sources[str(idx)] = "unknown"
        else:
            print(f"  Pattern {idx}: {name}  ({resolved_count} edges, source={source})")
            ctx.edge_counts[str(idx)] = int(resolved_count)
            ctx.edge_sources[str(idx)] = source
            if int(resolved_count) <= 0:
                edge_ok = False

        if resolved_count is None:
            edge_ok = False

    if edge_capability_missing:
        print("  Edge-count capability missing in SDK payload (line_count absent).")
        print("  Attempted SDK line-length probe and DXF fallback where possible.")

    # Validate CLO edge counts against the edge manifest (if one was loaded).
    if getattr(ctx, "edge_manifest", None):
        manifest_ok = validate_edge_counts(ctx)
        if not manifest_ok:
            print(
                "  Warning: edge count mismatch vs manifest — seam indices may be wrong. "
                "Verify DXF export and re-run."
            )

    print("\n[6b] Querying CLO arrangement slots ...")
    arr_resp, dbg = _query_slots(ctx, stage="post-import")

    if not arr_resp.get("slots"):
        print("  Slot warmup: arrangement list is empty, retrying with bounded warmup...")
        for attempt in range(1, SLOT_WARMUP_RETRIES + 1):
            if ctx.avatar_loaded:
                try:
                    ctx.client.simulate(steps=SLOT_WARMUP_SIM_STEPS)
                    ctx.client.wait_for_queue(timeout=20)
                except Exception:
                    pass
            arr_resp, dbg = _query_slots(ctx, stage=f"warmup-{attempt}")
            if arr_resp.get("slots"):
                print(f"  Slot warmup succeeded on retry {attempt}.")
                break

    ctx.slots = arr_resp.get("slots", [])

    if ctx.slots:
        for slot in ctx.slots:
            print(f"  Slot {slot.get('index', '?')}: {slot}")
    else:
        print("  No slots returned - avatar may not be loaded yet or CLO version")
        print("  doesn't populate arrangement list until after first simulate.")
        if dbg.get("success"):
            print(
                "  Arrangement debug - "
                f"slots:{dbg.get('slot_count', 0)} "
                f"patterns:{dbg.get('pattern_arrangement_count', 0)}"
            )

    front_candidates = _resolve_front_candidates(ctx.slots)
    back_candidates = _resolve_back_candidates(ctx.slots)
    left_candidates = _resolve_left_sleeve_candidates(ctx.slots)
    right_candidates = _resolve_right_sleeve_candidates(ctx.slots)

    ctx.slot_candidates = {
        "front": front_candidates,
        "back": back_candidates,
        "sleeve_L": left_candidates,
        "sleeve_R": right_candidates,
    }

    ctx.slot_map = {
        "front": front_candidates[0]["index"] if front_candidates else -1,
        "back": back_candidates[0]["index"] if back_candidates else -1,
        "sleeve_L": left_candidates[0]["index"] if left_candidates else -1,
        "sleeve_R": right_candidates[0]["index"] if right_candidates else -1,
    }

    print(
        "  Matched slots - "
        f"front:{ctx.slot_map['front']} back:{ctx.slot_map['back']} "
        f"sleeve_L:{ctx.slot_map['sleeve_L']} sleeve_R:{ctx.slot_map['sleeve_R']}"
    )

    print("  Slot scores - "
          f"front:{front_candidates[0]['score'] if front_candidates else 0} "
          f"back:{back_candidates[0]['score'] if back_candidates else 0} "
          f"sleeve_L:{left_candidates[0]['score'] if left_candidates else 0} "
          f"sleeve_R:{right_candidates[0]['score'] if right_candidates else 0}")

    slot_ok = all(ctx.slot_map.get(key, -1) >= 0 for key in ["front", "back", "sleeve_L", "sleeve_R"])
    if not slot_ok:
        arranged = ctx.client.get_pattern_arrangements().get("patterns", [])
        if len(arranged) >= ctx.expected_pattern_count:
            ctx.slot_fallback_mode = "pattern-arrangements-no-slots"
            slot_ok = True
            print("  Slot fallback enabled: using pattern-arrangements with direct offsets")
            print("  (arrangement slots unavailable in this CLO runtime)")

    ctx.edge_ok = edge_ok
    ctx.slot_ok = slot_ok

    if not edge_ok:
        print("  Edge validation failed - at least one pattern has missing/invalid edge data.")
        return False

    if not slot_ok:
        print("  Slot validation failed - required slots front/back/sleeve_L/sleeve_R were not resolved.")
        return False

    return True
