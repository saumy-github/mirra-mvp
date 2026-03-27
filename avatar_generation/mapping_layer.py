"""Mapping layer: Mongo measurement document to inputs.json + fitting targets."""

import sys
import os
from typing import Dict, Any, Tuple
from datetime import datetime

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from mirra_measurements.db import get_measurements_collection
from avatar_generation.run_manifest import RunIdentity
from avatar_generation.artifact_io import write_inputs_json, get_timestamp
from avatar_generation.artifact_schema import (
    create_inputs_schema,
    FITTING_MEASUREMENT_FIELDS,
    VALIDATE_ONLY_FIELDS,
    FITNESS_TOLERANCE_PERCENT
)
from avatar_generation.pose_catalog import get_apose_metadata, get_apose_thetas


# Fetch user measurement document from MongoDB
def fetch_user_measurements(user_id: str) -> Dict[str, Any]:
    collection = get_measurements_collection()
    doc = collection.find_one({"user_id": user_id})
    if doc is None:
        raise ValueError(f"No measurements found for user_id: {user_id}")
    return doc


# Validate required fields for MVP (gender-specific)
def validate_required_fields(doc: Dict[str, Any]) -> None:
    gender = doc.get('gender')
    if not gender:
        raise ValueError("Field 'gender' is required")
    
    # Base fields for both genders
    base_fields = ['user_id', 'gender', 'height_cm', 'weight_kg', 'shoulder_width_cm', 
                   'waist_circumference_cm', 'hip_circumference_cm', 'leg_length_cm']
    
    # Gender-specific chest/bust fields
    if gender == 'male':
        chest_fields = ['chest_circumference_cm']
    elif gender == 'female':
        chest_fields = ['bust_circumference_cm', 'under_bust_circumference_cm']
    else:
        raise ValueError(f"Invalid gender: {gender}. Expected 'male' or 'female'")
    
    required_fields = base_fields + chest_fields
    
    missing_fields = []
    for field in required_fields:
        if field not in doc or doc[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(missing_fields)}\n"
            f"Cannot generate avatar without complete measurement data."
        )


# Validate measurements are within plausible ranges
def validate_measurement_ranges(doc: Dict[str, Any]) -> None:
    measurement_ranges = {
        'height_cm': (120, 220),
        'weight_kg': (30, 200),
        'shoulder_width_cm': (25, 70),
        'chest_circumference_cm': (60, 150),
        'bust_circumference_cm': (60, 150),
        'under_bust_circumference_cm': (55, 140),
        'waist_circumference_cm': (40, 160),
        'hip_circumference_cm': (60, 160),
        'leg_length_cm': (50, 130),
    }
    
    out_of_range = []
    
    for field, (min_val, max_val) in measurement_ranges.items():
        if field in doc and doc[field] is not None:
            value = doc[field]
            if value < min_val or value > max_val:
                out_of_range.append(
                    f"{field}: {value:.1f} (expected {min_val}-{max_val})"
                )
    
    if out_of_range:
        raise ValueError(
            f"Measurements out of plausible range:\n" +
            "\n".join(f"  - {item}" for item in out_of_range)
        )


# Create derived fitting targets for MVP (gender-aware: map bust to chest for females)
def create_fitting_targets(doc: Dict[str, Any]) -> Dict[str, float]:
    gender = doc['gender']
    
    base_targets = {
        'height_cm': float(doc['height_cm']),
        'shoulder_width_cm': float(doc['shoulder_width_cm']),
        'waist_circumference_cm': float(doc['waist_circumference_cm']),
        'hip_circumference_cm': float(doc['hip_circumference_cm']),
    }
    
    if gender == 'male':
        base_targets['chest_circumference_cm'] = float(doc['chest_circumference_cm'])
    elif gender == 'female':
        # Map bust to chest for STAR model (Option A: use bust directly)
        base_targets['chest_circumference_cm'] = float(doc['bust_circumference_cm'])
    else:
        raise ValueError(f"Unsupported gender: {gender}")
    
    return base_targets


# Create run configuration
def create_run_config(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'tolerance_percent': FITNESS_TOLERANCE_PERCENT,
        'gated_fields': FITTING_MEASUREMENT_FIELDS,
        'validate_only_fields': VALIDATE_ONLY_FIELDS,
        'gender': doc['gender'],
        'num_betas': 10,
        'scale_enabled': True,
    }


# Convert MongoDB document to JSON-serializable snapshot
def sanitize_mongo_snapshot(doc: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = {}
    for k, v in doc.items():
        if k == '_id':
            continue
        if isinstance(v, datetime):
            snapshot[k] = v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        else:
            snapshot[k] = v
    return snapshot


# Map Mongo measurement document to inputs.json + fitting targets
def create_mapping_layer_output(
    user_id: str,
    run_number: int
) -> Tuple[RunIdentity, Dict[str, Any], Dict[str, float], str]:
    run_id = RunIdentity(user_id=user_id, number=run_number)
    
    doc = fetch_user_measurements(user_id)
    validate_required_fields(doc)
    validate_measurement_ranges(doc)
    
    mongo_snapshot = sanitize_mongo_snapshot(doc)
    
    fitting_targets = create_fitting_targets(doc)
    
    config = create_run_config(doc)
    
    pose_metadata = get_apose_metadata()
    
    inputs_data = create_inputs_schema(
        run_id=run_id.run_id,
        created_at=get_timestamp(),
        user_id=user_id,
        mongo_snapshot=mongo_snapshot,
        derived_targets=fitting_targets,
        config=config
    )
    
    inputs_file_path = write_inputs_json(run_id, inputs_data)
    
    return run_id, mongo_snapshot, fitting_targets, inputs_file_path

