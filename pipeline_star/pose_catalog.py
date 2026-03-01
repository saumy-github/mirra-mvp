"""Canonical pose definitions for STAR model."""

import numpy as np
from typing import Dict, Any


# Canonical T-pose metadata (STAR zero-pose = T-pose)
T_POSE_NAME = "star-tpose-v1"
T_POSE_VERSION = "1.0"


# Generate canonical T-pose thetas vector for STAR model
def get_apose_thetas(pose_size: int) -> np.ndarray:
    # Zero vector = T-pose for STAR model (arms horizontal)
    return np.zeros(pose_size)


# Get T-pose metadata for serialization to JSON
def get_apose_metadata() -> Dict[str, Any]:
    return {
        'pose_name': T_POSE_NAME,
        'pose_version': T_POSE_VERSION,
        'description': 'Zero-pose (T-pose) with all joint rotations at neutral, arms horizontal',
    }
