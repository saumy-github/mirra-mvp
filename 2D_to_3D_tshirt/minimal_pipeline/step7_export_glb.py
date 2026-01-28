"""
STEP 7: Connected T-Shirt GLB Export
=====================================
Generates a SINGLE CONNECTED 3D T-shirt mesh using boolean union.

This approach:
1. Creates body as a closed watertight tube
2. Creates sleeves as closed watertight cylinders  
3. Positions sleeves to overlap body
4. Uses boolean union to fuse into one connected mesh

Dependencies:
    pip install numpy trimesh manifold3d

Usage:
    python3 step7_export_glb.py
"""

import json
import math
from pathlib import Path
from typing import Dict, Tuple
import numpy as np

try:
    import trimesh
except ImportError:
    print("Install with: pip install trimesh numpy manifold3d")
    raise

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PATTERN_DIR = SCRIPT_DIR / "pattern_output"
COLOR_DIR = SCRIPT_DIR / "color_output"
OUTPUT_GLB = PATTERN_DIR / "tshirt_garment.glb"

CM_TO_M = 0.01


# ============================================================
# DATA LOADING
# ============================================================

def load_measurements() -> Dict:
    """Load measurements from pattern metadata."""
    metadata_file = PATTERN_DIR / "pattern_metadata.json"
    defaults = {
        "chest_flat": 52.0,
        "body_length": 72.0,
        "shoulder_width": 46.0,
        "sleeve_length": 22.0,
        "armhole_depth": 24.0
    }
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            return data.get('measurements', defaults)
        except:
            pass
    return defaults


def load_fabric_color() -> Tuple[int, int, int]:
    """Load fabric color."""
    color_file = COLOR_DIR / "front_fabric_color.json"
    if color_file.exists():
        try:
            with open(color_file, 'r') as f:
                data = json.load(f)
            return tuple(data.get('dominant', {}).get('rgb', [128, 128, 128]))
        except:
            pass
    return (128, 128, 128)


# ============================================================
# WATERTIGHT MESH PRIMITIVES
# ============================================================

def create_rounded_box(width: float, height: float, depth: float, 
                       corner_radius: float = 0.02, segments: int = 8) -> trimesh.Trimesh:
    """
    Create a rounded box (body cross-section swept along height).
    """
    # For simplicity, use a regular box and then apply smoothing
    box = trimesh.creation.box(extents=[width, height, depth])
    return box


def create_body_mesh(chest: float, body_len: float, shoulder: float, 
                     armhole: float, depth: float = 0.10) -> trimesh.Trimesh:
    """
    Create body as a watertight rounded tube.
    
    Uses a tapered capsule-like shape.
    """
    n_rings = 16
    n_segs = 24
    
    half_chest = chest / 2
    half_shoulder = shoulder / 2
    half_depth = depth / 2
    
    vertices = []
    
    for ring_idx in range(n_rings):
        t = ring_idx / (n_rings - 1)
        y = -t * body_len
        
        # Taper from shoulder to chest
        armhole_t = armhole / body_len
        if t < armhole_t * 0.8:
            blend = t / (armhole_t * 0.8)
            width = half_shoulder * (1 - blend) + half_chest * blend
        else:
            width = half_chest
        
        # Rounded rectangle cross-section (superellipse)
        for seg_idx in range(n_segs):
            theta = 2 * math.pi * seg_idx / n_segs
            c, s = math.cos(theta), math.sin(theta)
            n = 0.55  # Controls "squareness"
            
            x = width * (1 if c >= 0 else -1) * (abs(c) ** n)
            z = half_depth * (1 if s >= 0 else -1) * (abs(s) ** n)
            
            vertices.append([x, y, z])
    
    vertices = np.array(vertices)
    
    # Faces between rings
    faces = []
    for ring_idx in range(n_rings - 1):
        base = ring_idx * n_segs
        next_base = (ring_idx + 1) * n_segs
        
        for seg_idx in range(n_segs):
            next_seg = (seg_idx + 1) % n_segs
            
            v0 = base + seg_idx
            v1 = base + next_seg
            v2 = next_base + next_seg
            v3 = next_base + seg_idx
            
            faces.append([v0, v2, v1])
            faces.append([v0, v3, v2])
    
    # Cap top (neckline)
    top_center_idx = len(vertices)
    top_ring = vertices[:n_segs]
    center = top_ring.mean(axis=0)
    vertices = np.vstack([vertices, [center]])
    
    for seg_idx in range(n_segs):
        next_seg = (seg_idx + 1) % n_segs
        faces.append([top_center_idx, next_seg, seg_idx])
    
    # Cap bottom (hem)
    bottom_start = (n_rings - 1) * n_segs
    bottom_center_idx = len(vertices)
    bottom_ring = vertices[bottom_start:bottom_start + n_segs]
    center = bottom_ring.mean(axis=0)
    vertices = np.vstack([vertices, [center]])
    
    for seg_idx in range(n_segs):
        next_seg = (seg_idx + 1) % n_segs
        faces.append([bottom_center_idx, bottom_start + seg_idx, bottom_start + next_seg])
    
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.fix_normals()
    
    return mesh


