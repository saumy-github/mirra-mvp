"""
Seed script to populate the measurements collection with test data.
"""

from datetime import datetime
from mirra_measurements.db import get_measurements_collection, close_connection
from mirra_measurements.models import create_measurement_doc, validate_measurement_doc
from mirra_measurements.golden_users import GOLDEN_USER_IDS, GOLDEN_USER_PRIORITY


def get_seed_data():
    """
    Generate seed data for measurements.
    Returns list of 10 measurement documents (5 male, 5 female).
    """
    measurements = []
    
    # MALE MEASUREMENTS
    # Male 1 - Fully filled, accurate
    doc = create_measurement_doc(
        user_id="user_m_001",
        gender="male",
        accuracy="accurate",
        height_cm=178.5,
        weight_kg=75.2,
        shoulder_width_cm=45.0,
        waist_circumference_cm=85.0,
        hip_circumference_cm=98.0,
        leg_length_cm=90.0,
        chest_circumference_cm=100.0,
        body_shape_type="rectangle",
        skin_tone_hex="#8D5524"
    )
    doc['is_golden'] = True
    doc['golden_priority'] = 1
    measurements.append(doc)
    
    # Male 2 - Fully filled, approx
    doc = create_measurement_doc(
        user_id="user_m_002",
        gender="male",
        accuracy="approx",
        height_cm=182.0,
        weight_kg=82.5,
        shoulder_width_cm=47.5,
        waist_circumference_cm=90.0,
        hip_circumference_cm=102.0,
        leg_length_cm=93.0,
        chest_circumference_cm=105.0,
        body_shape_type="inverted_triangle",
        skin_tone_hex="#C58C85"
    )
    doc['is_golden'] = True
    doc['golden_priority'] = 2
    measurements.append(doc)
    
    # Male 3 - Missing hip, leg_length, skin_tone
    doc = create_measurement_doc(
        user_id="user_m_003",
        gender="male",
        accuracy="accurate",
        height_cm=175.0,
        weight_kg=70.0,
        shoulder_width_cm=43.0,
        waist_circumference_cm=82.0,
        chest_circumference_cm=96.0,
        body_shape_type="rectangle"
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    # Male 4 - Missing chest, body_shape_type, shoulder_width
    doc = create_measurement_doc(
        user_id="user_m_004",
        gender="male",
        accuracy="accurate",
        height_cm=180.0,
        weight_kg=78.0,
        waist_circumference_cm=88.0,
        hip_circumference_cm=100.0,
        leg_length_cm=91.5,
        skin_tone_hex="#F1C27D"
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    # Male 5 - Minimal (only height and weight)
    doc = create_measurement_doc(
        user_id="user_m_005",
        gender="male",
        accuracy="accurate",
        height_cm=177.0,
        weight_kg=73.0
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    # FEMALE MEASUREMENTS
    # Female 1 - Fully filled, accurate
    doc = create_measurement_doc(
        user_id="user_f_001",
        gender="female",
        accuracy="accurate",
        height_cm=165.0,
        weight_kg=58.5,
        shoulder_width_cm=38.0,
        waist_circumference_cm=68.0,
        hip_circumference_cm=95.0,
        leg_length_cm=85.0,
        bust_circumference_cm=90.0,
        under_bust_circumference_cm=75.0,
        body_shape_type="hourglass",
        skin_tone_hex="#FFDFC4"
    )
    doc['is_golden'] = True
    doc['golden_priority'] = 3
    measurements.append(doc)
    
    # Female 2 - Fully filled, approx
    doc = create_measurement_doc(
        user_id="user_f_002",
        gender="female",
        accuracy="approx",
        height_cm=170.0,
        weight_kg=62.0,
        shoulder_width_cm=39.5,
        waist_circumference_cm=70.0,
        hip_circumference_cm=97.0,
        leg_length_cm=88.0,
        bust_circumference_cm=92.0,
        under_bust_circumference_cm=76.0,
        body_shape_type="pear",
        skin_tone_hex="#E0AC69"
    )
    doc['is_golden'] = True
    doc['golden_priority'] = 4
    measurements.append(doc)
    
    # Female 3 - Missing under_bust, skin_tone, leg_length
    doc = create_measurement_doc(
        user_id="user_f_003",
        gender="female",
        accuracy="accurate",
        height_cm=162.0,
        weight_kg=55.0,
        shoulder_width_cm=37.0,
        waist_circumference_cm=65.0,
        hip_circumference_cm=92.0,
        bust_circumference_cm=88.0,
        body_shape_type="rectangle"
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    # Female 4 - Missing bust measurements, body_shape_type
    doc = create_measurement_doc(
        user_id="user_f_004",
        gender="female",
        accuracy="accurate",
        height_cm=168.0,
        weight_kg=60.0,
        shoulder_width_cm=38.5,
        waist_circumference_cm=72.0,
        hip_circumference_cm=98.0,
        leg_length_cm=87.0,
        skin_tone_hex="#5C4033"
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    # Female 5 - Minimal (only height and weight)
    doc = create_measurement_doc(
        user_id="user_f_005",
        gender="female",
        accuracy="accurate",
        height_cm=163.0,
        weight_kg=56.0
    )
    doc['is_golden'] = False
    doc['golden_priority'] = None
    measurements.append(doc)
    
    return measurements


def seed_database():
    """
    Seed the measurements collection with test data.
    Uses upsert to avoid duplicates on re-run.
    """
    print("=" * 60)
    print("Seeding measurements collection...")
    print("=" * 60)
    
    collection = get_measurements_collection()
    measurements = get_seed_data()
    
    upserted_ids = []
    inserted_count = 0
    updated_count = 0
    golden_users = []
    
    for doc in measurements:
        # Validate before inserting
        is_valid, error = validate_measurement_doc(doc)
        if not is_valid:
            print(f"❌ Validation failed for {doc['user_id']}: {error}")
            continue
        
        # Upsert by user_id
        result = collection.update_one(
            {"user_id": doc["user_id"]},
            {"$set": doc},
            upsert=True
        )
        
        upserted_ids.append(doc["user_id"])
        
        if doc.get('is_golden'):
            golden_users.append((doc['user_id'], doc.get('golden_priority')))
        
        golden_tag = f" [GOLDEN-{doc.get('golden_priority')}]" if doc.get('is_golden') else ""
        
        if result.upserted_id:
            inserted_count += 1
            print(f"✓ Inserted: {doc['user_id']} ({doc['gender']}, {doc['accuracy']}){golden_tag}")
        else:
            updated_count += 1
            print(f"↻ Updated:  {doc['user_id']} ({doc['gender']}, {doc['accuracy']}){golden_tag}")
    
    print("=" * 60)
    print(f"Summary:")
    print(f"  - Total processed: {len(upserted_ids)}")
    print(f"  - Newly inserted: {inserted_count}")
    print(f"  - Updated existing: {updated_count}")
    print(f"  - User IDs: {', '.join(upserted_ids)}")
    print(f"  - Golden users: {len(golden_users)}")
    for user_id, priority in golden_users:
        print(f"    • {user_id} (priority: {priority})")
    print("=" * 60)
    print(f"\nDatabase: mirratest")
    print(f"Collection: measurements")
    print(f"Total documents in collection: {collection.count_documents({})}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        seed_database()
    finally:
        close_connection()
        print("\n✓ Connection closed")
