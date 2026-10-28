"""Face photos -> face.glb. The one entry point the worker and the CLI share."""
from __future__ import annotations

from pathlib import Path

from .glb import to_glb
from .landmarks import observe
from .reconstruct import reconstruct

VIEWS = ("front", "left", "right")


def reconstruct_face(photos: dict[str, str | Path]) -> tuple[bytes, dict]:
    """photos: {"front": path, "left"?: path, "right"?: path} — left/right are the
    head turned ~45° towards the subject's left/right. Returns (glb bytes, info).

    A side photo where no face is found is dropped with a warning; the front
    photo is required."""
    if "front" not in photos:
        raise ValueError("a front face photo is required")
    observations, warnings = [], []
    for view in VIEWS:
        if view not in photos:
            continue
        try:
            observations.append(observe(photos[view], view))
        except RuntimeError as exc:
            if view == "front":
                raise
            warnings.append(f"{exc}; it was left out")
    face = reconstruct(observations)
    face.warnings[:0] = warnings
    info = {
        "views": face.views,
        "scale_source": face.scale_source,
        "skin_tone_hex": face.skin_tone_hex,
        "warnings": face.warnings,
        "width_cm": round(float(face.vertices[:, 0].ptp()) * 100, 1),
    }
    return to_glb(face), info
