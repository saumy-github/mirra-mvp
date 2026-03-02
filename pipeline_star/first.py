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
from pipeline_star.star_runner import generate_default_mesh, generate_mesh
from pipeline_star.fit_betas import fit_betas_to_measurements, predict_measurements_from_betas
from pipeline_star.mapping_layer import create_mapping_layer_output
from pipeline_star.artifact_io import write_values_json, get_timestamp
from pipeline_star.artifact_schema import create_values_schema, FITNESS_TOLERANCE_PERCENT
from pipeline_star.pose_catalog import get_apose_thetas, get_apose_metadata
from pipeline_star.avatar_exporter import export_mesh_to_glb
from pipeline_star.avatar_exporter_clo import export_avatar_for_clo
from pipeline_star.run_manifest import get_avatar_glb_path
from pipeline_star.mesh_postprocess import postprocess_mesh
from pipeline_star.avatar_style import get_material_config


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
        "--run_number", 
        type=int, 
        help="Run number for generate_avatar mode (e.g., 1 for user_m_001-001)"
    )
    parser.add_argument(
        "--mode", 
        choices=['validate_only', 'star_preflight', 'fit_betas', 'generate_avatar'], 
        default='validate_only', 
        help="Operation mode: validate_only (default), star_preflight (generate mesh), "
             "fit_betas (optimize shape), or generate_avatar (complete run with inputs/values/GLB)"
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
        
        elif args.mode == 'generate_avatar':
            if args.run_number is None:
                print("\n✗ ERROR: --run_number is required for generate_avatar mode", file=sys.stderr)
                return 1
            
            print("\n" + "=" * 60)
            print("GENERATE AVATAR MODE: Complete run bundle")
            print("=" * 60)
            
            try:
                print("\n[1/5] Mapping layer: validating and writing inputs JSON...")
                run_id, mongo_snapshot, fitting_targets, inputs_file = create_mapping_layer_output(
                    user_id=args.user_id,
                    run_number=args.run_number
                )
                print(f"✓ Inputs JSON written: {inputs_file}")
                
                gender = mongo_snapshot['gender']
                
                print("\n[2/5] Fitting betas to target measurements...")
                fitting_result = fit_betas_to_measurements(
                    fitting_targets, gender, num_betas=10, use_scale=True
                )
                print(f"✓ Fitting complete (loss={fitting_result['loss']:.6f}, iterations={fitting_result['iterations']})")
                
                print("\n[3/5] Computing errors and determining pass/fail status...")
                predicted = fitting_result['predicted_measurements']
                errors_percent = {}
                max_error = 0.0
                
                for field in fitting_targets.keys():
                    target = fitting_targets[field]
                    pred = predicted[field]
                    error_pct = abs((pred - target) / target * 100) if target > 0 else 0.0
                    errors_percent[field] = error_pct
                    max_error = max(max_error, error_pct)
                
                passed_gate = max_error <= FITNESS_TOLERANCE_PERCENT
                status = 'passed' if passed_gate else 'failed'
                
                print(f"  Max error: {max_error:.2f}%")
                print(f"  Tolerance: {FITNESS_TOLERANCE_PERCENT}%")
                print(f"  Status: {status.upper()}")
                
                print("\n[4/5] Writing values JSON...")
                
                pose_size = 72
                thetas = get_apose_thetas(pose_size).tolist()
                
                fit_report = {
                    'predicted_measurements': predicted,
                    'errors_percent': errors_percent,
                    'loss': float(fitting_result['loss']),
                    'iterations': int(fitting_result['iterations']),
                    'max_error_percent': float(max_error),
                    'passed_gate': bool(passed_gate),
                }
                
                values_data = create_values_schema(
                    run_id=run_id.run_id,
                    created_at=get_timestamp(),
                    status=status,
                    inputs_file=os.path.basename(inputs_file),
                    betas=fitting_result['betas'].tolist(),
                    thetas=thetas,
                    scale=float(fitting_result['scale']),
                    pose_metadata=get_apose_metadata(),
                    fit_report=fit_report
                )
                
                values_file = write_values_json(run_id, values_data)
                print(f"✓ Values JSON written: {values_file}")
                
                print("\n[5/5] Exporting GLB file...")
                
                mesh_data = generate_mesh(
                    gender=gender,
                    betas=fitting_result['betas'],
                    pose=get_apose_thetas(pose_size),
                    scale=fitting_result['scale'],
                    num_betas=10
                )
                
                processed_mesh = postprocess_mesh(
                    vertices=mesh_data['vertices'],
                    faces=mesh_data['faces'],
                    validate_arrays=True,
                    recenter=False,
                    apply_smoothing=False
                )
                
                glb_path = get_avatar_glb_path(run_id)
                export_mesh_to_glb(
                    vertices=processed_mesh['vertices'],
                    faces=processed_mesh['faces'],
                    output_glb_path=glb_path,
                    material_config=get_material_config()
                )
                print(f"✓ GLB exported: {glb_path}")
                
                # Also export OBJ for CLO3D integration
                clo_export_result = export_avatar_for_clo(
                    vertices=processed_mesh['vertices'],
                    faces=processed_mesh['faces'],
                    measurements=doc,
                    output_directory=os.path.join(os.path.dirname(glb_path), 'clo_avatars'),
                    user_id=user_id,
                    run_number=run_number
                )
                print(f"✓ CLO3D OBJ exported: {clo_export_result['obj_file']}")
                
                # Enhanced terminal feedback based on status
                print("\n" + "=" * 60)
                if status == 'failed':
                    print("❌ AVATAR GENERATION FAILED")
                    print("=" * 60)
                    print(f"The following measurements exceeded {FITNESS_TOLERANCE_PERCENT}% tolerance:")
                    
                    # Show failed measurements
                    failed_measurements = []
                    for field, error_pct in errors_percent.items():
                        if error_pct > FITNESS_TOLERANCE_PERCENT:
                            field_name = field.replace('_cm', '').replace('_', ' ').title()
                            failed_measurements.append((field_name, error_pct))
                    
                    # Sort by error percentage (highest first)
                    failed_measurements.sort(key=lambda x: x[1], reverse=True)
                    
                    for field_name, error_pct in failed_measurements:
                        print(f"  • {field_name}: {error_pct:.2f}% error")
                    
                    print(f"\nGLB file exported for debugging: {os.path.basename(glb_path)}")
                    print("Review the values JSON for detailed fit report.")
                else:
                    print("✅ AVATAR GENERATION SUCCESSFUL")
                    print("=" * 60)
                    print(f"All measurements within {FITNESS_TOLERANCE_PERCENT}% tolerance")
                    print(f"Ready for Blender import: {os.path.basename(glb_path)}")
                
                print("=" * 60)
                print(f"Run ID: {run_id.run_id}")
                print(f"Files generated:")
                print(f"  - {os.path.basename(inputs_file)}")
                print(f"  - {os.path.basename(values_file)}")
                print(f"  - {os.path.basename(glb_path)}")
                print("=" * 60)
                
            except Exception as e:
                print(f"\n✗ Avatar generation failed: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return 2
        
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
