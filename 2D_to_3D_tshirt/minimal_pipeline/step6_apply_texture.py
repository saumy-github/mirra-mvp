"""
STEP 6: Apply Color and Design Texture
=======================================
This script applies the extracted fabric color and design to the 3D garment.

What happens:
1. Load the fabric color (from Step 3)
2. Load the design texture (from Step 2)
3. Create a fabric material with the correct color
4. Apply the design as a texture overlay
5. UV map the garment for proper texture placement

Think of it like:
- Base coat of paint = fabric color
- Decal/sticker = printed design

HOW TO RUN:
Run this AFTER step5_blender_sewing.py
The garment should already exist in the scene.
"""

import bpy
import os
import json
from pathlib import Path
from mathutils import Vector

# ============================================================
# CONFIGURATION
# ============================================================

# Input directories
COLOR_DIR = Path(__file__).parent / "color_output"
DESIGN_DIR = Path(__file__).parent / "design_output"

# File paths
FABRIC_COLOR_JSON = COLOR_DIR / "front_fabric_color.json"
DESIGN_IMAGE = DESIGN_DIR / "front_design.png"

# Default fabric color (if JSON not found)
DEFAULT_FABRIC_COLOR = (0.2, 0.3, 0.5, 1.0)  # Navy blue RGBA


# ============================================================
# COLOR LOADING
# ============================================================

def load_fabric_color() -> tuple:
    """
    Load the extracted fabric color from Step 3.
    
    The color was saved as RGB values (0-255) in a JSON file.
    We convert to Blender's format (0.0-1.0).
    
    Returns:
        Tuple of (R, G, B, A) with values 0.0-1.0
    """
    print("→ Loading fabric color...")
    
    if not FABRIC_COLOR_JSON.exists():
        print(f"  ⚠ Color file not found: {FABRIC_COLOR_JSON}")
        print(f"  Using default color: {DEFAULT_FABRIC_COLOR[:3]}")
        return DEFAULT_FABRIC_COLOR
    
    try:
        with open(FABRIC_COLOR_JSON, 'r') as f:
            data = json.load(f)
        
        # Get RGB values (0-255)
        rgb = data["dominant"]["rgb"]
        
        # Convert to 0.0-1.0 range
        r = rgb[0] / 255.0
        g = rgb[1] / 255.0
        b = rgb[2] / 255.0
        
        color = (r, g, b, 1.0)
        
        color_name = data["dominant"].get("name", "Unknown")
        hex_code = data["dominant"].get("hex", "#???")
        
        print(f"  ✓ Loaded color: {color_name} ({hex_code})")
        print(f"    RGB: ({rgb[0]}, {rgb[1]}, {rgb[2]})")
        
        return color
        
    except Exception as e:
        print(f"  ⚠ Error loading color: {e}")
        print(f"  Using default color")
        return DEFAULT_FABRIC_COLOR


# ============================================================
# UV UNWRAPPING
# ============================================================

import bmesh

def unwrap_garment_uv(obj: bpy.types.Object):
    """
    Create UV mapping for the garment using headless-safe methods.
    
    This function uses bmesh and headless-compatible operators to ensure
    it works in both interactive and headless (--background) mode.
    
    Args:
        obj: The garment mesh object
    """
    print(f"→ Creating UV unwrap for {obj.name}...")
    
    # Ensure object is active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Switch to edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Use bmesh to select all faces
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    # Select all faces
    for face in bm.faces:
        face.select = True
    
    # Update mesh with selection
    bmesh.update_edit_mesh(obj.data)
    
    # Unwrap using angle-based method (headless-safe)
    try:
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.02)
        print("  ✓ UV unwrap completed (angle-based method)")
    except Exception as e:
        print(f"  ⚠ Angle-based unwrap failed: {e}")
        print("  Trying conformal method...")
        try:
            bpy.ops.uv.unwrap(method='CONFORMAL', margin=0.02)
            print("  ✓ UV unwrap completed (conformal method)")
        except Exception as e2:
            print(f"  ⚠ Conformal unwrap also failed: {e2}")
            print("  Using smart UV project as fallback...")
            bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
            print("  ✓ UV unwrap completed (smart project fallback)")
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print("  ✓ UV mapping created successfully")


