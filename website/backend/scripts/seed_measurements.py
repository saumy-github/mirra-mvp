"""Dev seed for the measurements collection — relocated from
mirra_measurements/seed_measurements.py, same 10 docs (5 male, 5 female),
same golden flags, same upsert-by-user_id behaviour.

Run from website/backend:  ../../.venv/Scripts/python.exe scripts/seed_measurements.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_settings  # noqa: E402

from golden_users import GOLDEN_USER_PRIORITY  # noqa: E402

BASE = {
    "u_001": dict(gender="male", accuracy="accurate", height_cm=178.5, weight_kg=75.2,
                  shoulder_width_cm=45.0, waist_circumference_cm=85.0, hip_circumference_cm=98.0,
                  leg_length_cm=90.0, chest_circumference_cm=100.0, body_shape_type="rectangle",
                  skin_tone_hex="#8D5524"),
    "u_002": dict(gender="male", accuracy="approx", height_cm=182.0, weight_kg=82.5,
                  shoulder_width_cm=47.5, waist_circumference_cm=90.0, hip_circumference_cm=102.0,
                  leg_length_cm=93.0, chest_circumference_cm=105.0, body_shape_type="inverted_triangle",
                  skin_tone_hex="#C58C85"),
    "u_003": dict(gender="male", accuracy="accurate", height_cm=175.0, weight_kg=70.0,
                  shoulder_width_cm=43.0, waist_circumference_cm=82.0, chest_circumference_cm=96.0,
                  body_shape_type="rectangle"),
    "u_004": dict(gender="male", accuracy="accurate", height_cm=180.0, weight_kg=78.0,
                  waist_circumference_cm=88.0, hip_circumference_cm=100.0, leg_length_cm=91.5,
                  skin_tone_hex="#F1C27D"),
    "u_005": dict(gender="male", accuracy="accurate", height_cm=177.0, weight_kg=73.0),
    "u_006": dict(gender="female", accuracy="accurate", height_cm=165.0, weight_kg=58.5,
                  shoulder_width_cm=38.0, waist_circumference_cm=68.0, hip_circumference_cm=95.0,
                  leg_length_cm=85.0, bust_circumference_cm=90.0, under_bust_circumference_cm=75.0,
                  body_shape_type="hourglass", skin_tone_hex="#FFDFC4"),
    "u_007": dict(gender="female", accuracy="approx", height_cm=170.0, weight_kg=62.0,
                  shoulder_width_cm=39.5, waist_circumference_cm=70.0, hip_circumference_cm=97.0,
                  leg_length_cm=88.0, bust_circumference_cm=92.0, under_bust_circumference_cm=76.0,
                  body_shape_type="pear", skin_tone_hex="#E0AC69"),
    "u_008": dict(gender="female", accuracy="accurate", height_cm=162.0, weight_kg=55.0,
                  shoulder_width_cm=37.0, waist_circumference_cm=65.0, hip_circumference_cm=92.0,
                  bust_circumference_cm=88.0, body_shape_type="rectangle"),
    "u_009": dict(gender="female", accuracy="accurate", height_cm=168.0, weight_kg=60.0,
                  shoulder_width_cm=38.5, waist_circumference_cm=72.0, hip_circumference_cm=98.0,
                  leg_length_cm=87.0, skin_tone_hex="#5C4033"),
    "u_010": dict(gender="female", accuracy="accurate", height_cm=163.0, weight_kg=56.0),
}


def main():
    settings = get_settings()
    col = MongoClient(settings.mongodb_uri)[settings.database_name]["measurements"]
    now = datetime.now(timezone.utc)
    inserted = updated = 0
    for user_id, fields in BASE.items():
        doc = {
            "user_id": user_id,
            **fields,
            "is_golden": user_id in GOLDEN_USER_PRIORITY,
            "golden_priority": GOLDEN_USER_PRIORITY.get(user_id),
            "created_at": now,
            "updated_at": now,
        }
        result = col.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
        if result.upserted_id:
            inserted += 1
            print(f"inserted {user_id} ({fields['gender']}, {fields['accuracy']})")
        else:
            updated += 1
            print(f"updated  {user_id} ({fields['gender']}, {fields['accuracy']})")
    print(f"\ninserted={inserted} updated={updated}  (db={settings.database_name})")


if __name__ == "__main__":
    main()
