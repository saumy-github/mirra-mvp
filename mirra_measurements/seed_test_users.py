"""Seed u_011..u_015 into the measurements collection for pipeline testing.

Separate from seed_measurements.py so re-running this never rewrites the
golden users. Bodies are realistic and mutually distinct; u_014 and u_015
share a height on purpose, so a run that swaps them stays detectable.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mirra_measurements import create_measurement_doc, validate_measurement_doc  # noqa: E402
from mirra_measurements.db import get_measurements_collection, close_connection  # noqa: E402

TEST_USERS = [
    dict(user_id="u_011", gender="male", accuracy="accurate",
         height_cm=168.0, weight_kg=62.0, shoulder_width_cm=42.0,
         chest_circumference_cm=92.0, waist_circumference_cm=76.0,
         hip_circumference_cm=92.0, leg_length_cm=79.0,
         body_shape_type="rectangle", skin_tone_hex="#C68642"),
    dict(user_id="u_012", gender="male", accuracy="accurate",
         height_cm=175.0, weight_kg=72.0, shoulder_width_cm=44.5,
         chest_circumference_cm=98.0, waist_circumference_cm=82.0,
         hip_circumference_cm=96.0, leg_length_cm=83.0,
         body_shape_type="trapezoid", skin_tone_hex="#8D5524"),
    dict(user_id="u_013", gender="male", accuracy="accurate",
         height_cm=181.0, weight_kg=88.0, shoulder_width_cm=47.0,
         chest_circumference_cm=106.0, waist_circumference_cm=92.0,
         hip_circumference_cm=104.0, leg_length_cm=86.0,
         body_shape_type="oval", skin_tone_hex="#E0AC69"),
    # u_014 and u_015 share height_cm=186.0 — every other field differs.
    dict(user_id="u_014", gender="male", accuracy="accurate",
         height_cm=186.0, weight_kg=79.0, shoulder_width_cm=46.0,
         chest_circumference_cm=100.0, waist_circumference_cm=84.0,
         hip_circumference_cm=98.0, leg_length_cm=90.0,
         body_shape_type="rectangle", skin_tone_hex="#F1C27D"),
    dict(user_id="u_015", gender="male", accuracy="accurate",
         height_cm=186.0, weight_kg=95.0, shoulder_width_cm=49.0,
         chest_circumference_cm=112.0, waist_circumference_cm=98.0,
         hip_circumference_cm=108.0, leg_length_cm=88.0,
         body_shape_type="oval", skin_tone_hex="#5C3836"),
]


def seed():
    collection = get_measurements_collection()
    for fields in TEST_USERS:
        doc = create_measurement_doc(**fields)
        is_valid, error = validate_measurement_doc(doc)
        if not is_valid:
            print(f"  {fields['user_id']}: INVALID -> {error}")
            continue
        result = collection.update_one(
            {"user_id": fields["user_id"]}, {"$set": doc}, upsert=True
        )
        action = "inserted" if result.upserted_id else "updated"
        print(f"  {fields['user_id']}: {action}  "
              f"H={fields['height_cm']} C={fields['chest_circumference_cm']} "
              f"W={fields['waist_circumference_cm']} Hip={fields['hip_circumference_cm']} "
              f"Leg={fields['leg_length_cm']} Sh={fields['shoulder_width_cm']}")


if __name__ == "__main__":
    print("Seeding test users u_011..u_015 into `measurements`...")
    try:
        seed()
    finally:
        close_connection()
    print("Done.")
