"""Canonical pose definitions for STAR model."""

import numpy as np
from typing import Dict, Any


# Canonical pose metadata
T_POSE_NAME = "star-tpose-v1"
A_POSE_NAME = "star-apose-v1"
POSE_VERSION = "1.0"

_LEFT_SHOULDER_JOINT = 16
_RIGHT_SHOULDER_JOINT = 17
_A_POSE_DEGREES = 35.0


# Generate canonical T-pose thetas vector for STAR model
def get_tpose_thetas(pose_size: int) -> np.ndarray:
    # Zero vector = T-pose for STAR model (arms horizontal)
    return np.zeros(pose_size)


# Generate canonical A-pose thetas vector for STAR model
def get_a_pose_thetas(pose_size: int) -> np.ndarray:
    thetas = np.zeros(pose_size)

    # Rotate shoulders around local Z to lower arms from T-pose.
    # If observed direction is inverted in preview/export, swap signs.
    angle_rad = np.deg2rad(_A_POSE_DEGREES)
    thetas[_LEFT_SHOULDER_JOINT * 3 + 2] = -angle_rad
    thetas[_RIGHT_SHOULDER_JOINT * 3 + 2] = angle_rad
    return thetas


def get_pose_thetas(pose_name: str, pose_size: int) -> np.ndarray:
    normalized = (pose_name or "tpose").strip().lower()
    if normalized == 'apose':
        return get_a_pose_thetas(pose_size)
    if normalized == 'tpose':
        return get_tpose_thetas(pose_size)
    raise ValueError(f"Unsupported pose '{pose_name}'. Expected 'tpose' or 'apose'.")


def get_pose_metadata(pose_name: str) -> Dict[str, Any]:
    normalized = (pose_name or "tpose").strip().lower()
    if normalized == 'apose':
        return {
            'pose_name': A_POSE_NAME,
            'pose_version': POSE_VERSION,
            'description': f'Canonical A-pose with shoulder adduction (~{int(_A_POSE_DEGREES)}°) from STAR neutral',
        }
    if normalized == 'tpose':
        return {
            'pose_name': T_POSE_NAME,
            'pose_version': POSE_VERSION,
            'description': 'Zero-pose (T-pose) with all joint rotations at neutral, arms horizontal',
        }
    raise ValueError(f"Unsupported pose '{pose_name}'. Expected 'tpose' or 'apose'.")


# Backwards compatibility (historical function names)
def get_apose_thetas(pose_size: int) -> np.ndarray:
    # Historical behavior in this codebase: zero-vector T-pose.
    return get_tpose_thetas(pose_size)


def get_apose_metadata() -> Dict[str, Any]:
    # Historical behavior in this codebase: metadata for zero-vector T-pose.
    return {
        'pose_name': T_POSE_NAME,
        'pose_version': POSE_VERSION,
        'description': 'Zero-pose (T-pose) with all joint rotations at neutral, arms horizontal',
    }
