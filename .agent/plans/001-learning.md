# Learning: Plan 001

1. **Trimesh Library**

Trimesh is a Python library for working with 3D triangular meshes (like the STAR body model output).

**What it does**:

- Loads, saves, and exports 3D mesh files in various formats (GLB, OBJ, STL, etc.)
- Provides mesh manipulation tools (scaling, rotation, translation)
- Calculates mesh properties (volume, surface area, bounds)

**Why we need it**:

- In `avatar_exporter.py`, we use trimesh to export the STAR mesh (vertices + faces) to GLB format
- GLB is a binary 3D format that works well with Blender and web viewers
- Trimesh handles all the complexity of the GLB file format specification

**Where it's used in our code**:

- `pipeline_star/avatar_exporter.py` lines 15-39
- Creates a `trimesh.Trimesh` object from vertices and faces
- Applies PBR material configuration (black matte finish for MVP)
- Exports to GLB file that can be imported into Blender

**Alternative libraries**: Could also use `pygltflib` or `bpy` (Blender Python), but trimesh is simpler and doesn't require Blender installation.
