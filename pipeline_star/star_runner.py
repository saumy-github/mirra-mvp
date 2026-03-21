#!/usr/bin/env python3
import sys
import os
from typing import Dict, Any, Tuple
import numpy as np
import torch

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Homebrew Python 3.12 can skip hidden .pth files (e.g. _editable_.star-*.pth),
# so editable installs may not expose the local STAR package. Add a direct fallback.
star_repo_root = os.path.join(workspace_root, 'libs', 'star')
if os.path.isdir(star_repo_root) and star_repo_root not in sys.path:
    sys.path.insert(0, star_repo_root)
    
from star.pytorch.star import STAR  # type: ignore
from pipeline_star.pose_catalog import get_apose_thetas
from utils.device import DEVICE


# Module-level cache to avoid re-instantiating STAR models (expensive)
# WARNING: NOT THREAD-SAFE. Cached STAR instances are mutated per call (model.pose[:], model.betas[:]).
# Current usage: single-threaded CLI only. Add threading.Lock if moving to concurrent/web environment.
# Do not execute this file directly (would create separate cache); use: python pipeline_star/first.py
_MODEL_CACHE: Dict[Tuple[str, int], Any] = {}
_FACES_CACHE: Dict[Tuple[str, int], np.ndarray] = {}


def _get_model(gender: str, num_betas: int) -> Any:
    cache_key = (gender, num_betas)
    if cache_key not in _MODEL_CACHE:
        _MODEL_CACHE[cache_key] = STAR(gender=gender, num_betas=num_betas).to(DEVICE)
    return _MODEL_CACHE[cache_key]


def _get_faces_numpy(gender: str, num_betas: int, model: Any) -> np.ndarray:
    cache_key = (gender, num_betas)
    if cache_key not in _FACES_CACHE:
        _FACES_CACHE[cache_key] = model.faces.detach().cpu().numpy()
    return _FACES_CACHE[cache_key]


def _to_numpy_cpu(t: torch.Tensor) -> np.ndarray:
    return t.detach().cpu().numpy()


def _ensure_batch_betas(betas: np.ndarray, num_betas: int) -> np.ndarray:
    arr = np.asarray(betas, dtype=np.float32)
    if arr.ndim == 1:
        if arr.shape[0] != num_betas:
            raise ValueError(
                f"Invalid betas shape {arr.shape}; expected ({num_betas},) or (B,{num_betas})"
            )
        arr = arr[np.newaxis, :]
    elif arr.ndim == 2:
        if arr.shape[1] != num_betas:
            raise ValueError(
                f"Invalid betas shape {arr.shape}; second dim must be {num_betas}"
            )
    else:
        raise ValueError(
            f"Invalid betas rank {arr.ndim}; expected rank 1 or 2"
        )
    return arr


def _ensure_batch_pose(pose: np.ndarray, batch_size: int) -> np.ndarray:
    arr = np.asarray(pose, dtype=np.float32)
    if arr.ndim == 1:
        if arr.shape[0] != 72:
            raise ValueError(
                f"Invalid pose shape {arr.shape}; expected (72,) or (B,72)"
            )
        arr = arr[np.newaxis, :]
    elif arr.ndim == 2:
        if arr.shape[1] != 72:
            raise ValueError(
                f"Invalid pose shape {arr.shape}; second dim must be 72"
            )
    else:
        raise ValueError(
            f"Invalid pose rank {arr.ndim}; expected rank 1 or 2"
        )

    if arr.shape[0] == 1 and batch_size > 1:
        arr = np.repeat(arr, batch_size, axis=0)
    elif arr.shape[0] != batch_size:
        raise ValueError(
            f"Pose batch size {arr.shape[0]} does not match betas batch size {batch_size}"
        )

    return arr


def _zeros_trans(batch_size: int) -> np.ndarray:
    return np.zeros((batch_size, 3), dtype=np.float32)


def _ensure_batch_trans(trans: np.ndarray, batch_size: int) -> np.ndarray:
    arr = np.asarray(trans, dtype=np.float32)
    if arr.ndim == 1:
        if arr.shape[0] != 3:
            raise ValueError(
                f"Invalid trans shape {arr.shape}; expected (3,) or (B,3)"
            )
        arr = arr[np.newaxis, :]
    elif arr.ndim == 2:
        if arr.shape[1] != 3:
            raise ValueError(
                f"Invalid trans shape {arr.shape}; second dim must be 3"
            )
    else:
        raise ValueError(
            f"Invalid trans rank {arr.ndim}; expected rank 1 or 2"
        )

    if arr.shape[0] == 1 and batch_size > 1:
        arr = np.repeat(arr, batch_size, axis=0)
    elif arr.shape[0] != batch_size:
        raise ValueError(
            f"Trans batch size {arr.shape[0]} does not match betas batch size {batch_size}"
        )

    return arr


def generate_mesh_batch(
    gender: str,
    betas: np.ndarray,
    pose: np.ndarray,
    trans: np.ndarray = None,
    scale: float = 1.0,
    num_betas: int = 10
) -> Dict[str, Any]:
    model = _get_model(gender=gender, num_betas=num_betas)

    betas_batch = _ensure_batch_betas(betas, num_betas=num_betas)
    batch_size = betas_batch.shape[0]
    pose_batch = _ensure_batch_pose(pose, batch_size=batch_size)
    if trans is None:
        trans_batch = _zeros_trans(batch_size)
    else:
        trans_batch = _ensure_batch_trans(trans, batch_size=batch_size)

    betas_t = torch.tensor(betas_batch, dtype=torch.float32, device=DEVICE)
    pose_t = torch.tensor(pose_batch, dtype=torch.float32, device=DEVICE)
    trans_t = torch.tensor(trans_batch, dtype=torch.float32, device=DEVICE)

    with torch.no_grad():
        vertices_t = model(pose_t, betas_t, trans_t)
    if vertices_t.ndim != 3 or vertices_t.shape[0] != batch_size or vertices_t.shape[2] != 3:
        raise RuntimeError(
            f"Unexpected STAR vertex output shape: {tuple(vertices_t.shape)}"
        )

    vertices_np = _to_numpy_cpu(vertices_t) * scale
    faces_np = _get_faces_numpy(gender=gender, num_betas=num_betas, model=model)

    return {
        'vertices': vertices_np,
        'faces': faces_np,
        'gender': gender,
        'num_betas': num_betas,
        'scale': scale,
    }


# Generate mesh from STAR model with given parameters
def generate_mesh(
    gender: str,
    betas: np.ndarray,
    pose: np.ndarray,
    scale: float = 1.0,
    num_betas: int = 10
) -> Dict[str, Any]:
    batch_result = generate_mesh_batch(
        gender=gender,
        betas=betas,
        pose=pose,
        trans=None,
        scale=scale,
        num_betas=num_betas
    )
    vertices_np = batch_result['vertices']

    if vertices_np.shape[0] == 1:
        vertices_out = vertices_np[0]
    else:
        vertices_out = vertices_np
    
    return {
        'vertices': vertices_out,
        'faces': batch_result['faces'],
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
    pose = get_apose_thetas(72)
    
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
