#!/usr/bin/env python3
import sys
import os
from typing import Dict, Any, Tuple
import numpy as np

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from star.ch.star import STAR  # type: ignore


# Module-level cache to avoid re-instantiating STAR models (expensive)
# WARNING: NOT THREAD-SAFE. Cached STAR instances are mutated per call (model.pose[:], model.betas[:]).
# Current usage: single-threaded CLI only. Add threading.Lock if moving to concurrent/web environment.
# Do not execute this file directly (would create separate cache); use: python pipeline_star/first.py
_MODEL_CACHE: Dict[Tuple[str, int], Any] = {}


# Generate mesh from STAR model with given parameters (CPU-only, deterministic)
def generate_mesh(
    gender: str,
    betas: np.ndarray,
    pose: np.ndarray,
    scale: float = 1.0,
    num_betas: int = 10
) -> Dict[str, Any]:
    cache_key = (gender, num_betas)
    if cache_key not in _MODEL_CACHE:
        _MODEL_CACHE[cache_key] = STAR(gender=gender, num_betas=num_betas)
    
    model = _MODEL_CACHE[cache_key]
    model.pose[:] = pose
    model.betas[:] = betas
    
    vertices = np.array(model.r) * scale
    faces = np.array(model.f)
    
    return {
        'vertices': vertices,
        'faces': faces,
        'gender': gender,
        'num_betas': num_betas,
        'scale': scale,
    }


# Generate mesh in A-pose (pose vector all zeros)
def generate_apose_mesh(
    gender: str,
    betas: np.ndarray,
    scale: float = 1.0,
    num_betas: int = 10
) -> Dict[str, Any]:
    cache_key = (gender, num_betas)
    if cache_key not in _MODEL_CACHE:
        _MODEL_CACHE[cache_key] = STAR(gender=gender, num_betas=num_betas)
    
    pose_size = _MODEL_CACHE[cache_key].pose.size
    pose = np.zeros(pose_size)
    
    return generate_mesh(gender, betas, pose, scale, num_betas)


# Generate mesh with default parameters (average shape, A-pose, unit scale)
def generate_default_mesh(gender: str, num_betas: int = 10) -> Dict[str, Any]:
    betas = np.zeros(num_betas)
    return generate_apose_mesh(gender, betas, scale=1.0, num_betas=num_betas)


if __name__ == "__main__":
    raise RuntimeError(
        "Do not execute star_runner.py directly (causes duplicate module cache).\n"
        "Use: python pipeline_star/first.py --user_id <id> --mode <mode>"
    )