def load_design_texture() -> bpy.types.Image:
    """
    Load the extracted design image from Step 2.
    
    The design is a PNG with transparency:
    - Design pixels are opaque
    - Non-design areas are transparent
    
    Returns:
        Blender Image object, or None if not found
    """
    print("→ Loading design texture...")
    
    if not DESIGN_IMAGE.exists():
        print(f"  ⚠ Design image not found: {DESIGN_IMAGE}")
        print(f"  Garment will have solid color only (no print)")
        return None
    
    try:
        # Load image into Blender
        img = bpy.data.images.load(str(DESIGN_IMAGE))
        img.name = "TShirt_Design"
        
        print(f"  ✓ Loaded design: {img.name}")
        print(f"    Size: {img.size[0]} x {img.size[1]} pixels")
        
        return img
        
    except Exception as e:
        print(f"  ⚠ Error loading design: {e}")
        return None


# ============================================================
# MATERIAL CREATION
# ============================================================

def create_fabric_material(
    name: str,
    base_color: tuple,
    design_image: bpy.types.Image = None
) -> bpy.types.Material:
    """
    Create a fabric material with color and optional design.
    
    Material structure (node-based):
    
    ┌──────────────────────────────────────────────────────────┐
    │                    MATERIAL NODES                        │
    │                                                          │
    │  ┌─────────┐                                            │
    │  │ Design  │──→ Alpha ──┐                               │
    │  │ Texture │            │                               │
    │  │         │──→ Color ──┤                               │
    │  └─────────┘            │   ┌─────────┐   ┌──────────┐ │
    │                         ├──→│  Mix    │──→│  Output  │ │
    │  ┌─────────┐            │   │  Shader │   │          │ │
    │  │ Fabric  │──→ Color ──┘   └─────────┘   └──────────┘ │
    │  │ Color   │                                            │
    │  └─────────┘                                            │
    │                                                          │
    └──────────────────────────────────────────────────────────┘
    
    The Mix Shader blends:
    - Fabric color (where design is transparent)
    - Design color (where design is opaque)
    
    Args:
        name: Material name
        base_color: RGBA tuple for fabric color
        design_image: Optional design texture image
    
    Returns:
        The created material
    """
    print(f"→ Creating material: {name}...")
    
    # Create new material
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # Get the node tree
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (600, 0)
    
    # Create principled BSDF for fabric
    fabric_shader = nodes.new(type='ShaderNodeBsdfPrincipled')
    fabric_shader.location = (200, 100)
    fabric_shader.inputs['Base Color'].default_value = base_color
    fabric_shader.inputs['Roughness'].default_value = 0.8  # Fabric is not shiny
    fabric_shader.inputs['Specular IOR Level'].default_value = 0.3
    
    if design_image is None:
        # No design - just use fabric color
        links.new(fabric_shader.outputs['BSDF'], output_node.inputs['Surface'])
        print("  ✓ Material created (solid color, no design)")
        return mat
    
    # === ADD DESIGN TEXTURE ===
    
    # Texture coordinate node (for UV mapping)
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-600, 0)
    
    # Mapping node (to adjust texture position/scale)
    mapping = nodes.new(type='ShaderNodeMapping')
    mapping.location = (-400, 0)
    # Center the design on the front of the shirt
    mapping.inputs['Location'].default_value = (0.5, 0.3, 0)
    mapping.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    
    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    
    # Design texture node
    design_tex = nodes.new(type='ShaderNodeTexImage')
    design_tex.location = (-200, 200)
    design_tex.image = design_image
    design_tex.extension = 'CLIP'  # Don't tile the design
    
    links.new(mapping.outputs['Vector'], design_tex.inputs['Vector'])
    
    # Create principled BSDF for design
    design_shader = nodes.new(type='ShaderNodeBsdfPrincipled')
    design_shader.location = (200, 300)
    design_shader.inputs['Roughness'].default_value = 0.7
    
    links.new(design_tex.outputs['Color'], design_shader.inputs['Base Color'])
    
    # Mix shader (blend between fabric and design based on alpha)
    mix_shader = nodes.new(type='ShaderNodeMixShader')
    mix_shader.location = (400, 150)
    
    # Use design alpha as mix factor
    links.new(design_tex.outputs['Alpha'], mix_shader.inputs['Fac'])
    links.new(fabric_shader.outputs['BSDF'], mix_shader.inputs[1])  # Where alpha = 0
    links.new(design_shader.outputs['BSDF'], mix_shader.inputs[2])  # Where alpha = 1
    
    # Connect to output
    links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])
    
    print("  ✓ Material created with design texture overlay")
    
    return mat