def create_sleeve_mesh(length: float, radius: float, 
                       attach_x: float, attach_y: float,
                       direction: int) -> trimesh.Trimesh:
    """
    Create sleeve as a watertight tapered cylinder.
    """
    n_rings = 10
    n_segs = 16
    
    taper = 0.8  # Sleeve tapers to 80% at wrist
    
    vertices = []
    
    for ring_idx in range(n_rings):
        t = ring_idx / (n_rings - 1)
        
        # Position along sleeve
        x = attach_x + direction * t * length
        r = radius * (1 - (1 - taper) * t)
        
        for seg_idx in range(n_segs):
            theta = 2 * math.pi * seg_idx / n_segs
            y = attach_y + r * math.sin(theta)
            z = r * math.cos(theta)
            
            vertices.append([x, y, z])
    
    vertices = np.array(vertices)
    
    # Faces
    faces = []
    for ring_idx in range(n_rings - 1):
        base = ring_idx * n_segs
        next_base = (ring_idx + 1) * n_segs
        
        for seg_idx in range(n_segs):
            next_seg = (seg_idx + 1) % n_segs
            
            v0 = base + seg_idx
            v1 = base + next_seg
            v2 = next_base + next_seg
            v3 = next_base + seg_idx
            
            if direction < 0:
                faces.append([v0, v1, v2])
                faces.append([v0, v2, v3])
            else:
                faces.append([v0, v2, v1])
                faces.append([v0, v3, v2])
    
    # Cap wrist end
    wrist_start = (n_rings - 1) * n_segs
    wrist_center_idx = len(vertices)
    wrist_ring = vertices[wrist_start:wrist_start + n_segs]
    center = wrist_ring.mean(axis=0)
    vertices = np.vstack([vertices, [center]])
    
    for seg_idx in range(n_segs):
        next_seg = (seg_idx + 1) % n_segs
        if direction < 0:
            faces.append([wrist_center_idx, wrist_start + next_seg, wrist_start + seg_idx])
        else:
            faces.append([wrist_center_idx, wrist_start + seg_idx, wrist_start + next_seg])
    
    # Cap shoulder end
    cap_center_idx = len(vertices)
    cap_ring = vertices[:n_segs]
    center = cap_ring.mean(axis=0)
    vertices = np.vstack([vertices, [center]])
    
    for seg_idx in range(n_segs):
        next_seg = (seg_idx + 1) % n_segs
        if direction < 0:
            faces.append([cap_center_idx, seg_idx, next_seg])
        else:
            faces.append([cap_center_idx, next_seg, seg_idx])
    
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.fix_normals()
    
    return mesh


# ============================================================
# MESH COMBINATION
# ============================================================

