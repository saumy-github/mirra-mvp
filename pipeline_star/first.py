#!/usr/bin/env python3
import sys
import os
import argparse
from typing import Dict, Any, List
import numpy as np

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from mirra_measurements.db import get_measurements_collection
from pipeline_star.star_runner import generate_default_mesh
from pipeline_star.fit_betas import fit_betas_to_measurements, predict_measurements_from_betas


REQUIRED_FIELDS = [
    'user_id',
    'gender',
    'height_cm',
    'weight_kg',
    'shoulder_width_cm',
    'chest_circumference_cm',
    'waist_circumference_cm',
    'hip_circumference_cm',
    'leg_length_cm',
]

MEASUREMENT_RANGES = {
    'height_cm': (120, 220),
    'weight_kg': (30, 200),
    'shoulder_width_cm': (25, 70),
    'chest_circumference_cm': (60, 150),
    'waist_circumference_cm': (40, 160),
    'hip_circumference_cm': (60, 160),
    'leg_length_cm': (50, 130),
}


# Fetch user measurement document from MongoDB
def fetch_user_measurements(user_id: str, version: int = 1) -> Dict[str, Any]:
    collection = get_measurements_collection()
    doc = collection.find_one({"user_id": user_id})
    if doc is None:
        raise ValueError(f"No measurements found for user_id: {user_id}")
    return doc


# Validate all required fields are present
def validate_required_fields(doc: Dict[str, Any]) -> None:
    missing_fields: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in doc or doc[field] is None:
            missing_fields.append(field)
    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(missing_fields)}\n"
            f"Cannot generate avatar without complete measurement data."
        )


# Validate measurements are within plausible ranges
def validate_measurement_ranges(doc: Dict[str, Any]) -> None:
    out_of_range: List[str] = []
    
    for field, (min_val, max_val) in MEASUREMENT_RANGES.items():
        if field in doc and doc[field] is not None:
            value = doc[field]
            if value < min_val or value > max_val:
                out_of_range.append(
                    f"{field}: {value:.1f} (expected {min_val}-{max_val})"
                )
    
    if out_of_range:
        raise ValueError(
            f"Measurements out of plausible range:\n" +
            "\n".join(f"  - {item}" for item in out_of_range) +
            f"\nPlease verify measurement data before generating avatar."
        )


