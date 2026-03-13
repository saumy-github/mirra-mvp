"""Seed script to populate garments with baseline t-shirt data (flat schema)."""

from mirra_measurements.db import get_garments_collection, close_connection
from mirra_measurements import create_garment_doc, validate_garment_doc


# ---------------------------------------------------------------------------
# Seed data — flat schema: garment_id, fit_type, + 10 measurement fields
# ---------------------------------------------------------------------------
GARMENT_SEED_DATA = [
    # ── Male ────────────────────────────────────────────────────────────────
    {
        "garment_id": "001", "fit_type": "regular",
        "half_chest_width_cm": 52.0, "garment_length_cm": 71.0,
        "shoulder_width_cm": 46.0,   "neck_width_cm": 18.0,
        "neck_depth_front_cm": 9.0,  "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 21.0,    "bicep_width_cm": 18.0,
        "armhole_depth_cm": 24.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "002", "fit_type": "regular",
        "half_chest_width_cm": 49.0, "garment_length_cm": 68.0,
        "shoulder_width_cm": 43.0,   "neck_width_cm": 17.0,
        "neck_depth_front_cm": 8.5,  "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 20.0,    "bicep_width_cm": 17.0,
        "armhole_depth_cm": 23.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "003", "fit_type": "relaxed",
        "half_chest_width_cm": 56.0, "garment_length_cm": 74.0,
        "shoulder_width_cm": 49.0,   "neck_width_cm": 19.0,
        "neck_depth_front_cm": 9.5,  "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 22.0,    "bicep_width_cm": 20.0,
        "armhole_depth_cm": 26.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "004", "fit_type": "oversized",
        "half_chest_width_cm": 61.0, "garment_length_cm": 77.0,
        "shoulder_width_cm": 53.0,   "neck_width_cm": 20.0,
        "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 3.0,
        "sleeve_length_cm": 24.0,    "bicep_width_cm": 22.0,
        "armhole_depth_cm": 28.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "005", "fit_type": "slim",
        "half_chest_width_cm": 46.0, "garment_length_cm": 66.0,
        "shoulder_width_cm": 40.0,   "neck_width_cm": 16.0,
        "neck_depth_front_cm": 8.0,  "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 19.0,    "bicep_width_cm": 16.0,
        "armhole_depth_cm": 22.0,    "seam_allowance_cm": 1.0,
    },
    # ── Female ──────────────────────────────────────────────────────────────
    {
        "garment_id": "006", "fit_type": "regular",
        "half_chest_width_cm": 46.0, "garment_length_cm": 62.0,
        "shoulder_width_cm": 39.0,   "neck_width_cm": 17.0,
        "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 16.0,    "bicep_width_cm": 15.0,
        "armhole_depth_cm": 21.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "007", "fit_type": "slim",
        "half_chest_width_cm": 43.0, "garment_length_cm": 60.0,
        "shoulder_width_cm": 37.0,   "neck_width_cm": 16.0,
        "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 15.0,    "bicep_width_cm": 14.0,
        "armhole_depth_cm": 20.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "008", "fit_type": "relaxed",
        "half_chest_width_cm": 50.0, "garment_length_cm": 64.0,
        "shoulder_width_cm": 42.0,   "neck_width_cm": 18.0,
        "neck_depth_front_cm": 11.0, "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 17.0,    "bicep_width_cm": 16.5,
        "armhole_depth_cm": 23.0,    "seam_allowance_cm": 1.0,
    },
    # ── Unisex ──────────────────────────────────────────────────────────────
    {
        "garment_id": "009", "fit_type": "oversized",
        "half_chest_width_cm": 58.0, "garment_length_cm": 73.0,
        "shoulder_width_cm": 52.0,   "neck_width_cm": 19.0,
        "neck_depth_front_cm": 9.5,  "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 25.0,    "bicep_width_cm": 21.0,
        "armhole_depth_cm": 27.0,    "seam_allowance_cm": 1.0,
    },
    {
        "garment_id": "010", "fit_type": "regular",
        "half_chest_width_cm": 66.0, "garment_length_cm": 80.0,
        "shoulder_width_cm": 57.0,   "neck_width_cm": 21.0,
        "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 3.0,
        "sleeve_length_cm": 25.0,    "bicep_width_cm": 24.0,
        "armhole_depth_cm": 30.0,    "seam_allowance_cm": 1.0,
    },
]


def seed_garments(upsert: bool = True):
    """Insert or update all garment seed records in garments (flat schema)."""
    collection = get_garments_collection()
    inserted = updated = skipped = 0

    for raw in GARMENT_SEED_DATA:
        doc = create_garment_doc(
            garment_id=raw["garment_id"],
            fit_type=raw["fit_type"],
            half_chest_width_cm=raw["half_chest_width_cm"],
            garment_length_cm=raw["garment_length_cm"],
            shoulder_width_cm=raw["shoulder_width_cm"],
            neck_width_cm=raw["neck_width_cm"],
            neck_depth_front_cm=raw["neck_depth_front_cm"],
            neck_depth_back_cm=raw["neck_depth_back_cm"],
            sleeve_length_cm=raw["sleeve_length_cm"],
            bicep_width_cm=raw["bicep_width_cm"],
            armhole_depth_cm=raw["armhole_depth_cm"],
            seam_allowance_cm=raw["seam_allowance_cm"],
        )

        ok, err = validate_garment_doc(doc)
        if not ok:
            print(f"  ✗ {raw['garment_id']} — validation failed: {err}")
            skipped += 1
            continue

        if upsert:
            result = collection.update_one(
                {"garment_id": doc["garment_id"]},
                {"$set": doc},
                upsert=True,
            )
            if result.upserted_id:
                print(f"  ✓ inserted  {doc['garment_id']}  (fit={doc['fit_type']})")
                inserted += 1
            else:
                print(f"  ~ updated   {doc['garment_id']}  (fit={doc['fit_type']})")
                updated += 1
        else:
            collection.insert_one(doc)
            print(f"  ✓ inserted  {doc['garment_id']}  (fit={doc['fit_type']})")
            inserted += 1

    print(f"\n  inserted={inserted}  updated={updated}  skipped={skipped}")
    return inserted, updated, skipped


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("SEEDING garments (flat schema)")
    print("=" * 50)
    seed_garments()
    close_connection()
    print("Done.")
