"""Dev seed for the sizes collection — relocated from
mirra_measurements/seed_sizes.py, same 10 flat size docs, upsert by size_id.

Run from website/backend:  ../../.venv/Scripts/python.exe scripts/seed_sizes.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_settings  # noqa: E402

SIZE_SEED_DATA = [
    {"size_id": "s_001", "fit_type": "regular", "half_chest_width_cm": 52.0, "garment_length_cm": 71.0,
     "shoulder_width_cm": 46.0, "neck_width_cm": 18.0, "neck_depth_front_cm": 9.0, "neck_depth_back_cm": 2.5,
     "sleeve_length_cm": 21.0, "bicep_width_cm": 18.0, "armhole_depth_cm": 24.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_002", "fit_type": "regular", "half_chest_width_cm": 49.0, "garment_length_cm": 68.0,
     "shoulder_width_cm": 43.0, "neck_width_cm": 17.0, "neck_depth_front_cm": 8.5, "neck_depth_back_cm": 2.0,
     "sleeve_length_cm": 20.0, "bicep_width_cm": 17.0, "armhole_depth_cm": 23.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_003", "fit_type": "relaxed", "half_chest_width_cm": 56.0, "garment_length_cm": 74.0,
     "shoulder_width_cm": 49.0, "neck_width_cm": 19.0, "neck_depth_front_cm": 9.5, "neck_depth_back_cm": 2.5,
     "sleeve_length_cm": 22.0, "bicep_width_cm": 20.0, "armhole_depth_cm": 26.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_004", "fit_type": "oversized", "half_chest_width_cm": 61.0, "garment_length_cm": 77.0,
     "shoulder_width_cm": 53.0, "neck_width_cm": 20.0, "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 3.0,
     "sleeve_length_cm": 24.0, "bicep_width_cm": 22.0, "armhole_depth_cm": 28.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_005", "fit_type": "slim", "half_chest_width_cm": 46.0, "garment_length_cm": 66.0,
     "shoulder_width_cm": 40.0, "neck_width_cm": 16.0, "neck_depth_front_cm": 8.0, "neck_depth_back_cm": 2.0,
     "sleeve_length_cm": 19.0, "bicep_width_cm": 16.0, "armhole_depth_cm": 22.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_006", "fit_type": "regular", "half_chest_width_cm": 46.0, "garment_length_cm": 62.0,
     "shoulder_width_cm": 39.0, "neck_width_cm": 17.0, "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 2.0,
     "sleeve_length_cm": 16.0, "bicep_width_cm": 15.0, "armhole_depth_cm": 21.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_007", "fit_type": "slim", "half_chest_width_cm": 43.0, "garment_length_cm": 60.0,
     "shoulder_width_cm": 37.0, "neck_width_cm": 16.0, "neck_depth_front_cm": 10.0, "neck_depth_back_cm": 2.0,
     "sleeve_length_cm": 15.0, "bicep_width_cm": 14.0, "armhole_depth_cm": 20.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_008", "fit_type": "relaxed", "half_chest_width_cm": 50.0, "garment_length_cm": 64.0,
     "shoulder_width_cm": 42.0, "neck_width_cm": 18.0, "neck_depth_front_cm": 11.0, "neck_depth_back_cm": 2.5,
     "sleeve_length_cm": 17.0, "bicep_width_cm": 16.5, "armhole_depth_cm": 23.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_009", "fit_type": "oversized", "half_chest_width_cm": 58.0, "garment_length_cm": 73.0,
     "shoulder_width_cm": 52.0, "neck_width_cm": 19.0, "neck_depth_front_cm": 9.5, "neck_depth_back_cm": 2.5,
     "sleeve_length_cm": 25.0, "bicep_width_cm": 21.0, "armhole_depth_cm": 27.0, "seam_allowance_cm": 1.0},
    {"size_id": "s_010", "fit_type": "regular", "half_chest_width_cm": 66.0, "garment_length_cm": 80.0,
     "shoulder_width_cm": 57.0, "neck_width_cm": 21.0, "neck_depth_front_cm": 10.5, "neck_depth_back_cm": 3.0,
     "sleeve_length_cm": 25.0, "bicep_width_cm": 24.0, "armhole_depth_cm": 30.0, "seam_allowance_cm": 1.0},
]


def main():
    settings = get_settings()
    col = MongoClient(settings.mongodb_uri)[settings.database_name]["sizes"]
    now = datetime.now(timezone.utc)
    inserted = updated = 0
    for raw in SIZE_SEED_DATA:
        doc = {**raw, "created_at": now, "updated_at": now}
        result = col.update_one({"size_id": doc["size_id"]}, {"$set": doc}, upsert=True)
        if result.upserted_id:
            inserted += 1
            print(f"inserted {doc['size_id']} (fit={doc['fit_type']})")
        else:
            updated += 1
            print(f"updated  {doc['size_id']} (fit={doc['fit_type']})")
    print(f"\ninserted={inserted} updated={updated}  (db={settings.database_name})")


if __name__ == "__main__":
    main()
