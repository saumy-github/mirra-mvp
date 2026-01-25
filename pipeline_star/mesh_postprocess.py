"""Conservative mesh post-processing (no vertex/face deletion by default)."""

import numpy as np
from typing import Dict, Any, Optional


# Validate mesh arrays for NaN/inf values
def validate_mesh_arrays(vertices: np.ndarray, faces: np.ndarray) -> None:
    if np.any(np.isnan(vertices)):
        raise ValueError("Mesh vertices contain NaN values")
    
    if np.any(np.isinf(vertices)):
        raise ValueError("Mesh vertices contain infinite values")
    
    if np.any(np.isnan(faces)):
        raise ValueError("Mesh faces contain NaN values")
    
    if np.any(faces < 0):
        raise ValueError("Mesh faces contain negative indices")
    
    if np.any(faces >= len(vertices)):
        raise ValueError("Mesh faces reference out-of-bounds vertex indices")


# Recenter mesh to origin (optional, conservative transformation)
def recenter_mesh(vertices: np.ndarray, center_point: Optional[np.ndarray] = None) -> np.ndarray:
    if center_point is None:
        center_point = np.mean(vertices, axis=0)
    
    return vertices - center_point


# Apply conservative post-processing to mesh
def postprocess_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    validate_arrays: bool = True,
    recenter: bool = False,
    apply_smoothing: bool = False
) -> Dict[str, Any]:
    processed_vertices = vertices.copy()
    processed_faces = faces.copy()
    
    if validate_arrays:
        validate_mesh_arrays(processed_vertices, processed_faces)
    
    if recenter:
        processed_vertices = recenter_mesh(processed_vertices)
    
    if apply_smoothing:
        raise NotImplementedError(
            "Modesty/crotch smoothing is not implemented in MVP. "
            "This flag is reserved for future use."
        )
    
    return {
        'vertices': processed_vertices,
        'faces': processed_faces,
        'postprocess_applied': {
            'validate_arrays': validate_arrays,
            'recenter': recenter,
            'apply_smoothing': apply_smoothing,
        }
    }
