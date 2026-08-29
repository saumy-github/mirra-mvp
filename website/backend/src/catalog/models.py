"""Catalog's Mongo document shape — ported from mirra_measurements/size_model.py.
See schemas.py for pagination — this module has no request-body schemas
(public GET endpoints, query params only).

Reads the existing sizes collection (written by the Step 2 pipeline and the
seed script) — flat schema, one doc per size_id:
    size_id, fit_type, the 12 measurement fields below (all cm; the last two
    are optional and read back as null on documents seeded before them),
    optional cloth metadata (cloth_id, cloth_label, category),
    created_at, updated_at

Read-only service: garments are produced by product_ingestion (Step 2),
never created through this API.
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
    # Full flat taper widths. Optional in the schema, so documents seeded
    # before these existed report them as null rather than being omitted.
    "hem_width_cm",
    "wrist_width_cm",
)


VALID_CATEGORIES = ("top", "bottom", "outerwear", "footwear", "accessory")


class ClothDocument(BaseModel):
    """The `cloths` collection doc shape — one per input/c_XXX/ folder.

    A cloth names the sizes it is offered in; a size does not name a cloth,
    so two brands can use entirely different measurements while a single
    brand's cloths share one chart. See doc 13 section 47.
    """

    cloth_id: str
    label: str
    category: str = "top"
    size_ids: list[str] = []
    brand_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
    hem_width_cm: float | None = None
    wrist_width_cm: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
