"""Shared helpers for step modules."""

from pathlib import Path


def resolve_patterns_dir():
    """Find the latest run_NNN/patterns_dxf directory."""
    workspace_root = Path(__file__).resolve().parents[3]
    base = workspace_root / "2d_patterned_garment_generation_clo3d/output"
    if not base.exists():
        return base / "patterns_dxf"

    runs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: int(d.name.split("_")[1])
        if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit()
        else 0,
    )
    return (runs[-1] / "patterns_dxf") if runs else (base / "patterns_dxf")


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
        blob = " ".join(str(v) for v in slot.values()).lower()
        if all(k.lower() in blob for k in keywords):
            return int(slot.get("index", -1))
    return -1
