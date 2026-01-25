"""Export STAR mesh to GLB file format."""

import numpy as np
from typing import Any, Optional, Dict


# Export mesh to GLB file
def export_mesh_to_glb(
    vertices: np.ndarray,
    faces: np.ndarray,
    output_glb_path: str,
    material_config: Optional[Dict[str, Any]] = None
) -> None:
    try:
        import trimesh
    except ImportError:
        raise ImportError(
            "trimesh library is required for GLB export. "
            "Install it with: pip install trimesh"
        )
    
    if vertices.shape[1] != 3:
        raise ValueError(f"Vertices must have shape (N, 3), got {vertices.shape}")
    
    if faces.shape[1] != 3:
        raise ValueError(f"Faces must have shape (M, 3), got {faces.shape}")
    
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    
    if material_config is not None:
        # Create PBR material
        material = trimesh.visual.material.PBRMaterial(
            baseColorFactor=material_config.get('baseColorFactor', [1.0, 1.0, 1.0, 1.0]),
            metallicFactor=material_config.get('metallicFactor', 0.0),
            roughnessFactor=material_config.get('roughnessFactor', 1.0),
            doubleSided=material_config.get('doubleSided', False)
        )
        # Use TextureVisuals with material (supports PBR materials)
        mesh.visual = trimesh.visual.TextureVisuals(material=material)
    
    try:
        mesh.export(output_glb_path, file_type='glb')
    except Exception as e:
        raise RuntimeError(f"Failed to export GLB to {output_glb_path}: {e}")
