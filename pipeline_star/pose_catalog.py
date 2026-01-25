"""Canonical pose definitions for STAR model."""

import numpy as np
from typing import Dict, Any


# Canonical A-pose metadata
A_POSE_NAME = "star-apose-v1"
A_POSE_VERSION = "1.0"


# Generate canonical A-pose thetas vector for STAR model
def get_apose_thetas(pose_size: int) -> np.ndarray:
    return np.zeros(pose_size)


# Get A-pose metadata for serialization to JSON
def get_apose_metadata() -> Dict[str, Any]:
    return {
        'pose_name': A_POSE_NAME,
        'pose_version': A_POSE_VERSION,
        'description': 'Zero-pose (A-pose) with all joint rotations at neutral',
    }
