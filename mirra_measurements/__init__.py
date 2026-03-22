"""
Mirra Measurements DB - Standalone MongoDB module for storing user body measurements.
"""

__version__ = "0.1.0"

# ── Avatar (body) model ─────────────────────────────────────────────────────
from mirra_measurements.avatar_model import (
    create_measurement_doc,
    validate_measurement_doc,
    VALID_GENDERS,
    VALID_ACCURACIES,
    REQUIRED_FIELDS,
    NUMERIC_FIELDS,
    STRING_FIELDS,
)

# ── Garment model ────────────────────────────────────────────────────────────
from mirra_measurements.size_model import (
    create_size_doc,
    validate_size_doc,
    VALID_FIT_TYPES,
    SIZE_MEASUREMENT_FIELDS,
)

# Legacy aliases kept while older Step 2 helpers still exist.
create_garment_doc = create_size_doc
validate_garment_doc = validate_size_doc
GARMENT_MEASUREMENT_FIELDS = SIZE_MEASUREMENT_FIELDS
