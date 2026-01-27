#!/usr/bin/env python3
"""
Inspect STAR model to find shoulder joint indices.
"""
import sys
import os
import numpy as np

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from pipeline_star.star_runner import generate_default_mesh

# Load STAR model data
model_path = '/home/saumy/Documents/mirra-mvp/models/star_1_1/male/model.npz'
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
print(f"\nKinematic tree (parent-child relationships):")
print(kintree)

print("\n" + "=" * 80)
print("JOINT REGRESSOR")
print("=" * 80)
if 'J_regressor' in data:
    J_reg = data['J_regressor']
    print(f"Shape: {J_reg.shape}")
    print(f"Type: {type(J_reg)}")
    
    # J_regressor is typically num_joints x num_vertices sparse matrix
    # Each row represents a joint, non-zero entries are vertex indices/weights
    
print("\n" + "=" * 80)
print("FINDING SHOULDER JOINTS")
print("=" * 80)

# Generate default mesh to get joint positions
mesh_data = generate_default_mesh('male')
vertices = mesh_data['vertices']

# Based on SMPL/STAR standard, joints are typically:
# Joint indices (0-indexed):
# 0: pelvis
# 1-2: left/right hip
# 3: spine1
# 4-5: left/right knee
# 6: spine2
# 7-8: left/right ankle
# 9: spine3
# 10-11: left/right foot
# 12: neck
# 13-14: left/right collar (shoulder area)
# 15: head
# 16-17: left/right shoulder
# 18-19: left/right elbow
# 20-21: left/right wrist
# 22-23: left/right hand

# Most likely shoulder joints are indices 16, 17 (left, right shoulder)
# Or possibly 13, 14 (left, right collar)

print("\nStandard SMPL/STAR joint mapping (typical):")
joint_names = [
    "pelvis",           # 0
    "left_hip",         # 1
    "right_hip",        # 2
    "spine1",           # 3
    "left_knee",        # 4
    "right_knee",       # 5
    "spine2",           # 6
    "left_ankle",       # 7
    "right_ankle",      # 8
    "spine3",           # 9
    "left_foot",        # 10
    "right_foot",       # 11
    "neck",             # 12
    "left_collar",      # 13
    "right_collar",     # 14
    "head",             # 15
    "left_shoulder",    # 16
    "right_shoulder",   # 17
    "left_elbow",       # 18
    "right_elbow",      # 19
    "left_wrist",       # 20
    "right_wrist",      # 21
    "left_hand",        # 22
    "right_hand",       # 23
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
