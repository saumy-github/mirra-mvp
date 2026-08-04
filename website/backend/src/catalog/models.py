"""Catalog's Mongo document shape — ported from mirra_measurements/size_model.py.
See schemas.py for pagination — this module has no request-body schemas
(public GET endpoints, query params only).

Reads the existing sizes collection (written by the Step 2 pipeline and the
seed script) — flat schema, one doc per size_id. Read-only service: garments
are produced by product_ingestion (Step 2), never created through this API.
"""

from datetime import datetime

from pydantic import BaseModel

VALID_FIT_TYPES = ("slim", "regular", "relaxed", "oversized")

# Order matches size_model.SIZE_MEASUREMENT_FIELDS for easy diffing.
SIZE_MEASUREMENT_FIELDS = (
    "half_chest_width_cm",
    "garment_length_cm",
    "shoulder_width_cm",
    "neck_width_cm",
    "neck_depth_front_cm",
    "neck_depth_back_cm",
    "sleeve_length_cm",
    "bicep_width_cm",
    "armhole_depth_cm",
    "seam_allowance_cm",
)


class SizeDocument(BaseModel):
    """The `sizes` collection doc shape. No validation constraints beyond
    type — this is a read-only mirror of an externally-owned pipeline doc,
    so being lenient here beats a stray field breaking garment browsing."""

    size_id: str
    fit_type: str
    cloth_id: str | None = None
    cloth_label: str | None = None
    category: str | None = None
    half_chest_width_cm: float | None = None
    garment_length_cm: float | None = None
    shoulder_width_cm: float | None = None
    neck_width_cm: float | None = None
    neck_depth_front_cm: float | None = None
    neck_depth_back_cm: float | None = None
    sleeve_length_cm: float | None = None
    bicep_width_cm: float | None = None
    armhole_depth_cm: float | None = None
    seam_allowance_cm: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
