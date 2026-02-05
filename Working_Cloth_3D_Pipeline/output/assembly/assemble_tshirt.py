"""
MIRAAA T-Shirt Assembly - Proper 3D garment construction
Positions pattern pieces and welds seams to create a wearable 3D garment
"""

import bpy
import bmesh
import os
import math
from mathutils import Vector, kdtree

# Configuration
PATTERN_DIR = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/patterns"
OUTPUT_PATH = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/tshirt_3d.glb"

# Weld threshold - vertices closer than this will be merged
WELD_THRESHOLD = 0.05  # 5cm


def clear_scene():
    """Clear all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in bpy.data.collections:
        if col.name != 'Scene Collection':
            bpy.data.collections.remove(col)


def import_svg_as_mesh(svg_path: str, name: str):
    """Import SVG and convert to mesh."""
    existing = set(bpy.data.objects.keys())
    
    bpy.ops.import_curve.svg(filepath=svg_path)
    
    new_objs = [obj for obj in bpy.data.objects if obj.name not in existing]
    curves = [obj for obj in new_objs if obj.type == 'CURVE']
    
    if not curves:
        print(f"No curves found in {svg_path}")
        return None
    
    # Select and join all curves
    bpy.ops.object.select_all(action='DESELECT')
    for c in curves:
        c.select_set(True)
    bpy.context.view_layer.objects.active = curves[0]
    
    if len(curves) > 1:
        bpy.ops.object.join()
    
    curve_obj = bpy.context.active_object
    
    # Set up curve for mesh conversion
    curve_obj.data.dimensions = '2D'
    curve_obj.data.fill_mode = 'BOTH'
    curve_obj.data.extrude = 0.005  # 5mm thickness - thin fabric
    
    # Convert to mesh
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    
    # Scale up (Blender SVG import is small)
    mesh_obj.scale = (10, 10, 10)
    bpy.ops.object.transform_apply(scale=True)
    
    print(f"Imported {name}: {len(mesh_obj.data.vertices)} verts, dimensions: {mesh_obj.dimensions}")
    
    return mesh_obj


def create_tshirt_material(name: str, color=(0.2, 0.2, 0.2, 1.0)):
    """Create a fabric-like material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8  # Matte fabric
    
    return mat


def position_for_tshirt(pieces: dict):
    """
    Position pattern pieces to form a T-shirt shape.
    Front and back bodice face each other, sleeves attached at sides.
    """
    
    # Get the front bodice dimensions for reference
    front = pieces.get("front_bodice")
    if not front:
        return
    
    # Front bodice width and height
    width = front.dimensions.x
    height = front.dimensions.y
    
    print(f"Front bodice: width={width:.2f}m, height={height:.2f}m")
    
    # FRONT BODICE - Standing upright, facing +Y
    front.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.view_layer.objects.active = front
    bpy.ops.object.transform_apply(rotation=True)
    front.location = (0, 0.025, 0)  # Slightly forward
    
    # BACK BODICE - Standing upright, facing -Y (behind front)
    back = pieces.get("back_bodice")
    if back:
        back.rotation_euler = (math.radians(90), 0, math.radians(180))
        bpy.context.view_layer.objects.active = back
        bpy.ops.object.transform_apply(rotation=True)
        back.location = (0, -0.025, 0)  # Slightly back
    
    # LEFT SLEEVE - Rotated to attach at left armhole
    left_sleeve = pieces.get("sleeve_left")
    if left_sleeve:
        # Rotate sleeve to horizontal position
        left_sleeve.rotation_euler = (math.radians(90), math.radians(90), 0)
        bpy.context.view_layer.objects.active = left_sleeve
        bpy.ops.object.transform_apply(rotation=True)
        # Position at left side of bodice
        left_sleeve.location = (-width/2 - 0.1, 0, height * 0.7)
    
    # RIGHT SLEEVE - Mirror of left
    right_sleeve = pieces.get("sleeve_right")
    if right_sleeve:
        right_sleeve.rotation_euler = (math.radians(90), math.radians(-90), 0)
        bpy.context.view_layer.objects.active = right_sleeve
        bpy.ops.object.transform_apply(rotation=True)
        right_sleeve.location = (width/2 + 0.1, 0, height * 0.7)
    
    # NECK BAND - Positioned at neckline
    neck = pieces.get("neck_band")
    if neck:
        neck.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.objects.active = neck
        bpy.ops.object.transform_apply(rotation=True)
        neck.location = (0, 0, height + 0.05)


def weld_seams(obj_a, obj_b, threshold=WELD_THRESHOLD):
    """
    Join two objects and weld vertices that are close together.
    This simulates sewing seams.
    """
    if obj_a is None or obj_b is None:
        return None
    
    # Select both objects
    bpy.ops.object.select_all(action='DESELECT')
    obj_a.select_set(True)
    obj_b.select_set(True)
    bpy.context.view_layer.objects.active = obj_a
    
    # Join them
    bpy.ops.object.join()
    joined = bpy.context.active_object
    
    # Enter edit mode to merge vertices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Merge by distance (weld close vertices)
    bpy.ops.mesh.remove_doubles(threshold=threshold)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return joined