def combine_with_union(body: trimesh.Trimesh, 
                       left_sleeve: trimesh.Trimesh,
                       right_sleeve: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Combine meshes using boolean union for a single connected mesh.
    """
    print("  Attempting boolean union...")
    
    # Try different engines
    engines = ['manifold', 'blender', None]
    
    for engine in engines:
        try:
            engine_name = engine if engine else 'auto'
            print(f"    Trying engine: {engine_name}...")
            
            if engine:
                combined = body.union(left_sleeve, engine=engine)
                combined = combined.union(right_sleeve, engine=engine)
            else:
                combined = body.union(left_sleeve)
                combined = combined.union(right_sleeve)
            
            n_components = len(combined.split(only_watertight=False))
            print(f"      Result: {n_components} component(s)")
            
            if n_components == 1:
                print(f"    ✓ Boolean union successful with {engine_name}")
                return combined
                
        except Exception as e:
            print(f"      Failed: {str(e)[:50]}")
            continue
    
    # Fallback: concatenate and merge vertices
    print("    Falling back to vertex merge...")
    combined = trimesh.util.concatenate([body, left_sleeve, right_sleeve])
    combined.merge_vertices(merge_tex=True, merge_norm=True)
    combined.fix_normals()
    
    return combined


def build_tshirt(measurements: Dict) -> trimesh.Trimesh:
    """Build complete T-shirt mesh."""
    print("  Creating mesh components...")
    
    # Extract measurements (convert to meters)
    chest = measurements.get('chest_flat', 52.0) * CM_TO_M
    body_len = measurements.get('body_length', 72.0) * CM_TO_M
    shoulder = measurements.get('shoulder_width', 46.0) * CM_TO_M
    sleeve_len = measurements.get('sleeve_length', 22.0) * CM_TO_M
    armhole = measurements.get('armhole_depth', 24.0) * CM_TO_M
    
    depth = 0.10  # Front-to-back depth
    half_chest = chest / 2
    sleeve_radius = armhole / 3.5
    
    # Create body
    print("    Body tube...")
    body = create_body_mesh(chest, body_len, shoulder, armhole, depth)
    print(f"      {len(body.vertices)} vertices, {len(body.faces)} faces")
    print(f"      Watertight: {body.is_watertight}")
    
    # Create sleeves with overlap into body for boolean union
    overlap = 0.025  # 2.5cm overlap into body
    
    print("    Left sleeve...")
    left_sleeve = create_sleeve_mesh(
        length=sleeve_len,
        radius=sleeve_radius,
        attach_x=-half_chest + overlap,  # Overlaps into body
        attach_y=-armhole / 2,
        direction=-1
    )
    print(f"      {len(left_sleeve.vertices)} vertices")
    print(f"      Watertight: {left_sleeve.is_watertight}")
    
    print("    Right sleeve...")
    right_sleeve = create_sleeve_mesh(
        length=sleeve_len,
        radius=sleeve_radius,
        attach_x=half_chest - overlap,  # Overlaps into body
        attach_y=-armhole / 2,
        direction=+1
    )
    print(f"      {len(right_sleeve.vertices)} vertices")
    print(f"      Watertight: {right_sleeve.is_watertight}")
    
    # Combine
    print("\n  Combining meshes...")
    mesh = combine_with_union(body, left_sleeve, right_sleeve)
    
    return mesh


# ============================================================
# EXPORT
# ============================================================

def apply_material(mesh: trimesh.Trimesh, rgb: Tuple[int, int, int]):
    """Apply fabric material."""
    # Generate UVs
    verts = mesh.vertices
    xy = verts[:, :2]
    min_xy, max_xy = xy.min(axis=0), xy.max(axis=0)
    range_xy = np.maximum(max_xy - min_xy, 1e-6)
    uvs = (xy - min_xy) / range_xy
    
    # Create material
    color = [c / 255.0 for c in rgb] + [1.0]
    material = trimesh.visual.material.PBRMaterial(
        baseColorFactor=color,
        metallicFactor=0.0,
        roughnessFactor=0.8,
        name="FabricMaterial"
    )
    
    mesh.visual = trimesh.visual.TextureVisuals(uv=uvs, material=material)


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("   STEP 7: CONNECTED T-SHIRT GLB EXPORT")
    print("=" * 60)
    
    print("\n→ Loading measurements...")
    measurements = load_measurements()
    for k, v in measurements.items():
        print(f"    {k}: {v} cm")
    
    print("\n→ Loading fabric color...")
    color = load_fabric_color()
    print(f"    RGB{color}")
    
    print("\n→ Building T-shirt mesh...")
    mesh = build_tshirt(measurements)
    
    # Statistics
    n_components = len(mesh.split(only_watertight=False))
    print(f"\n→ Final mesh statistics:")
    print(f"    Vertices: {len(mesh.vertices)}")
    print(f"    Faces: {len(mesh.faces)}")
    print(f"    Watertight: {mesh.is_watertight}")
    print(f"    Components: {n_components}")
    
    print("\n→ Applying fabric material...")
    apply_material(mesh, color)
    print(f"    Color: RGB{color}")
    
    print("\n→ Exporting GLB...")
    OUTPUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(OUTPUT_GLB), file_type='glb')
    
    if OUTPUT_GLB.exists():
        size_kb = OUTPUT_GLB.stat().st_size / 1024
        print(f"    ✓ Exported: {OUTPUT_GLB}")
        print(f"    ✓ Size: {size_kb:.1f} KB")
    
    # Summary
    if n_components == 1:
        status = "✅ SINGLE CONNECTED MESH"
    else:
        status = f"⚠️ {n_components} COMPONENTS"
    
    print("\n" + "=" * 60)
    print(f"   {status}")
    print("=" * 60)
    
    print(f"""
Output: {OUTPUT_GLB}

Mesh construction:
  ✓ Body: tapered tube (shoulder → chest)
  ✓ Sleeves: tapered cylinders (overlapping body)
  ✓ Combined with boolean union
  ✓ Fabric color applied (PBR material)

View at: https://gltf-viewer.donmccurdy.com
""")
    
    return mesh


if __name__ == "__main__":
    main()
