#!/usr/bin/env python3
"""Inspect STAR model to find shoulder joint indices."""
import sys
import os
import numpy as np

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from avatar_generation.star_runner import generate_default_mesh

# Load STAR model data
model_path = os.path.join(repo_root, 'models', 'star_1_1', 'male', 'model.npz')
data = np.load(model_path, allow_pickle=True)

print("=" * 80)
print("STAR MODEL INSPECTION")
print("=" * 80)
print("\nAvailable keys in model file:")
for key in sorted(data.keys()):
    print(f"  - {key}: {type(data[key])} {data[key].shape if hasattr(data[key], 'shape') else ''}")

print("\n" + "=" * 80)
print("KINEMATIC TREE (kintree_table)")
print("=" * 80)
kintree = data['kintree_table']
print(f"Shape: {kintree.shape}")
print("\nKinematic tree (parent-child relationships):")
print(kintree)

print("\n" + "=" * 80)
print("JOINT REGRESSOR")
print("=" * 80)
if 'J_regressor' in data:
    j_reg = data['J_regressor']
    print(f"Shape: {j_reg.shape}")
    print(f"Type: {type(j_reg)}")

print("\n" + "=" * 80)
print("FINDING SHOULDER JOINTS")
print("=" * 80)

# Generate default mesh to get joint positions
mesh_data = generate_default_mesh('male')
vertices = mesh_data['vertices']

print("\nStandard SMPL/STAR joint mapping (typical):")
joint_names = [
    "pelvis",
    "left_hip",
    "right_hip",
    "spine1",
    "left_knee",
    "right_knee",
    "spine2",
    "left_ankle",
    "right_ankle",
    "spine3",
    "left_foot",
    "right_foot",
    "neck",
    "left_collar",
    "right_collar",
    "head",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hand",
    "right_hand",
]

for i, name in enumerate(joint_names):
    print(f"  {i:2d}: {name}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("\nFor anatomical shoulder width:")
print("  - Use joints 16 (left_shoulder) and 17 (right_shoulder)")
print("  - These are the shoulder joint centers (where arm connects to torso)")
print("  - Calculate distance between these two joint positions")
print("\nNext step: Implement extract_shoulder_landmarks() using these joint indices")
