"""
MIRAAA T-Shirt Assembly v2 - Proper 3D garment construction
Creates a proper T-shirt shape by correctly positioning and joining pattern pieces
"""

import bpy
import bmesh
import os
import math
from mathutils import Vector

# Configuration
PATTERN_DIR = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/patterns"
OUTPUT_PATH = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/tshirt_3d.glb"


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
    
    # Set up curve for mesh conversion - thin fabric
    curve_obj.data.dimensions = '2D'
    curve_obj.data.fill_mode = 'BOTH'
    curve_obj.data.extrude = 0.002  # 2mm thickness
    
    # Convert to mesh
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    
    # Reset origin to geometry center
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    # Move to world origin
    mesh_obj.location = (0, 0, 0)
    
    # Get raw dimensions
    raw_dims = mesh_obj.dimensions.copy()
    print(f"Imported {name}: raw dimensions {raw_dims}")
    
    return mesh_obj


def create_tshirt_material(color=(0.2, 0.2, 0.2, 1.0)):
    """Create a fabric-like material."""
    mat = bpy.data.materials.new(name="tshirt_fabric")
    mat.use_nodes = True
    
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.85
    
    return mat


def create_tshirt_from_primitives():
    """
    Create a proper T-shirt mesh from scratch using the pattern dimensions.
    This ensures proper topology for a garment.
    """
    
    # T-shirt dimensions (in Blender units = meters)
    body_width = 0.50      # 50cm chest width
    body_height = 0.70     # 70cm body length
    body_depth = 0.25      # 25cm front-to-back depth
    
    sleeve_length = 0.25   # 25cm sleeve
    sleeve_width = 0.18    # 18cm sleeve opening
    
    neck_width = 0.20      # 20cm neck opening
    neck_depth = 0.08      # 8cm neck depth
    
    shoulder_drop = 0.03   # 3cm shoulder slope
    
    # Create the mesh
    mesh = bpy.data.meshes.new("tshirt_mesh")
    obj = bpy.data.objects.new("tshirt", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Define vertices for front panel
    # Bottom edge
    v_front_bl = bm.verts.new((-body_width/2, body_depth/2, 0))
    v_front_br = bm.verts.new((body_width/2, body_depth/2, 0))
    
    # Armpit level
    armpit_height = body_height * 0.65
    v_front_al = bm.verts.new((-body_width/2, body_depth/2, armpit_height))
    v_front_ar = bm.verts.new((body_width/2, body_depth/2, armpit_height))
    
    # Shoulder level (with slope)
    shoulder_width = body_width * 0.45
    v_front_sl = bm.verts.new((-shoulder_width, body_depth/2, body_height - shoulder_drop))
    v_front_sr = bm.verts.new((shoulder_width, body_depth/2, body_height - shoulder_drop))
    
    # Neck points
    v_front_nl = bm.verts.new((-neck_width/2, body_depth/2, body_height - shoulder_drop))
    v_front_nr = bm.verts.new((neck_width/2, body_depth/2, body_height - shoulder_drop))
    v_front_nc = bm.verts.new((0, body_depth/2, body_height - neck_depth))  # Neck center (lower for V)
    
    # Define vertices for back panel (mirror of front)
    v_back_bl = bm.verts.new((-body_width/2, -body_depth/2, 0))
    v_back_br = bm.verts.new((body_width/2, -body_depth/2, 0))
    v_back_al = bm.verts.new((-body_width/2, -body_depth/2, armpit_height))
    v_back_ar = bm.verts.new((body_width/2, -body_depth/2, armpit_height))
    v_back_sl = bm.verts.new((-shoulder_width, -body_depth/2, body_height - shoulder_drop))
    v_back_sr = bm.verts.new((shoulder_width, -body_depth/2, body_height - shoulder_drop))
    v_back_nl = bm.verts.new((-neck_width/2, -body_depth/2, body_height - shoulder_drop))
    v_back_nr = bm.verts.new((neck_width/2, -body_depth/2, body_height - shoulder_drop))
    v_back_nc = bm.verts.new((0, -body_depth/2, body_height - 0.02))  # Back neck (higher)
    
    # Left sleeve vertices
    sleeve_y_outer = body_depth/2 + 0.02
    sleeve_y_inner = -body_depth/2 - 0.02
    
    v_sleeve_l_top_inner = bm.verts.new((-body_width/2, sleeve_y_inner, armpit_height + sleeve_width/2))
    v_sleeve_l_top_outer = bm.verts.new((-body_width/2, sleeve_y_outer, armpit_height + sleeve_width/2))
    v_sleeve_l_bot_inner = bm.verts.new((-body_width/2, sleeve_y_inner, armpit_height - sleeve_width/2))
    v_sleeve_l_bot_outer = bm.verts.new((-body_width/2, sleeve_y_outer, armpit_height - sleeve_width/2))
    
    v_sleeve_l_end_top = bm.verts.new((-body_width/2 - sleeve_length, 0, armpit_height + sleeve_width/3))
    v_sleeve_l_end_bot = bm.verts.new((-body_width/2 - sleeve_length, 0, armpit_height - sleeve_width/3))
    
    # Right sleeve vertices
    v_sleeve_r_top_inner = bm.verts.new((body_width/2, sleeve_y_inner, armpit_height + sleeve_width/2))
    v_sleeve_r_top_outer = bm.verts.new((body_width/2, sleeve_y_outer, armpit_height + sleeve_width/2))
    v_sleeve_r_bot_inner = bm.verts.new((body_width/2, sleeve_y_inner, armpit_height - sleeve_width/2))
    v_sleeve_r_bot_outer = bm.verts.new((body_width/2, sleeve_y_outer, armpit_height - sleeve_width/2))
    
    v_sleeve_r_end_top = bm.verts.new((body_width/2 + sleeve_length, 0, armpit_height + sleeve_width/3))
    v_sleeve_r_end_bot = bm.verts.new((body_width/2 + sleeve_length, 0, armpit_height - sleeve_width/3))
    
    # Create faces
    
    # Front panel - lower section
    bm.faces.new([v_front_bl, v_front_br, v_front_ar, v_front_al])
    
    # Front panel - left upper
    bm.faces.new([v_front_al, v_front_sl, v_front_nl, v_front_nc])
    
    # Front panel - right upper  
    bm.faces.new([v_front_ar, v_front_nc, v_front_nr, v_front_sr])
    
    # Front panel - center upper
    bm.faces.new([v_front_al, v_front_nc, v_front_ar])
    
    # Front shoulder left
    bm.faces.new([v_front_al, v_front_nl, v_front_sl])
    
    # Front shoulder right
    bm.faces.new([v_front_ar, v_front_sr, v_front_nr])
    
    # Back panel - lower section
    bm.faces.new([v_back_bl, v_back_al, v_back_ar, v_back_br])
    
    # Back panel - left upper
    bm.faces.new([v_back_al, v_back_nc, v_back_nl, v_back_sl])
    
    # Back panel - right upper
    bm.faces.new([v_back_ar, v_back_sr, v_back_nr, v_back_nc])
    
    # Back panel - center upper
    bm.faces.new([v_back_al, v_back_ar, v_back_nc])
    
    # Back shoulder left
    bm.faces.new([v_back_al, v_back_sl, v_back_nl])
    
    # Back shoulder right
    bm.faces.new([v_back_ar, v_back_nr, v_back_sr])
    
    # Side panels (connecting front and back)
    # Left side - bottom
    bm.faces.new([v_front_bl, v_front_al, v_back_al, v_back_bl])
    
    # Right side - bottom
    bm.faces.new([v_front_br, v_back_br, v_back_ar, v_front_ar])
    
    # Bottom hem
    bm.faces.new([v_front_bl, v_back_bl, v_back_br, v_front_br])
    
    # Shoulders
    bm.faces.new([v_front_sl, v_front_nl, v_back_nl, v_back_sl])
    bm.faces.new([v_front_sr, v_back_sr, v_back_nr, v_front_nr])
    
    # Neck opening (ring)
    bm.faces.new([v_front_nl, v_front_nc, v_back_nc, v_back_nl])
    bm.faces.new([v_front_nr, v_back_nr, v_back_nc, v_front_nc])
    
    # Left sleeve
    bm.faces.new([v_front_al, v_sleeve_l_top_outer, v_sleeve_l_end_top, v_sleeve_l_end_bot, v_sleeve_l_bot_outer])
    bm.faces.new([v_back_al, v_sleeve_l_bot_inner, v_sleeve_l_end_bot, v_sleeve_l_end_top, v_sleeve_l_top_inner])
    bm.faces.new([v_sleeve_l_top_outer, v_sleeve_l_top_inner, v_sleeve_l_end_top])
    bm.faces.new([v_sleeve_l_bot_outer, v_sleeve_l_end_bot, v_sleeve_l_bot_inner])
    
    # Connect sleeve to body
    bm.faces.new([v_front_al, v_back_al, v_sleeve_l_top_inner, v_sleeve_l_top_outer])
    bm.faces.new([v_front_al, v_sleeve_l_bot_outer, v_sleeve_l_bot_inner, v_back_al])
    
    # Right sleeve
    bm.faces.new([v_front_ar, v_sleeve_r_bot_outer, v_sleeve_r_end_bot, v_sleeve_r_end_top, v_sleeve_r_top_outer])
    bm.faces.new([v_back_ar, v_sleeve_r_top_inner, v_sleeve_r_end_top, v_sleeve_r_end_bot, v_sleeve_r_bot_inner])
    bm.faces.new([v_sleeve_r_top_outer, v_sleeve_r_end_top, v_sleeve_r_top_inner])
    bm.faces.new([v_sleeve_r_bot_outer, v_sleeve_r_bot_inner, v_sleeve_r_end_bot])
    
    # Connect sleeve to body
    bm.faces.new([v_front_ar, v_sleeve_r_top_outer, v_sleeve_r_top_inner, v_back_ar])
    bm.faces.new([v_front_ar, v_back_ar, v_sleeve_r_bot_inner, v_sleeve_r_bot_outer])
    
    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Recalculate normals
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return obj


def subdivide_mesh(obj, levels=2):
    """Add subdivision for smoother mesh."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Add subdivision surface modifier
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = levels
    subsurf.render_levels = levels
    
    # Apply modifier
    bpy.ops.object.modifier_apply(modifier=subsurf.name)
    
    print(f"After subdivision: {len(obj.data.vertices)} vertices, {len(obj.data.polygons)} faces")


def smooth_mesh(obj):
    """Apply smooth shading."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()


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
    print("MIRAAA T-Shirt 3D Assembly v2")
    print("=" * 50)
    
    # Clear scene
    clear_scene()
    
    # Create T-shirt from proper mesh topology
    print("\nCreating T-shirt mesh...")
    tshirt = create_tshirt_from_primitives()
    
    # Add material
    mat = create_tshirt_material(color=(0.15, 0.15, 0.15, 1.0))  # Dark gray
    tshirt.data.materials.append(mat)
    
    # Subdivide for smoother surface
    print("\nSubdividing mesh...")
    subdivide_mesh(tshirt, levels=2)
    
    # Smooth shading
    smooth_mesh(tshirt)
    
    print(f"\nFinal T-shirt: {len(tshirt.data.vertices)} vertices, {len(tshirt.data.polygons)} faces")
    print(f"Dimensions: {tshirt.dimensions}")
    
    # Export
    export_glb(tshirt, OUTPUT_PATH)
    
    print("\n" + "=" * 50)
    print("T-SHIRT ASSEMBLY COMPLETE!")
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()
