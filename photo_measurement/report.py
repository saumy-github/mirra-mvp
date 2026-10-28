"""Measurements -> Mirra body profile (the backend's field names) and a plain-text report."""
from __future__ import annotations

import numpy as np

from .capture import Observation

# Mirra profile field -> measurement key produced by measure.extract
PROFILE_FIELDS = {
    "height_cm": "height",
    "shoulder_width_cm": "shoulder_width",
    "waist_circumference_cm": "waist",
    "hip_circumference_cm": "hip",
    "leg_length_cm": "inseam",
    "chest_circumference_cm": "chest",
    "bust_circumference_cm": "bust",
    "under_bust_circumference_cm": "under_bust",
}


def body_shape_type(bust: float, waist: float, hip: float) -> str:
    """Common five-shape rule set on bust/waist/hip girths."""
    if waist >= 0.95 * min(bust, hip):
        return "apple"
    if abs(bust - hip) <= 0.05 * hip and waist <= 0.75 * min(bust, hip):
        return "hourglass"
    if bust - hip > 0.05 * hip:
        return "inverted_triangle"
    if hip - bust > 0.05 * bust:
        return "pear"
    return "rectangle"


def skin_tone_hex(front: Observation) -> str | None:
    """Median colour of two cheek patches (between nose and ears, slightly below)."""
    if front.image is None:
        return None
    nose = front.pt("nose")
    h, w = front.mask.shape
    pixels = []
    for side in ("left", "right"):
        ear = front.pt(f"{side}_ear")
        span = float(np.linalg.norm(ear - nose))
        c = nose + 0.45 * (ear - nose) + np.array([0, 0.15 * span])
        r = max(2, int(0.12 * span))
        x0, x1 = max(0, int(c[0]) - r), min(w, int(c[0]) + r + 1)
        y0, y1 = max(0, int(c[1]) - r), min(h, int(c[1]) + r + 1)
        patch, inside = front.image[y0:y1, x0:x1], front.mask[y0:y1, x0:x1]
        pixels.append(patch[inside])
    px = np.concatenate(pixels) if pixels else np.empty((0, 3))
    if len(px) < 10:
        return None
    r, g, b = np.median(px, axis=0).astype(int)
    return f"#{r:02X}{g:02X}{b:02X}"


def to_profile(result: dict, front: Observation | None = None, weight_kg: float | None = None) -> dict:
    m = result["measurements"]
    profile = {field: m.get(key) for field, key in PROFILE_FIELDS.items()}
    profile["weight_kg"] = weight_kg  # not measurable from photos; passed through from user input
    if all(m.get(k) for k in ("bust", "waist", "hip")):
        profile["body_shape_type"] = body_shape_type(m["bust"], m["waist"], m["hip"])
    else:
        profile["body_shape_type"] = None
    profile["skin_tone_hex"] = skin_tone_hex(front) if front is not None else None
    return profile


def format_text(result: dict, profile: dict) -> str:
    lines = ["MIRRA BODY MEASUREMENTS", "=" * 44, "", "Profile (backend fields)", "-" * 44]
    for k, v in profile.items():
        lines.append(f"  {k:30s} {'—' if v is None else v}")
    mode = ("learned model: " + ", ".join(result["model"]) if result.get("model")
            else "calibrated" if result.get("calibrated") else "UNCALIBRATED")
    lines += ["", f"All measurements ({result['unit']}, {mode})",
              "-" * 44]
    for k, v in result["measurements"].items():
        cm = f"{v:6.1f} cm  {v / 2.54:5.1f} in"
        lines.append(f"  {k:20s} {cm}   [{result['methods'][k]}]")
    if result["warnings"]:
        lines += ["", "WARNINGS (fix the capture before trusting numbers)", "-" * 44]
        lines += [f"  ! {w}" for w in result["warnings"]]
    return "\n".join(lines)