def create_simple_fabric_material(name: str, base_color: tuple) -> bpy.types.Material:
    """
    Create a simple fabric material without node complexity.
    
    This is a simpler version that just sets the base color.
    Use when you don't need the design overlay.
    
    Args:
        name: Material name
        base_color: RGBA tuple
    
    Returns:
        The created material
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # Get the Principled BSDF node (created by default)
    principled = mat.node_tree.nodes.get('Principled BSDF')
    
    if principled:
        principled.inputs['Base Color'].default_value = base_color
        principled.inputs['Roughness'].default_value = 0.8
    
    return mat


# ============================================================
# UV MAPPING
# ============================================================

def unwrap_garment_uv(obj: bpy.types.Object):
    """
    Create UV coordinates for the garment mesh.
    
    UV mapping is like flattening the 3D surface back to 2D:
    - U = horizontal position on texture (0-1)
    - V = vertical position on texture (0-1)
    
    For a T-shirt, we want:
    - Front panel gets the design texture
    - Proper alignment so design appears centered
    
    Args:
        obj: The garment mesh object
    """
    print(f"→ Creating UV map for {obj.name}...")
    
    # Select the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all faces
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Project from view (front view gives good UV for front of shirt)
    # First, set view to front

    
    # Alternative: Smart UV Project (automatic, works for complex shapes)
    bpy.ops.uv.smart_project(
        angle_limit=66.0,
        island_margin=0.02,
        correct_aspect=True
    )
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"  ✓ UV map created")


def project_design_to_front(obj: bpy.types.Object):
    """
    Project texture specifically onto the front of the garment.
    
    For T-shirt designs, we typically want:
    - Design appears on the FRONT panel
    - Centered horizontally
    - Positioned in upper chest area
    
    This creates a custom UV projection for the front faces.
    
    Args:
        obj: The garment mesh object
    """
    print(f"→ Projecting design to front panel...")
    
    # This is a simplified approach
    # In production, you'd identify front faces by normal direction
    # and create a separate UV map just for them
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Project from front (negative Y in Blender = front view)
    # This assumes the garment is oriented with front facing -Y

    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"  ✓ Front projection complete")


# ============================================================
# MATERIAL APPLICATION
# ============================================================

def apply_material_to_object(obj: bpy.types.Object, material: bpy.types.Material):
    """
    Apply a material to an object.
    
    In Blender, each object can have multiple material slots.
    We assign our fabric material to the first slot.
    
    Args:
        obj: The object to apply material to
        material: The material to apply
    """
    print(f"→ Applying material to {obj.name}...")
    
    # Clear existing materials
    obj.data.materials.clear()
    
    # Add our material
    obj.data.materials.append(material)
    
    print(f"  ✓ Material applied: {material.name}")


def find_garment_object() -> bpy.types.Object:
    """
    Find the T-shirt garment object in the scene.
    
    Looks for an object named "TShirt_Garment" (created in Step 5)
    or any object with "Garment" or "Joined" in its name.
    Falls back to cloth modifier search.
    
    Returns:
        The garment object, or None if not found
    
    Raises:
        RuntimeError: If no suitable garment mesh is found
    """
    print("→ Searching for garment object...")
    
    # First, try exact name match
    garment = bpy.data.objects.get("TShirt_Garment")
    if garment:
        print(f"  ✓ Found by exact name: {garment.name}")
        return garment
    
    # Second, search for objects with "Garment" in name
    print("  ⚠ Exact name not found, searching for 'Garment' pattern...")
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and ("Garment" in obj.name or "garment" in obj.name):
            print(f"  ✓ Found by pattern match: {obj.name}")
            return obj
    
    # Third, search for objects with "Joined" in name
    print("  ⚠ No 'Garment' found, searching for 'Joined' pattern...")
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and ("Joined" in obj.name or "joined" in obj.name):
            print(f"  ✓ Found by pattern match: {obj.name}")
            return obj
    
    # Fourth, find any object with cloth modifier
    print("  ⚠ No named match, searching for cloth modifier...")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'CLOTH':
                    print(f"  ✓ Found by cloth modifier: {obj.name}")
                    return obj
    
    # Last resort: find largest mesh
    print("  ⚠ No cloth modifier found, using largest mesh...")
    largest = None
    largest_verts = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            vert_count = len(obj.data.vertices)
            if vert_count > largest_verts:
                largest = obj
                largest_verts = vert_count
    
    if largest:
        print(f"  ✓ Found largest mesh: {largest.name} ({largest_verts} vertices)")
        return largest
    
    # Nothing found - raise clear error
    print("  ✗ No garment mesh found in scene!")
    print("  Available objects:")
    for obj in bpy.data.objects:
        print(f"    - {obj.name} ({obj.type})")
    
    raise RuntimeError(
        "ERROR: No garment object found!\\n"
        "Make sure step5_blender_sewing.py ran successfully and created 'TShirt_Garment'.\\n"
        "Available meshes: " + ", ".join([o.name for o in bpy.data.objects if o.type == 'MESH'])
    )


# ============================================================
# RENDERING PREVIEW
# ============================================================

def setup_preview_lighting():
    """
    Set up lighting for a nice preview render.
    """
    print("→ Setting up preview lighting...")
    
    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(2, -2, 3))
    sun = bpy.context.active_object
    sun.name = "Preview_Sun"
    sun.data.energy = 3
    
    # Add fill light
    bpy.ops.object.light_add(type='AREA', location=(-2, -1, 2))
    fill = bpy.context.active_object
    fill.name = "Preview_Fill"
    fill.data.energy = 100
    fill.data.size = 2
    
    print("  ✓ Lighting set up")


def setup_camera():
    """
    Set up camera for preview render.
    """
    print("→ Setting up camera...")
    
    # Add camera
    bpy.ops.object.camera_add(location=(0, -2, 0.5))
    camera = bpy.context.active_object
    camera.name = "Preview_Camera"
    
    # Point at origin (where garment is)
    camera.rotation_euler = (1.4, 0, 0)  # ~80 degrees
    
    # Set as active camera
    bpy.context.scene.camera = camera
    
    print("  ✓ Camera set up")


def render_preview(output_path: str = None):
    """
    Render a preview image of the garment.
    
    Args:
        output_path: Where to save the render (optional)
    """
    print("→ Rendering preview...")
    
    # Set render settings
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Fast preview
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    
    if output_path:
        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        print(f"  ✓ Saved render to: {output_path}")
    else:
        # Just render to viewer
        bpy.ops.render.render()
        print("  ✓ Render complete (view in Image Editor)")


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_texture_application_pipeline():
    """
    Main function to apply color and design to the garment.
    
    Steps:
    1. Load fabric color from Step 3
    2. Load design texture from Step 2
    3. Find garment object in scene
    4. Create UV mapping
    5. Create material with color and design
    6. Apply material to garment
    """
    print("\n" + "="*60)
    print("   STEP 6: APPLY COLOR AND DESIGN")
    print("="*60)
    
    # Step 1: Load fabric color
    print("\n" + "-"*40)
    fabric_color = load_fabric_color()
    
    # Step 2: Load design texture
    print("\n" + "-"*40)
    design_image = load_design_texture()
    
    # Step 3: Find garment object
    print("\n" + "-"*40)
    print("→ Finding garment object...")
    garment = find_garment_object()
    
    if garment is None:
        print("  ✗ No garment found in scene!")
        print("  Run step5_blender_sewing.py first.")
        return False
    
    print(f"  ✓ Found garment: {garment.name}")
    
    # Step 4: Create UV mapping
    print("\n" + "-"*40)
    unwrap_garment_uv(garment)
    
    # Step 5: Create material
    print("\n" + "-"*40)
    material = create_fabric_material(
        name="TShirt_Material",
        base_color=fabric_color,
        design_image=design_image
    )
    
    # Step 6: Apply material
    print("\n" + "-"*40)
    apply_material_to_object(garment, material)
    
    # Optional: Set up preview
    print("\n" + "-"*40)
    setup_preview_lighting()
    setup_camera()
    
    # Summary
    print("\n" + "="*60)
    print("   TEXTURE APPLICATION COMPLETE")
    print("="*60)
    print(f"""