def join_all_pieces(pieces: dict):
    """Join all pattern pieces into one mesh and weld seams."""
    
    # Get list of valid pieces
    valid_pieces = [obj for obj in pieces.values() if obj is not None]
    
    if not valid_pieces:
        print("No pieces to join!")
        return None
    
    # Select all pieces
    bpy.ops.object.select_all(action='DESELECT')
    for obj in valid_pieces:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = valid_pieces[0]
    
    # Join all into one mesh
    bpy.ops.object.join()
    garment = bpy.context.active_object
    garment.name = "tshirt"
    
    # Weld seams by merging close vertices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Merge vertices that are close (this welds the seams)
    result = bpy.ops.mesh.remove_doubles(threshold=WELD_THRESHOLD)
    print(f"Welded seams: merged vertices")
    
    # Clean up mesh
    bpy.ops.mesh.dissolve_degenerate()
    bpy.ops.mesh.delete_loose()
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return garment


def add_cloth_physics(obj):
    """Add cloth simulation to make it drape naturally."""
    if obj is None:
        return
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Add cloth modifier
    cloth_mod = obj.modifiers.new(name="Cloth", type='CLOTH')
    
    if cloth_mod:
        settings = cloth_mod.settings
        settings.quality = 10
        settings.mass = 0.3
        settings.tension_stiffness = 15
        settings.compression_stiffness = 15
        settings.shear_stiffness = 15
        settings.bending_stiffness = 5
        
        # Enable self collision
        cloth_mod.collision_settings.use_self_collision = True
        cloth_mod.collision_settings.self_friction = 5.0


def add_armature_shape(garment):
    """Add a simple armature to give the shirt a body shape."""
    # Create a simple collision body (cylinder approximation)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15,  # ~30cm diameter torso
        depth=0.6,    # 60cm tall torso
        location=(0, 0, 0.3)
    )
    body = bpy.context.active_object
    body.name = "body_collision"
    
    # Add collision modifier
    coll_mod = body.modifiers.new(name="Collision", type='COLLISION')
    if coll_mod:
        coll_mod.settings.thickness_outer = 0.02
    
    return body


def run_simulation(frames=50):
    """Run cloth simulation for specified frames."""
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frames
    
    # Bake simulation
    bpy.ops.ptcache.bake_all(bake=True)
    
    # Go to final frame
    bpy.context.scene.frame_set(frames)


def apply_modifiers(obj):
    """Apply all modifiers to freeze the shape."""
    if obj is None:
        return
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    for mod in obj.modifiers:
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except:
            pass


def export_glb(obj, filepath):
    """Export object as GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        use_selection=True,
        export_format='GLB',
        export_materials='EXPORT'
    )
    print(f"Exported: {filepath}")


def main():
    print("=" * 50)
    print("MIRAAA T-Shirt 3D Assembly")
    print("=" * 50)
    
    # Clear scene
    clear_scene()
    
    # Import pattern pieces
    pieces = {}
    piece_names = ["front_bodice", "back_bodice", "sleeve", "neck_band"]
    
    for name in piece_names:
        svg_path = os.path.join(PATTERN_DIR, f"{name}.svg")
        if os.path.exists(svg_path):
            pieces[name] = import_svg_as_mesh(svg_path, name)
    
    if not pieces:
        print("ERROR: No pattern pieces imported!")
        return
    
    # Create duplicate sleeve for left/right
    if "sleeve" in pieces and pieces["sleeve"]:
        sleeve = pieces["sleeve"]
        bpy.context.view_layer.objects.active = sleeve
        sleeve.select_set(True)
        bpy.ops.object.duplicate()
        
        pieces["sleeve_left"] = sleeve
        pieces["sleeve_left"].name = "sleeve_left"
        pieces["sleeve_right"] = bpy.context.active_object
        pieces["sleeve_right"].name = "sleeve_right"
        del pieces["sleeve"]
    
    # Add material to all pieces
    fabric_mat = create_tshirt_material("fabric", color=(0.15, 0.15, 0.15, 1.0))
    for name, obj in pieces.items():
        if obj:
            obj.data.materials.clear()
            obj.data.materials.append(fabric_mat)
    
    # Position pieces in T-shirt formation
    print("\nPositioning pieces...")
    position_for_tshirt(pieces)
    
    # Join all pieces and weld seams
    print("\nJoining pieces and welding seams...")
    garment = join_all_pieces(pieces)
    
    if garment:
        print(f"\nFinal garment: {len(garment.data.vertices)} vertices, {len(garment.data.polygons)} faces")
        
        # Add a body shape for the shirt to drape on
        print("\nAdding body collision object...")
        body = add_armature_shape(garment)
        
        # Add cloth physics
        print("\nAdding cloth simulation...")
        add_cloth_physics(garment)
        
        # Run simulation
        print("\nRunning cloth simulation (50 frames)...")
        run_simulation(frames=50)
        
        # Apply modifiers
        print("\nApplying modifiers...")
        apply_modifiers(garment)
        
        # Delete the body collision object before export
        bpy.data.objects.remove(body, do_unlink=True)
        
        # Export
        export_glb(garment, OUTPUT_PATH)
        
        print("\n" + "=" * 50)
        print("T-SHIRT ASSEMBLY COMPLETE!")
        print(f"Output: {OUTPUT_PATH}")
        print("=" * 50)
    else:
        print("ERROR: Failed to create garment!")


if __name__ == "__main__":
    main()
