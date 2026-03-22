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
    """Calculated garment pattern measurements in centimeters."""

    # Body measurements
    body_height: float
    body_chest: float
    body_shoulder: float

    # Calculated garment dimensions (with ease)
    half_chest_width: float
    garment_length: float
    shoulder_width: float
    neck_width: float
    neck_depth_front: float
    neck_depth_back: float
    sleeve_length: float
    bicep_width: float
    armhole_depth: float
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
