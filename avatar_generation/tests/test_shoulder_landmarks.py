#!/usr/bin/env python3
"""Test the new shoulder landmark measurement function."""
import sys
import os
import numpy as np

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from avatar_generation.star_runner import generate_default_mesh
from avatar_generation.mesh_measure import (
    extract_shoulder_width_from_mesh,
    extract_shoulder_landmarks_from_mesh,
)

# Load J_regressor from STAR model
model_path = os.path.join(repo_root, 'models', 'star_1_1', 'male', 'model.npz')
data = np.load(model_path, allow_pickle=True)
j_regressor = data['J_regressor']

# Generate default male mesh
print("Generating default male mesh...")
mesh_data = generate_default_mesh('male')
vertices = mesh_data['vertices']

print("\n" + "=" * 80)
print("SHOULDER WIDTH COMPARISON")
print("=" * 80)

# Old method (flawed - includes arms)
old_width = extract_shoulder_width_from_mesh(vertices, debug=True)
print(f"\nOLD METHOD (max X-range in band): {old_width:.2f} cm")
print("  ^ This includes arms, not just shoulder joints")

# New method (correct - uses anatomical landmarks)
new_width = extract_shoulder_landmarks_from_mesh(vertices, j_regressor, debug=True)
print(f"\nNEW METHOD (anatomical landmarks): {new_width:.2f} cm")
print("  ^ This is the true anatomical shoulder width")

print("\n" + "=" * 80)
print("RESULT")
print("=" * 80)
print(f"Difference: {old_width - new_width:.2f} cm")
print(f"Old/New ratio: {old_width / new_width:.2f}x")
print("\nFor u_001 (target shoulder width: 45.0 cm):")
print(f"  - Old method error: ~{abs(old_width - 45.0) / 45.0 * 100:.1f}%")
print(f"  - New method error: ~{abs(new_width - 45.0) / 45.0 * 100:.1f}%")
print("\nNew method should be much closer to 45 cm!")
