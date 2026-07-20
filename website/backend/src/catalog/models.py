"""Catalog schema — ported from mirra_measurements/size_model.py.

Reads the existing sizes collection (written by the Step 2 pipeline and the
seed script) — flat schema, one doc per size_id:
    size_id, fit_type, the 10 measurement fields below (all cm),
    optional cloth metadata (cloth_id, cloth_label, category),
    created_at, updated_at

Read-only service: garments are produced by product_ingestion (Step 2),
never created through this API.
"""

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

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20