# Print formatted summary of user measurements
def print_measurements_summary(doc: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("MEASUREMENT SUMMARY")
    print("=" * 60)
    print(f"User ID:              {doc['user_id']}")
    print(f"Gender:               {doc['gender']}")
    print(f"Height:               {doc['height_cm']:.1f} cm")
    print(f"Weight:               {doc['weight_kg']:.1f} kg")
    print(f"Shoulder Width:       {doc['shoulder_width_cm']:.1f} cm")
    print(f"Chest Circumference:  {doc['chest_circumference_cm']:.1f} cm")
    print(f"Waist Circumference:  {doc['waist_circumference_cm']:.1f} cm")
    print(f"Hip Circumference:    {doc['hip_circumference_cm']:.1f} cm")
    print(f"Leg Length:           {doc['leg_length_cm']:.1f} cm")
    print("=" * 60 + "\n")


# Print formatted mesh statistics
def print_mesh_stats(mesh_data: Dict[str, Any]) -> None:
    vertices = mesh_data['vertices']
    faces = mesh_data['faces']
    
    print("\n" + "=" * 60)
    print("STAR MESH STATISTICS")
    print("=" * 60)
    print(f"Gender:        {mesh_data['gender']}")
    print(f"Num Betas:     {mesh_data['num_betas']}")
    print(f"Vertex Count:  {vertices.shape[0]:,}")
    print(f"Face Count:    {faces.shape[0]:,}")
    print(f"Vertex Shape:  {vertices.shape}")
    print(f"Face Shape:    {faces.shape}")
    print("=" * 60 + "\n")


# Main CLI entry point for STAR pipeline
def main():
    parser = argparse.ArgumentParser(
        description="Fetch and validate user measurements from MongoDB, "
                    "optionally generate STAR mesh or fit betas"
    )
    parser.add_argument(
        "--user_id", 
        required=True, 
        help="User ID to fetch measurements for"
    )
    parser.add_argument(
        "--version", 
        type=int, 
        default=1, 
        help="Version number (default: 1, reserved for future use)"
    )
    parser.add_argument(
        "--mode", 
        choices=['validate_only', 'star_preflight', 'fit_betas'], 
        default='validate_only', 
        help="Operation mode: validate_only (default), star_preflight (generate mesh), "
             "or fit_betas (optimize shape)"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"Fetching measurements for user_id: {args.user_id}...")
        doc = fetch_user_measurements(args.user_id, args.version)
        
        print("Validating required fields...")
        validate_required_fields(doc)
        
        print("Validating measurement ranges...")
        validate_measurement_ranges(doc)
        
        print_measurements_summary(doc)
        print("✓ All required fields present and valid")
        print("✓ All measurements within plausible ranges")
        
        if args.mode == 'star_preflight':
            print("\n" + "=" * 60)
            print("STAR PREFLIGHT MODE: Generating test mesh")
            print("=" * 60)
            
            gender = doc['gender']
            print(f"\nLoading STAR model (gender={gender}, num_betas=10)...")
            mesh_data = generate_default_mesh(gender=gender, num_betas=10)
            print("✓ Mesh generated successfully")
            
            print_mesh_stats(mesh_data)
            
            print("✓ STAR mesh generation complete")
            print("  (No files saved in Phase 1 - preflight only)")
        
        elif args.mode == 'fit_betas':
            print("\n" + "=" * 60)
            print("FIT BETAS MODE: Optimizing STAR shape parameters")
            print("=" * 60)
            
            gender = doc['gender']
            
            target_measurements = {
                'height_cm': doc['height_cm'],
                'shoulder_width_cm': doc['shoulder_width_cm'],
                'chest_circumference_cm': doc['chest_circumference_cm'],
                'waist_circumference_cm': doc['waist_circumference_cm'],
                'hip_circumference_cm': doc['hip_circumference_cm'],
            }
            
            print("\nComputing initial predictions (betas=zeros)...")
            initial_betas = np.zeros(10)
            
            # Compute initial scale using same logic as fitter (height matching)
            temp_pred = predict_measurements_from_betas(
                gender, initial_betas, scale=1.0, num_betas=10, debug=False
            )
            default_height = temp_pred.get('height_cm', 170.0)
            target_height = target_measurements['height_cm']
            initial_scale = target_height / default_height if default_height > 0 else 1.0
            
            initial_measurements = predict_measurements_from_betas(
                gender, initial_betas, scale=initial_scale, num_betas=10, debug=False
            )
            
            fitting_result = fit_betas_to_measurements(
                target_measurements, gender, num_betas=10, use_scale=True
            )
            
            print("\n" + "=" * 60)
            print("SANITY COMPARISON TABLE")
            print("=" * 60)
            print(f"{'Measurement':<25s} {'Target':>10s} {'Initial':>10s} {'%Error':>8s} "
                  f"{'Final':>10s} {'%Error':>8s}")
            print("-" * 80)
            
            pred_measurements = fitting_result['predicted_measurements']
            measurement_fields = [
                'height_cm', 
                'shoulder_width_cm', 
                'chest_circumference_cm', 
                'waist_circumference_cm', 
                'hip_circumference_cm'
            ]
            
            for field in measurement_fields:
                if (field in target_measurements and 
                    field in initial_measurements and 
                    field in pred_measurements):
                    
                    target = target_measurements[field]
                    initial = initial_measurements[field]
                    final = pred_measurements[field]
                    
                    initial_error_pct = ((initial - target) / target * 100) if target > 0 else 0.0
                    final_error_pct = ((final - target) / target * 100) if target > 0 else 0.0
                    
                    field_name = field.replace('_cm', '').replace('_', ' ').title()
                    
                    print(f"{field_name:<25s} {target:10.2f} {initial:10.2f} "
                          f"{initial_error_pct:>7.2f}% {final:10.2f} {final_error_pct:>7.2f}%")
            print("=" * 60)
            
            print("\n✓ Beta fitting complete")
            print(f"  Final betas: {fitting_result['betas']}")
            print(f"  Final scale: {fitting_result['scale']:.4f}")
            print(f"  Final loss: {fitting_result['loss']:.6f}")
            print(f"  Iterations: {fitting_result['iterations']}")
            print("  (No files saved in Phase 2 - fitting only)")
        
        return 0
        
    except ValueError as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
