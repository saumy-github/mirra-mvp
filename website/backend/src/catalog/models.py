"""Catalog schema — ported from mirra_measurements/size_model.py.

Reads the existing sizes collection (written by the Step 2 pipeline and the
seed script) — flat schema, one doc per size_id:
    size_id, fit_type, the 12 measurement fields below (all cm; the last two
    are optional and read back as null on documents seeded before them),
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
    # Full flat taper widths. Optional in the schema, so documents seeded
    # before these existed report them as null rather than being omitted.
    "hem_width_cm",
    "wrist_width_cm",
)

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20
