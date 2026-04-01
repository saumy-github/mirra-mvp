"""Shared helpers for Step 3 modules."""

import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parents[2]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from product_ingestion.run_manifest import get_latest_panels_dxf_dir


def resolve_patterns_dir():
    """Find the latest canonical panels/dxf directory."""
    try:
        return Path(get_latest_panels_dxf_dir())
    except FileNotFoundError:
        return workspace_root / "product_ingestion" / "output" / "panels" / "dxf"


def print_result(result, label):
    """Print one command result line and return success bool."""
    ok = result.get("success", False)
    sym = "[OK]" if ok else "[FAIL]"
    msg = result.get("message", result.get("error", str(result)))
    print(f"  {sym} {label}: {msg}")
    return ok


def find_slot(slots, keywords):
    """Find arrangement slot index by keyword match across slot fields."""
    for slot in slots:
        blob = " ".join(str(value) for value in slot.values()).lower()
        if all(keyword.lower() in blob for keyword in keywords):
            return int(slot.get("index", -1))
    return -1


def score_slots(slots, required_keywords, optional_keywords=None):
    """Score arrangement slots by keyword evidence and return ranked candidates.

    Each candidate is {'index': int, 'score': int, 'slot': dict}.
    """
    optional_keywords = optional_keywords or []
    ranked = []
    for slot in slots:
        blob = " ".join(str(v) for v in slot.values()).lower()
        score = 0
        for kw in required_keywords:
            if kw.lower() in blob:
                score += 10
        for kw in optional_keywords:
            if kw.lower() in blob:
                score += 3

        # Small preference for explicit arrangement names if present.
        name_blob = str(slot.get("name", "")).lower()
        for kw in required_keywords:
            if kw.lower() in name_blob:
                score += 2

        idx = int(slot.get("index", -1))
        if idx >= 0 and score > 0:
            ranked.append({"index": idx, "score": score, "slot": slot})

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked
