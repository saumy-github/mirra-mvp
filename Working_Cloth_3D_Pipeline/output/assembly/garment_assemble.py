"""
MIRAAA Pipeline - Blender Garment Assembly Script
Auto-generated script for garment assembly with GarmentTool

Run this script in Blender:
    blender --background --python garment_assemble.py
"""

import bpy
import os
import math
from pathlib import Path

# Configuration
PATTERN_DIR = r"output/patterns"
OUTPUT_PATH = r"output/assembly/garment.glb"
OUTPUT_FORMAT = "GLB"

# Pattern pieces to import
PATTERN_PIECES = [
    "front_bodice",
    "back_bodice", 
    "sleeve",
    "neck_band"
]

# Seam definitions
SEAMS = [
    {
        "type": "side_seam",
        "from_piece": "front_bodice",
        "from_edge": "left_side",
        "to_piece": "back_bodice",
        "to_edge": "right_side",
        "spacing": 0.5,
        "strength": 1.0
    },
    {
        "type": "shoulder",
        "from_piece": "front_bodice",
        "from_edge": "shoulder",
        "to_piece": "back_bodice",
        "to_edge": "shoulder",
        "spacing": 0.5,
        "strength": 1.0
    },
    {
        "type": "armhole",
        "from_piece": "sleeve",
        "from_edge": "sleeve_cap",
        "to_piece": "front_bodice + back_bodice",
        "to_edge": "armhole",
        "spacing": 0.5,
        "strength": 1.0
    },
    {
        "type": "neck",
        "from_piece": "neck_band",
        "from_edge": "edge",
        "to_piece": "front_bodice + back_bodice",
        "to_edge": "neckline",
        "spacing": 0.5,
        "strength": 1.0
    }
]

# Cloth simulation settings
CLOTH_SETTINGS = {
    "quality": 5,
    "mass": 0.3,
    "air_damping": 1.0,
    "bending_stiffness": 0.5,
    "tension_stiffness": 15.0,
    "compression_stiffness": 15.0,
    "shear_stiffness": 5.0,
    "self_collision": False
}

FRAME_START = 1
FRAME_END = 120


def clear_scene():
    """Clear the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Also remove any imported collections
    for col in bpy.data.collections:
        if col.name != 'Scene Collection':
            bpy.data.collections.remove(col)


def import_svg_pattern(svg_path: str, name: str) -> bpy.types.Object:
    """Import an SVG file and convert to mesh with proper faces."""
    # Store existing objects before import
    existing_objects = set(bpy.data.objects.keys())
    
    # Import SVG
    bpy.ops.import_curve.svg(filepath=svg_path)
    
    # Find newly imported objects
    new_objects = [obj for obj in bpy.data.objects if obj.name not in existing_objects]
    
    if not new_objects:
        print(f"Warning: No objects imported from {svg_path}")
        return None
    
    # Select all new curve objects
    bpy.ops.object.select_all(action='DESELECT')
    curve_objects = []
    for obj in new_objects:
        if obj.type == 'CURVE':
            obj.select_set(True)
            curve_objects.append(obj)
    
    if not curve_objects:
        print(f"Warning: No curve objects found in {svg_path}")
        return None
    
    # Set the first selected as active
    bpy.context.view_layer.objects.active = curve_objects[0]
    
    # Join all curves into one if multiple
    if len(curve_objects) > 1:
        bpy.ops.object.join()
    
    curve_obj = bpy.context.active_object
    curve_obj.name = name + "_curve"
    
    # Set curve to 2D and filled
    curve_obj.data.dimensions = '2D'
    curve_obj.data.fill_mode = 'BOTH'
    
    # Give it slight extrusion to make it visible
    curve_obj.data.extrude = 0.01  # 1cm thickness
    
    # Convert curve to mesh
    bpy.ops.object.convert(target='MESH')
    
    # Get mesh object
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    
    # Scale UP by 10 - Blender SVG import scales down significantly
    # This makes garment ~70cm wide which is realistic for a t-shirt
    mesh_obj.scale = (10, 10, 10)
    bpy.ops.object.transform_apply(scale=True)
    
    # Add a basic material so it's visible
    mat = bpy.data.materials.new(name=f"{name}_material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)  # Light gray
    mesh_obj.data.materials.append(mat)
    
    print(f"Imported {name}: {len(mesh_obj.data.vertices)} vertices, {len(mesh_obj.data.polygons)} faces, dimensions: {mesh_obj.dimensions}")
    
    return mesh_obj


def position_pattern_pieces(pieces: dict):
    """Position pattern pieces in 3D space for assembly."""
    
    # Front bodice - centered, facing forward
    if "front_bodice" in pieces and pieces["front_bodice"] is not None:
        obj = pieces["front_bodice"]
        obj.location = (0, 0.5, 0)
        obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Back bodice - behind front
    if "back_bodice" in pieces and pieces["back_bodice"] is not None:
        obj = pieces["back_bodice"]
        obj.location = (0, -0.5, 0)
        obj.rotation_euler = (math.radians(90), 0, math.radians(180))
    
    # Sleeves
    if "sleeve" in pieces and pieces["sleeve"] is not None:
        obj = pieces["sleeve"]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Create a copy for the right sleeve
        bpy.ops.object.duplicate()
        right_sleeve = bpy.context.active_object
        right_sleeve.name = "sleeve_right"
        pieces["sleeve_right"] = right_sleeve
        
        # Position sleeves
        obj.name = "sleeve_left"
        obj.location = (-1.5, 0, 0)
        obj.rotation_euler = (math.radians(90), 0, math.radians(90))
        
        right_sleeve.location = (1.5, 0, 0)
        right_sleeve.rotation_euler = (math.radians(90), 0, math.radians(-90))
    
    # Neck band
    if "neck_band" in pieces and pieces["neck_band"] is not None:
        obj = pieces["neck_band"]
        obj.location = (0, 0, 1.5)
        obj.rotation_euler = (0, 0, 0)


def setup_cloth_simulation(obj: bpy.types.Object):
    """Add cloth simulation modifier to an object."""
    if obj is None:
        print("Warning: Cannot setup cloth on None object")
        return
    
    if obj.type != 'MESH':
        print(f"Warning: Object {obj.name} is not a mesh, skipping cloth")
        return
    
    # Make sure object is active and selected
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Add cloth modifier
    cloth_mod = obj.modifiers.new(name="Cloth", type='CLOTH')
    
    if cloth_mod is None:
        print(f"Warning: Could not create cloth modifier for {obj.name}")
        return
    
    cloth = cloth_mod.settings
    
    # Apply settings
    cloth.quality = CLOTH_SETTINGS["quality"]
    cloth.mass = CLOTH_SETTINGS["mass"]
    cloth.air_damping = CLOTH_SETTINGS["air_damping"]
    
    # Stiffness
    cloth.tension_stiffness = CLOTH_SETTINGS["tension_stiffness"]
    cloth.compression_stiffness = CLOTH_SETTINGS["compression_stiffness"]
    cloth.shear_stiffness = CLOTH_SETTINGS["shear_stiffness"]
    cloth.bending_stiffness = CLOTH_SETTINGS["bending_stiffness"]
    
    # Collision settings
    cloth_mod.collision_settings.use_self_collision = CLOTH_SETTINGS["self_collision"]


def create_sewing_springs(pieces: dict):
    """
    Create sewing springs between pattern pieces.
    Uses vertex groups to define seam edges.
    """
    for seam in SEAMS:
        from_piece = seam["from_piece"]
        to_piece = seam["to_piece"]
        
        # Handle combined pieces (e.g., "front_bodice + back_bodice")
        if "+" in to_piece:
            # This would require more complex handling
            # For now, we'll create springs to the primary piece
            to_piece = to_piece.split("+")[0].strip()
        
        if from_piece in pieces and to_piece in pieces:
            create_spring_constraint(
                pieces[from_piece],
                pieces[to_piece],
                seam["from_edge"],
                seam["to_edge"]
            )


def create_spring_constraint(obj_a, obj_b, edge_a, edge_b):
    """Create spring constraints between two edges."""
    # This is a simplified version - GarmentTool provides better sewing
    # For production, use the GarmentTool addon's sewing features
    
    # Create an empty to parent both objects for simulation
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    empty = bpy.context.active_object
    empty.name = f"seam_{obj_a.name}_to_{obj_b.name}"
    
    # In a real implementation, you would:
    # 1. Identify matching vertices on both edges
    # 2. Create sewing springs between corresponding vertices
    # 3. Use GarmentTool's sewing functionality
    
    print(f"Created seam: {obj_a.name}.{edge_a} -> {obj_b.name}.{edge_b}")


def bake_simulation():
    """Bake the cloth simulation."""
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end = FRAME_END
    
    # Bake all cloth simulations
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            if mod.type == 'CLOTH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.ptcache.bake_all(bake=True)
                break
    
    # Go to final frame
    bpy.context.scene.frame_set(FRAME_END)


def apply_modifiers_and_join(pieces: dict) -> bpy.types.Object:
    """Apply modifiers and join all pieces into single mesh."""
    
    # Select all pattern pieces
    bpy.ops.object.select_all(action='DESELECT')
    
    for name, obj in pieces.items():
        obj.select_set(True)
        
        # Apply cloth modifier
        bpy.context.view_layer.objects.active = obj
        for mod in obj.modifiers:
            if mod.type == 'CLOTH':
                bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # Join all pieces
    if pieces:
        first_piece = list(pieces.values())[0]
        bpy.context.view_layer.objects.active = first_piece
        bpy.ops.object.join()
        
        joined_obj = bpy.context.active_object
        joined_obj.name = "garment"
        return joined_obj
    
    return None


def export_mesh(obj: bpy.types.Object, output_path: str, format: str):
    """Export the final mesh."""
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    if format.upper() == "GLB":
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            use_selection=True,
            export_format='GLB'
        )
    elif format.upper() == "FBX":
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=True
        )
    elif format.upper() == "OBJ":
        bpy.ops.export_scene.obj(
            filepath=output_path,
            use_selection=True
        )
    
    print(f"Exported: {output_path}")


def main():
    """Main assembly pipeline."""
    print("Starting MIRAAA Garment Assembly...")
    
    # Clear scene
    clear_scene()
    
    # Import pattern pieces
    pieces = {}
    for piece_name in PATTERN_PIECES:
        svg_path = os.path.join(PATTERN_DIR, f"{piece_name}.svg")
        if os.path.exists(svg_path):
            print(f"Importing: {piece_name}")
            result = import_svg_pattern(svg_path, piece_name)
            if result is not None:
                pieces[piece_name] = result
        else:
            print(f"Warning: {svg_path} not found")
    
    if not pieces:
        print("Error: No pattern pieces imported successfully")
        return
    
    # Filter out None values
    pieces = {k: v for k, v in pieces.items() if v is not None}
    
    # Position pieces
    position_pattern_pieces(pieces)
    
    # Setup cloth simulation
    for name, obj in pieces.items():
        if obj is not None:
            setup_cloth_simulation(obj)
    
    # Create sewing connections
    create_sewing_springs(pieces)
    
    # Run simulation
    print("Baking cloth simulation...")
    bake_simulation()
    
    # Finalize and export
    print("Finalizing mesh...")
    garment = apply_modifiers_and_join(pieces)
    
    if garment:
        export_mesh(garment, OUTPUT_PATH, OUTPUT_FORMAT)
        print("Assembly complete!")
    else:
        print("Error: No garment mesh created")


if __name__ == "__main__":
    main()
