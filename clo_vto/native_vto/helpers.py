"""Shared helpers for Step 3 modules."""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

workspace_root = Path(__file__).resolve().parents[2]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from product_ingestion.run_manifest import get_latest_panels_dxf_dir

_LINE = "═" * 56

# Module-level active logger, set once per pipeline run via set_logger().
# A module-level reference (rather than threading `ctx`/`logger` through every
# call site across all 12 step files) keeps this a minimal-diff addition —
# there is only ever one active VTO pipeline per process. Falls back to
# print-only behavior (unchanged from before) if never set, e.g. in ad-hoc
# scripts or tests that call these helpers directly.
_logger: Optional[logging.Logger] = None


def set_logger(logger: Optional[logging.Logger]) -> None:
    """Register the active run logger so step_header/footer/print_result tee to it."""
    global _logger
    _logger = logger


def step_header(
    step_num: int,
    step_name: str,
    extras: dict | None = None,
) -> float:
    """Print a step banner with optional key path info and return start timestamp.

    extras is an ordered dict of {label: value} lines printed between the two
    separator bars.  Use it to surface the key file paths and EXISTS checks for
    the step so the reader can diagnose problems without opening source code.
    """
    print(f"\n{_LINE}")
    print(f"[STEP {step_num:02d}] {step_name}")
    if extras:
        width = max(len(k) for k in extras)
        for key, val in extras.items():
            print(f"  {key:<{width}} : {val}")
    print(_LINE)
    if _logger:
        _logger.info("[STEP %02d] %s starting%s", step_num, step_name,
                      f" ({extras})" if extras else "")
    return time.monotonic()


def step_footer(step_num: int, start_time: float, ok: bool, reason: str = "") -> None:
    """Print a step completion/failure line with elapsed time."""
    elapsed = time.monotonic() - start_time
    if ok:
        print(f"[STEP {step_num:02d}] ✓  completed in {elapsed:.1f}s")
        if _logger:
            _logger.info("[STEP %02d] completed in %.1fs", step_num, elapsed)
    else:
        tail = f" — {reason}" if reason else ""
        print(f"[STEP {step_num:02d}] ✗  FAILED{tail}  ({elapsed:.1f}s)")
        if _logger:
            _logger.error("[STEP %02d] FAILED%s (%.1fs)", step_num, tail, elapsed)


def resolve_patterns_dir():
    """Find the latest canonical panels/dxf directory."""
    try:
        return Path(get_latest_panels_dxf_dir())
    except FileNotFoundError:
        return workspace_root / "product_ingestion" / "output" / "panels" / "dxf"


def ensure_avatar_visible_checked(ctx, label: str, avatar_index: int = -1) -> None:
    """Re-assert avatar visibility (Bug 2 fix) and log before/after state into ctx.

    Records a before/after IsShowAvatar readback under
    ctx.avatar_visibility_debug[label] so a regression is visible in the
    pipeline report, not just discoverable by eyeballing the CLO window. Never
    raises or blocks the pipeline — this is defensive insurance, not a gate;
    if the plugin capability isn't available yet (older plugin build), the
    calls simply report failure and that failure is logged, not escalated.
    See .agent/clo-avatar-vto/vto-pipeline-debug-plan-26_7_24.md, Bug 2.
    """
    before = ctx.client.get_avatar_visible(0 if avatar_index < 0 else avatar_index)
    ensure_result = ctx.client.ensure_avatar_visible(avatar_index)
    print_result(ensure_result, f"ensure-avatar-visible ({label})")
    after = ctx.client.get_avatar_visible(0 if avatar_index < 0 else avatar_index)

    ctx.avatar_visibility_debug[label] = {
        "before_visible": before.get("visible") if before.get("success") else None,
        "after_visible": after.get("visible") if after.get("success") else None,
        "ensure_call_ok": bool(ensure_result.get("success")),
    }
    print(f"    avatar visible: before={before.get('visible')!r} -> after={after.get('visible')!r}")


def print_result(result, label):
    """Print one command result line and return success bool."""
    ok = result.get("success", False)
    sym = "[OK]" if ok else "[FAIL]"
    msg = result.get("message", result.get("error", str(result)))
    print(f"  {sym} {label}: {msg}")
    if _logger:
        if ok:
            _logger.info("%s: %s", label, msg)
        else:
            _logger.error("%s: %s", label, msg)
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
