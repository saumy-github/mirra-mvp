"""Shared helpers for Step 3 modules."""

import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parents[3]
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
    sym = "\u2713" if ok else "\u2717"
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
