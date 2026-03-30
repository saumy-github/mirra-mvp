"""Garment measurement types used by the ingestion pipeline.

This module extracts the minimal `GarmentMeasurements` dataclass (and a
lightweight `AvatarMeasurements`) so run-time code doesn't need to import the
full `generate_patterns_clo3d.py` legacy script.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

HAS_DB = False
get_sizes_collection = None
try:
    from mirra_measurements.db import get_sizes_collection  # type: ignore
    HAS_DB = True
except Exception:
    HAS_DB = False

@dataclass
class GarmentMeasurements:
    """Calculated garment pattern measurements in centimeters.

    Measurement conventions (IMPORTANT — read before adding new fields)
    -------------------------------------------------------------------
    All width/girth fields use the FLAT SEAM-TO-SEAM (half-girth) convention:

      half_chest_width  — half the full chest circumference.
                          One body panel = this width.  Front + Back together
                          form the full tube (2 × half_chest_width).

      shoulder_width    — half the full shoulder span, measured from centre-
                          back to shoulder point.  Matches half_chest_width
                          convention so edge algebra is consistent.

      bicep_width       — flat seam-to-seam measurement of the FOLDED sleeve
                          (= half the bicep tube circumference).
                          Pattern generators must multiply by 2 to get the
                          UNFOLDED sleeve piece width (full tube circumference).
                          Do NOT store the full circumference here — the *2
                          factor is applied in panels.py generate_sleeve().

    All other linear measurements (garment_length, sleeve_length, armhole_depth,
    neck_width, neck_depth_*) are absolute values in centimetres with no
    halving convention.
    """

    # Body measurements
    body_height: float
    body_chest: float
    body_shoulder: float

    # Calculated garment dimensions (with ease)
    # See class docstring for the half-girth convention on width fields.
    half_chest_width: float    # half chest girth (one panel width), cm
    garment_length: float      # full torso length hem-to-shoulder, cm
    shoulder_width: float      # half shoulder span (centre to shoulder point), cm
    neck_width: float          # full neck opening width, cm
    neck_depth_front: float    # front neckline drop from shoulder line, cm
    neck_depth_back: float     # back neckline drop from shoulder line, cm
    sleeve_length: float       # full sleeve length cuff-to-underarm, cm
    bicep_width: float         # flat half-girth of folded sleeve (× 2 = unfolded), cm
    armhole_depth: float       # depth of armhole opening on body panel, cm
    seam_allowance: float = 1.0

    # Fit details
    ease_cm: float = 0
    fit_type: str = "regular"

    @classmethod
    def from_sizes_db(cls, size_id: str) -> "GarmentMeasurements":
        if not HAS_DB:
            raise RuntimeError(
                "pymongo is not installed. Cannot load from database.\n"
                "Install it with: pip install pymongo python-dotenv"
            )
        col = get_sizes_collection()
        doc = col.find_one({"size_id": size_id}, {"_id": 0})
        if doc is None:
            available = [d["size_id"] for d in col.find({}, {"size_id": 1, "_id": 0}).sort("size_id", 1)]
            raise ValueError(
                f"size_id='{size_id}' not found in sizes collection.\n"
                f"Available IDs: {', '.join(available) if available else 'none — run seed first'}"
            )

        return cls(
            body_height=175.0,
            body_chest=0.0,
            body_shoulder=doc["shoulder_width_cm"],
            half_chest_width=doc["half_chest_width_cm"],
            garment_length=doc["garment_length_cm"],
            shoulder_width=doc["shoulder_width_cm"],
            neck_width=doc["neck_width_cm"],
            neck_depth_front=doc["neck_depth_front_cm"],
            neck_depth_back=doc["neck_depth_back_cm"],
            sleeve_length=doc["sleeve_length_cm"],
            bicep_width=doc["bicep_width_cm"],
            armhole_depth=doc["armhole_depth_cm"],
            seam_allowance=doc.get("seam_allowance_cm", 1.0),
            fit_type=doc.get("fit_type", "regular"),
            ease_cm=0.0,
        )
