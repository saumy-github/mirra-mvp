"""Seed script to populate cloths — one document per input/c_XXX/ folder.

Demo data (doc 13, D3): five cloths, all offered in the same ten shared
sizes. A second brand would later get its own cloths pointing at its own
size ids; nothing about the shape changes.
"""

from mirra_measurements.db import get_cloths_collection, get_sizes_collection, close_connection
from mirra_measurements import create_cloth_doc, validate_cloth_doc


SHARED_SIZE_IDS = [f"s_{n:03d}" for n in range(1, 11)]

CLOTH_SEED_DATA = [
    {"cloth_id": "c_001", "label": "Classic Tee",    "category": "top"},
    {"cloth_id": "c_002", "label": "Graphic Tee",    "category": "top"},
    {"cloth_id": "c_003", "label": "Striped Tee",    "category": "top"},
    {"cloth_id": "c_004", "label": "Pocket Tee",     "category": "top"},
    {"cloth_id": "c_005", "label": "Oversized Tee",  "category": "top"},
]


def seed_cloths(upsert: bool = True):
    """Insert or update all cloth seed records in cloths."""
    sizes = get_sizes_collection()
    known_size_ids = {doc["size_id"] for doc in sizes.find({}, {"size_id": 1, "_id": 0})}

    collection = get_cloths_collection()
    inserted = updated = skipped = 0

    for raw in CLOTH_SEED_DATA:
        doc = create_cloth_doc(
            cloth_id=raw["cloth_id"],
            label=raw["label"],
            size_ids=SHARED_SIZE_IDS,
            category=raw["category"],
        )

        is_valid, reason = validate_cloth_doc(doc, known_size_ids=known_size_ids)
        if not is_valid:
            print(f"  SKIPPED {raw['cloth_id']}: {reason}")
            skipped += 1
            continue

        existing = collection.find_one({"cloth_id": doc["cloth_id"]})
        if existing:
            if not upsert:
                print(f"  SKIPPED {doc['cloth_id']} (already exists)")
                skipped += 1
                continue
            doc["created_at"] = existing.get("created_at", doc["created_at"])
            collection.replace_one({"cloth_id": doc["cloth_id"]}, doc)
            updated += 1
            print(f"  updated  {doc['cloth_id']} ({doc['label']}, {len(doc['size_ids'])} sizes)")
        else:
            collection.insert_one(doc)
            inserted += 1
            print(f"  inserted {doc['cloth_id']} ({doc['label']}, {len(doc['size_ids'])} sizes)")

    print(f"\nCloths: {inserted} inserted, {updated} updated, {skipped} skipped.")
    return inserted, updated, skipped


def main():
    print("\nSeeding cloths")
    print("-" * 50)
    if not get_sizes_collection().count_documents({}):
        print("  The sizes collection is empty — run seed_sizes first.")
        return 1
    seed_cloths()
    close_connection()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
