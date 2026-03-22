"""Seed script to populate sizes with baseline t-shirt data (flat schema)."""

from mirra_measurements.db import get_sizes_collection, close_connection
from mirra_measurements import create_size_doc, validate_size_doc


# ---------------------------------------------------------------------------
# Seed data - flat schema: size_id, fit_type, + 10 measurement fields
# ---------------------------------------------------------------------------
SIZE_SEED_DATA = [
    {
        "size_id": "s_001", "fit_type": "regular",
        "half_chest_width_cm": 52.0, "garment_length_cm": 71.0,
        "shoulder_width_cm": 46.0, "neck_width_cm": 18.0,
        "neck_depth_front_cm": 9.0, "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 21.0, "bicep_width_cm": 18.0,
        "armhole_depth_cm": 24.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_002", "fit_type": "regular",
        "half_chest_width_cm": 49.0, "garment_length_cm": 68.0,
        "shoulder_width_cm": 43.0, "neck_width_cm": 17.0,
        "neck_depth_front_cm": 8.5, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 20.0, "bicep_width_cm": 17.0,
        "armhole_depth_cm": 23.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_003", "fit_type": "relaxed",
        "half_chest_width_cm": 56.0, "garment_length_cm": 74.0,
        "shoulder_width_cm": 49.0, "neck_width_cm": 19.0,
        "neck_depth_front_cm": 9.5, "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 22.0, "bicep_width_cm": 20.0,
        "armhole_depth_cm": 26.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_004", "fit_type": "oversized",
        "half_chest_width_cm": 61.0, "garment_length_cm": 77.0,
        "shoulder_width_cm": 53.0, "neck_width_cm": 20.0,
        "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 3.0,
        "sleeve_length_cm": 24.0, "bicep_width_cm": 22.0,
        "armhole_depth_cm": 28.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_005", "fit_type": "slim",
        "half_chest_width_cm": 46.0, "garment_length_cm": 66.0,
        "shoulder_width_cm": 40.0, "neck_width_cm": 16.0,
        "neck_depth_front_cm": 8.0, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 19.0, "bicep_width_cm": 16.0,
        "armhole_depth_cm": 22.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_006", "fit_type": "regular",
        "half_chest_width_cm": 46.0, "garment_length_cm": 62.0,
        "shoulder_width_cm": 39.0, "neck_width_cm": 17.0,
        "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 16.0, "bicep_width_cm": 15.0,
        "armhole_depth_cm": 21.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_007", "fit_type": "slim",
        "half_chest_width_cm": 43.0, "garment_length_cm": 60.0,
        "shoulder_width_cm": 37.0, "neck_width_cm": 16.0,
        "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 2.0,
        "sleeve_length_cm": 15.0, "bicep_width_cm": 14.0,
        "armhole_depth_cm": 20.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_008", "fit_type": "relaxed",
        "half_chest_width_cm": 50.0, "garment_length_cm": 64.0,
        "shoulder_width_cm": 42.0, "neck_width_cm": 18.0,
        "neck_depth_front_cm": 11.0, "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 17.0, "bicep_width_cm": 16.5,
        "armhole_depth_cm": 23.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_009", "fit_type": "oversized",
        "half_chest_width_cm": 58.0, "garment_length_cm": 73.0,
        "shoulder_width_cm": 52.0, "neck_width_cm": 19.0,
        "neck_depth_front_cm": 9.5, "neck_depth_back_cm": 2.5,
        "sleeve_length_cm": 25.0, "bicep_width_cm": 21.0,
        "armhole_depth_cm": 27.0, "seam_allowance_cm": 1.0,
    },
    {
        "size_id": "s_010", "fit_type": "regular",
        "half_chest_width_cm": 66.0, "garment_length_cm": 80.0,
        "shoulder_width_cm": 57.0, "neck_width_cm": 21.0,
        "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 3.0,
        "sleeve_length_cm": 25.0, "bicep_width_cm": 24.0,
        "armhole_depth_cm": 30.0, "seam_allowance_cm": 1.0,
    },
]


def seed_sizes(upsert: bool = True):
    """Insert or update all size seed records in sizes."""
    collection = get_sizes_collection()
    inserted = updated = skipped = 0

    for raw in SIZE_SEED_DATA:
        doc = create_size_doc(
            size_id=raw["size_id"],
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

        ok, err = validate_size_doc(doc)
        if not ok:
            print(f"  x {raw['size_id']} - validation failed: {err}")
            skipped += 1
            continue

        if upsert:
            result = collection.update_one(
                {"size_id": doc["size_id"]},
                {"$set": doc},
                upsert=True,
            )
            if result.upserted_id:
                print(f"  inserted {doc['size_id']} (fit={doc['fit_type']}, cloth={doc.get('cloth_id', 'n/a')})")
                inserted += 1
            else:
                print(f"  updated  {doc['size_id']} (fit={doc['fit_type']}, cloth={doc.get('cloth_id', 'n/a')})")
                updated += 1
        else:
            collection.insert_one(doc)
            print(f"  inserted {doc['size_id']} (fit={doc['fit_type']}, cloth={doc.get('cloth_id', 'n/a')})")
            inserted += 1

    print(f"\n  inserted={inserted}  updated={updated}  skipped={skipped}")
    return inserted, updated, skipped


# Legacy alias kept while older references still exist in the repo.
seed_garments = seed_sizes


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("SEEDING sizes (flat schema)")
    print("=" * 50)
    seed_sizes()
    close_connection()
    print("Done.")
