import bpy
import os

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Pattern directory
pattern_dir = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/patterns"
output_path = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/debug_garment.glb"

pieces = {}

for piece_name in ["front_bodice", "back_bodice", "sleeve", "neck_band"]:
    svg_path = os.path.join(pattern_dir, f"{piece_name}.svg")
    if not os.path.exists(svg_path):
        print(f"Not found: {svg_path}")
        continue
    
    # Track objects before import
    existing = set(bpy.data.objects.keys())
    
    # Import SVG
    bpy.ops.import_curve.svg(filepath=svg_path)
    
    # Find new objects
    new_objs = [obj for obj in bpy.data.objects if obj.name not in existing]
    
    # Select and join curves
    bpy.ops.object.select_all(action='DESELECT')
    curves = [obj for obj in new_objs if obj.type == 'CURVE']
    
    if not curves:
        print(f"No curves in {piece_name}")
        continue
    
    for c in curves:
        c.select_set(True)
    bpy.context.view_layer.objects.active = curves[0]
    
    if len(curves) > 1:
        bpy.ops.object.join()
    
    curve_obj = bpy.context.active_object
    
    # Set fill mode
    curve_obj.data.dimensions = '2D'
    curve_obj.data.fill_mode = 'BOTH'
    curve_obj.data.extrude = 0.01  # 1cm thickness for visibility
    
    # Convert to mesh
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    mesh_obj.name = piece_name
    
    # Blender SVG import scales down significantly
    # Scale UP by 10 to make garment visible (~70cm = 0.7m becomes reasonable)
    mesh_obj.scale = (10, 10, 10)
    bpy.ops.object.transform_apply(scale=True)
    print(f"  Dimensions after 10x scale: {mesh_obj.dimensions}")
    
    # Add material
    mat = bpy.data.materials.new(name=f"{piece_name}_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.2, 0.2, 1.0)  # Red for visibility
    mesh_obj.data.materials.append(mat)
    
    pieces[piece_name] = mesh_obj
    
    print(f"{piece_name}: {len(mesh_obj.data.vertices)} verts, {len(mesh_obj.data.polygons)} faces")
    print(f"  Location: {mesh_obj.location}")
    print(f"  Dimensions: {mesh_obj.dimensions}")

# Position pieces laid out flat (not overlapping)
if "front_bodice" in pieces:
    pieces["front_bodice"].location = (0, 0, 0)
if "back_bodice" in pieces:
    pieces["back_bodice"].location = (2, 0, 0)  # 2 meters to the right
if "sleeve" in pieces:
    pieces["sleeve"].location = (0, 3, 0)  # 3 meters forward
if "neck_band" in pieces:
    pieces["neck_band"].location = (2, 3, 0)

# Select all and export
bpy.ops.object.select_all(action='SELECT')

bpy.ops.export_scene.gltf(
    filepath=output_path,
    use_selection=True,
    export_format='GLB',
    export_materials='EXPORT'
)

print(f"\nExported to: {output_path}")
print(f"Total objects: {len(pieces)}")
