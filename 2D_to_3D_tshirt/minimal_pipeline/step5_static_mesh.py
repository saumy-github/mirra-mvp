"""
Step 5B: Static 3D T-Shirt Mesh Generator

This creates a 3D T-shirt mesh directly from pattern pieces using
mathematical deformation instead of physics simulation.

Perfect for:
- Quick visualization
- Texture mapping
- Product catalogs
- When you don't need realistic draping

NO physics, NO avatar, NO waiting - instant result!

Usage:
    blender --background --python step5_static_mesh.py
    
Output:
    - pattern_output/tshirt_static.blend
    - pattern_output/exports/TShirt_Static.obj/fbx/glb
"""

import bpy
import bmesh
import json
from pathlib import Path
from mathutils import Vector, Matrix
import math

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PATTERN_DIR = SCRIPT_DIR / "pattern_output"
OUTPUT_DIR = PATTERN_DIR / "exports"

# ============================================================
# MESH UTILITIES
# ============================================================

def create_mesh_from_points(points: list, name: str) -> bpy.types.Object:
    """Create a mesh object from a list of 2D points."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Convert 2D points to 3D (Z=0)
    verts = [(p[0]/100, p[1]/100, 0) for p in points]  # cm to meters
    
    # Create faces (assuming convex polygon)
    if len(verts) >= 3:
        faces = [list(range(len(verts)))]
    else:
        faces = []
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    # Subdivide for smoother deformation
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=8)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return obj


def deform_to_cylinder(obj: bpy.types.Object, radius: float, axis: str = 'Y'):
    """
    Deform a flat mesh into a cylindrical shape.
    
    Args:
        obj: The mesh object to deform
        radius: Radius of the cylinder
        axis: Axis to wrap around ('X', 'Y', or 'Z')
    """
    mesh = obj.data
    
    # Get bounds
    verts = mesh.vertices
    if not verts:
        return
    
    # Find min/max in the wrap direction
    if axis == 'Y':
        wrap_coords = [v.co.y for v in verts]
        height_coords = [v.co.z for v in verts]
    elif axis == 'X':
        wrap_coords = [v.co.x for v in verts]
        height_coords = [v.co.z for v in verts]
    else:  # Z
        wrap_coords = [v.co.z for v in verts]
        height_coords = [v.co.y for v in verts]
    
    min_wrap = min(wrap_coords)
    max_wrap = max(wrap_coords)
    wrap_range = max_wrap - min_wrap
    
    if wrap_range == 0:
        return
    
    # Deform each vertex
    for v in verts:
        if axis == 'Y':
            # Normalize Y position to 0-1
            t = (v.co.y - min_wrap) / wrap_range
            # Map to cylinder
            angle = t * math.pi  # 180 degrees (half cylinder for front/back)
            v.co.x = v.co.x  # Keep X (width) unchanged
            v.co.y = radius * math.sin(angle)
            v.co.z = v.co.z + radius * (1 - math.cos(angle))
        elif axis == 'X':
            t = (v.co.x - min_wrap) / wrap_range
            angle = t * math.pi * 2  # Full cylinder for sleeve
            v.co.x = radius * math.cos(angle)
            v.co.y = radius * math.sin(angle)
            # v.co.z stays as height
    
    mesh.update()


def create_tshirt_from_patterns(measurements: dict) -> bpy.types.Object:
    """
    Create a 3D T-shirt from pattern measurements using geometric deformation.
    
    This creates a simplified T-shirt shape:
    - Front/back panels deformed into torso cylinder
    - Sleeves deformed into arm cylinders
    - All pieces merged at seams
    
    Args:
        measurements: Dictionary with chest, length, shoulder, sleeve measurements
    
    Returns:
        The combined T-shirt mesh object
    """
    print("\n" + "="*60)
    print("   CREATING STATIC 3D T-SHIRT MESH")
    print("="*60)
    
    chest = measurements.get("chest_flat", 52.0) / 100  # cm to m
    length = measurements.get("body_length", 72.0) / 100
    shoulder = measurements.get("shoulder_width", 46.0) / 100
    sleeve_len = measurements.get("sleeve_length", 22.0) / 100
    armhole = measurements.get("armhole_depth", 24.0) / 100
    
    print(f"\nMeasurements:")
    print(f"  Chest: {chest*100:.1f}cm")
    print(f"  Length: {length*100:.1f}cm")
    print(f"  Shoulder: {shoulder*100:.1f}cm")
    print(f"  Sleeve: {sleeve_len*100:.1f}cm")
    
    # Calculate cylinder radius from chest circumference
    # chest_flat is half circumference
    circumference = chest * 2
    torso_radius = circumference / (2 * math.pi)
    
    print(f"\n→ Creating torso (radius: {torso_radius*100:.1f}cm)...")
    
    # ============================================================
    # CREATE FRONT PANEL
    # ============================================================
    
    front_width = chest
    front_height = length
    neck_width = 0.15  # 15cm neck opening
    neck_depth = 0.08  # 8cm neck depth
    
    # Front panel points (simple rectangle with neck cutout)
    front_points = [
        (0, 0),                              # Bottom left
        (front_width*100, 0),               # Bottom right
        (front_width*100, front_height*100), # Top right
        (front_width*100/2 + neck_width*50, front_height*100),  # Neck right
        (front_width*100/2 + neck_width*50, front_height*100 - neck_depth*100),  # Neck inner right
        (front_width*100/2 - neck_width*50, front_height*100 - neck_depth*100),  # Neck inner left
        (front_width*100/2 - neck_width*50, front_height*100),  # Neck left
        (0, front_height*100),              # Top left
    ]
    
    front = create_mesh_from_points(front_points, "Front")
    print(f"  ✓ Front panel: {len(front.data.vertices)} vertices")
    
    # Deform to cylinder (front half)
    deform_to_cylinder(front, torso_radius, axis='Y')
    print(f"  ✓ Deformed to cylinder")
    
    # ============================================================
    # CREATE BACK PANEL
    # ============================================================
    
    # Back is same as front but no neck cutout
    back_points = [
        (0, 0),
        (front_width*100, 0),
        (front_width*100, front_height*100),
        (0, front_height*100),
    ]
    
    back = create_mesh_from_points(back_points, "Back")
    print(f"\n→ Creating back panel...")
    print(f"  ✓ Back panel: {len(back.data.vertices)} vertices")
    
    # Deform to cylinder (back half) and rotate 180 degrees
    deform_to_cylinder(back, torso_radius, axis='Y')
    back.rotation_euler.z = math.pi  # Rotate 180 degrees
    bpy.context.view_layer.objects.active = back
    bpy.ops.object.transform_apply(rotation=True)
    print(f"  ✓ Deformed to cylinder (back)")
    
    # ============================================================
    # CREATE SLEEVES
    # ============================================================
    
    sleeve_width = armhole  # Armhole depth becomes sleeve circumference
    sleeve_radius = sleeve_width / (2 * math.pi)
    
    print(f"\n→ Creating sleeves (radius: {sleeve_radius*100:.1f}cm)...")
    
    # Left sleeve
    sleeve_points = [
        (0, 0),
        (sleeve_width*100, 0),
        (sleeve_width*100, sleeve_len*100),
        (0, sleeve_len*100),
    ]
    
    left_sleeve = create_mesh_from_points(sleeve_points, "LeftSleeve")
    deform_to_cylinder(left_sleeve, sleeve_radius, axis='X')
    
    # Position at shoulder
    left_sleeve.location = Vector((
        -front_width/2,  # Left side
        0,
        front_height - armhole/2  # At armhole height
    ))
    left_sleeve.rotation_euler = (0, 0, -math.pi/2)  # Rotate to point left
    bpy.ops.object.transform_apply(location=True, rotation=True)
    
    print(f"  ✓ Left sleeve: {len(left_sleeve.data.vertices)} vertices")
    
    # Right sleeve (mirror)
    right_sleeve = left_sleeve.copy()
    right_sleeve.data = left_sleeve.data.copy()
    right_sleeve.name = "RightSleeve"
    bpy.context.collection.objects.link(right_sleeve)
    
    right_sleeve.location = Vector((
        front_width/2,  # Right side
        0,
        front_height - armhole/2
    ))
    right_sleeve.rotation_euler = (0, 0, math.pi/2)  # Rotate to point right
    bpy.ops.object.transform_apply(location=True, rotation=True)
    
    print(f"  ✓ Right sleeve: {len(right_sleeve.data.vertices)} vertices")
    
    # ============================================================
    # MERGE ALL PIECES
    # ============================================================
    
    print(f"\n→ Merging pieces...")
    
    # Select all pieces
    bpy.ops.object.select_all(action='DESELECT')
    front.select_set(True)
    back.select_set(True)
    left_sleeve.select_set(True)
    right_sleeve.select_set(True)
    bpy.context.view_layer.objects.active = front
    
    # Join
    bpy.ops.object.join()
    tshirt = bpy.context.active_object
    tshirt.name = "TShirt_Static"
    
    # Merge vertices at seams
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.05)  # 5cm threshold
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"  ✓ Merged into single mesh")
    print(f"  ✓ Final mesh: {len(tshirt.data.vertices)} vertices, {len(tshirt.data.polygons)} faces")
    
    return tshirt


def export_mesh(obj: bpy.types.Object, output_dir: Path):
    """Export mesh in multiple formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n→ Exporting to {output_dir}...")
    
    # Select only the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    formats = {
        "obj": "OBJ (Universal)",
        "fbx": "FBX (Game Engines)",
        "glb": "GLB (Web/AR)"
    }
    
    for fmt, desc in formats.items():
        filepath = str(output_dir / f"{obj.name}.{fmt}")
        
        try:
            if fmt == "obj":
                bpy.ops.wm.obj_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    export_materials=False
                )
            elif fmt == "fbx":
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    mesh_smooth_type='FACE'
                )
            elif fmt == "glb":
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    use_selection=True,
                    export_format='GLB'
                )
            
            print(f"  ✓ {desc}: {filepath}")
        except Exception as e:
            print(f"  ✗ Failed to export {fmt}: {e}")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Load measurements
    metadata_path = PATTERN_DIR / "pattern_metadata.json"
    measurements = {
        "chest_flat": 52.0,
        "body_length": 72.0,
        "shoulder_width": 46.0,
        "sleeve_length": 22.0,
        "armhole_depth": 24.0,
    }
    
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            measurements = metadata.get("measurements", measurements)
        print(f"✓ Loaded measurements from {metadata_path}")
    
    # Create T-shirt
    tshirt = create_tshirt_from_patterns(measurements)
    
    # Save blend file
    blend_path = PATTERN_DIR / "tshirt_static.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"\n✓ Saved: {blend_path}")
    
    # Export
    export_mesh(tshirt, OUTPUT_DIR)
    
    print("\n" + "="*60)
    print("   STATIC MESH COMPLETE!")
    print("="*60)
    print(f"""
Output files:
  Blend: {blend_path}
  Exports: {OUTPUT_DIR}/
    - TShirt_Static.obj
    - TShirt_Static.fbx
    - TShirt_Static.glb

This is a simplified geometric mesh.
For realistic draping, use step5_blender_sewing.py with simulation.
""")