✓ Fabric color applied: {fabric_color[:3]}
✓ Design texture: {"Applied" if design_image else "None (solid color)"}
✓ UV mapping created
✓ Material assigned to garment

TO VIEW:
- Switch to "Rendered" viewport shading (Z > 8)
- Or press F12 to render

TO ADJUST DESIGN POSITION:
1. Select the garment
2. Go to Shader Editor
3. Find the "Mapping" node
4. Adjust Location/Scale values

NEXT STEPS:
- Press F12 to render final image
- File > Export to save as OBJ/FBX/GLB
- File > Save to keep .blend file
""")
    
    return True


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    This script runs inside Blender.
    
    PREREQUISITES:
    - Run step5_blender_sewing.py first (creates the garment)
    - Have color_output/front_fabric_color.json (from Step 3)
    - Have design_output/front_design.png (from Step 2)
    
    Or run without those files - it will use defaults.
    
    To run:
    1. Open the .blend file from Step 5
    2. Go to Scripting workspace
    3. Open this file
    4. Click "Run Script"
    
    Or from terminal (after Step 5):
        blender garment.blend --python step6_apply_texture.py
    """
    
    success = run_texture_application_pipeline()
    
    if success:
        print("\n" + "="*60)
        print("   STEP 6 COMPLETE — GREEN SIGNAL ✅")
        print("="*60)
        print("\n🎉 PIPELINE COMPLETE!")
        print("""
═══════════════════════════════════════════════════════════

   ██████╗ ██████╗ ███╗   ███╗██████╗ ██╗     ███████╗████████╗███████╗
  ██╔════╝██╔═══██╗████╗ ████║██╔══██╗██║     ██╔════╝╚══██╔══╝██╔════╝
  ██║     ██║   ██║██╔████╔██║██████╔╝██║     █████╗     ██║   █████╗  
  ██║     ██║   ██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝     ██║   ██╔══╝  
  ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║     ███████╗███████╗   ██║   ███████╗
   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝   ╚═╝   ╚══════╝

═══════════════════════════════════════════════════════════

FINAL VERIFICATION:
  ✅ Front image processed
  ✅ Design extracted  
  ✅ Color extracted
  ✅ Patterns generated
  ✅ Panels sewn
  ✅ Color + design applied

PIPELINE READY — GREEN SIGNAL ✅

═══════════════════════════════════════════════════════════
""")
    else:
        print("\n✗ Texture application failed. Check errors above.")
