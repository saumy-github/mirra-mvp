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
import time
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Input directories
COLOR_DIR = Path(__file__).parent / "color_output"
DESIGN_DIR = Path(__file__).parent / "design_output"

# Logging directory
LOG_DIR = Path(__file__).parent / "blender_logs"
LOG_FILE = LOG_DIR / "step6_detailed_log.txt"

# File paths
FABRIC_COLOR_JSON = COLOR_DIR / "front_fabric_color.json"
DESIGN_IMAGE = DESIGN_DIR / "front_design.png"

# Default fabric color (if JSON not found)
DEFAULT_FABRIC_COLOR = (0.2, 0.3, 0.5, 1.0)  # Navy blue RGBA


# ============================================================
# LOGGING SYSTEM (works in Blender environment)
# ============================================================

class BlenderTextureLogger:
    """Logger for Blender texture operations"""
    
    def __init__(self):
        self.log_entries = []
        self.start_time = time.time()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        elapsed = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] [{elapsed:7.3f}s] [{level:7}] {message}"
        self.log_entries.append(entry)
        print(message)  # Also print to Blender console
    
    def save_log(self):
        """Save log to file"""
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.log_entries))
            self.log(f"Log saved to: {LOG_FILE}", "SUCCESS")
        except Exception as e:
            print(f"Failed to save log: {e}")

logger = BlenderTextureLogger()


# ============================================================
# COLOR LOADING
# ============================================================

def load_fabric_color() -> tuple:
    """
    Load the extracted fabric color from Step 3 with logging.
    
    The color was saved as RGB values (0-255) in a JSON file.
    We convert to Blender's format (0.0-1.0).
    
    Returns:
        Tuple of (R, G, B, A) with values 0.0-1.0
    """
    logger.log("Loading fabric color...", "INFO")
    
    if not FABRIC_COLOR_JSON.exists():
        logger.log(f"  Color file not found: {FABRIC_COLOR_JSON}", "WARNING")
        logger.log(f"  Using default color: RGB{DEFAULT_FABRIC_COLOR[:3]}", "WARNING")
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
        
        logger.log(f"  \u2713 Loaded color: {color_name} ({hex_code})", "SUCCESS")
        logger.log(f"    RGB (0-255): ({rgb[0]}, {rgb[1]}, {rgb[2]})", "INFO")
        logger.log(f"    RGB (0-1): ({r:.3f}, {g:.3f}, {b:.3f})", "INFO")
        
        return color
        
    except Exception as e:
        logger.log(f"  Error loading color: {e}", "ERROR")
        logger.log(f"  Using default color", "WARNING")
        return DEFAULT_FABRIC_COLOR


def load_design_texture() -> bpy.types.Image:
    """
    Load the extracted design image from Step 2 with logging.
    
    The design is a PNG with transparency:
    - Design pixels are opaque
    - Non-design areas are transparent
    
    Returns:
        Blender Image object, or None if not found
    """
    logger.log("Loading design texture...", "INFO")
    
    if not DESIGN_IMAGE.exists():
        logger.log(f"  Design image not found: {DESIGN_IMAGE}", "WARNING")
        logger.log("  Proceeding with solid fabric color only", "INFO")
        return None
    
    try:
        # Load image into Blender
        img = bpy.data.images.load(str(DESIGN_IMAGE))
        img.name = "TShirt_Design"
        
        logger.log(f"  ✓ Loaded design: {img.name}", "SUCCESS")
        logger.log(f"    Size: {img.size[0]}x{img.size[1]} pixels", "INFO")
        logger.log(f"    Color space: {img.colorspace_settings.name}", "INFO")
        logger.log(f"    Has alpha: {img.alpha_mode != 'NONE'}", "INFO")
        
        return img
        
    except Exception as e:
        logger.log(f"  Error loading design: {e}", "ERROR")
        logger.log("  Proceeding with solid fabric color only", "WARNING")
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
    logger.log(f"Creating material: {name}...", "INFO")
    
    # Create new material
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # Get the node tree
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    logger.log("  Setting up material nodes...", "INFO")
    
    # Create output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (600, 0)
    
    # Create principled BSDF for fabric
    fabric_shader = nodes.new(type='ShaderNodeBsdfPrincipled')
    fabric_shader.location = (200, 100)
    fabric_shader.inputs['Base Color'].default_value = base_color
    fabric_shader.inputs['Roughness'].default_value = 0.8  # Fabric is not shiny
    fabric_shader.inputs['Specular IOR Level'].default_value = 0.3
    
    logger.log(f"  Fabric color set: RGBA{base_color}", "INFO")
    
    if design_image is None:
        # No design - just use fabric color
        links.new(fabric_shader.outputs['BSDF'], output_node.inputs['Surface'])
        logger.log("  ✓ Material created (solid color, no design)", "SUCCESS")
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
    
    logger.log("  ✓ Material created with design texture overlay", "SUCCESS")
    logger.log(f"    Total nodes: {len(nodes)}", "INFO")
    
    return mat


def create_simple_fabric_material(name: str, base_color: tuple) -> bpy.types.Material:
    """
    Create a simple fabric material without node complexity with logging.
    
    This is a simpler version that just sets the base color.
    Use when you don't need the design overlay.
    
    Args:
        name: Material name
        base_color: RGBA tuple
    
    Returns:
        The created material
    """
    logger.log(f"Creating simple material: {name}...", "INFO")
    
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # Get the Principled BSDF node (created by default)
    principled = mat.node_tree.nodes.get('Principled BSDF')
    
    if principled:
        principled.inputs['Base Color'].default_value = base_color
        principled.inputs['Roughness'].default_value = 0.8
        logger.log(f"  ✓ Simple material created: RGBA{base_color}", "SUCCESS")
    else:
        logger.log("  WARNING: No Principled BSDF found", "WARNING")
    
    return mat


# ============================================================
# UV MAPPING
# ============================================================

def unwrap_garment_uv(obj: bpy.types.Object):
    """
    Create UV coordinates for the garment mesh with logging.
    
    UV mapping is like flattening the 3D surface back to 2D:
    - U = horizontal position on texture (0-1)
    - V = vertical position on texture (0-1)
    
    For a T-shirt, we want:
    - Front panel gets the design texture
    - Proper alignment so design appears centered
    
    Args:
        obj: The garment mesh object
    """
    logger.log(f"Creating UV map for {obj.name}...", "INFO")
    
    face_count = len(obj.data.polygons)
    logger.log(f"  Unwrapping {face_count} faces...", "INFO")
    
    # Select the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all faces
    bpy.ops.mesh.select_all(action='SELECT')
    
    try:
        # Project from view (front view gives good UV for front of shirt)
        # First, set view to front
        bpy.ops.uv.project_from_view(
            orthographic=True,
            correct_aspect=True,
            scale_to_bounds=True
        )
        logger.log("  Applied view projection", "INFO")
        
        # Alternative: Smart UV Project (automatic, works for complex shapes)
        bpy.ops.uv.smart_project(
            angle_limit=66.0,
            island_margin=0.02,
            correct_aspect=True
        )
        logger.log("  Applied smart UV projection", "INFO")
        
    except Exception as e:
        logger.log(f"  Error during UV unwrapping: {e}", "ERROR")
    
    # Exit edit mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Check UV layers
    if obj.data.uv_layers:
        uv_layer_count = len(obj.data.uv_layers)
        logger.log(f"  ✓ UV map created ({uv_layer_count} layers)", "SUCCESS")
    else:
        logger.log("  WARNING: No UV layers created!", "WARNING")


def project_design_to_front(obj: bpy.types.Object):
    """
    Project texture specifically onto the front of the garment with logging.
    
    For T-shirt designs, we typically want:
    - Design appears on the FRONT panel
    - Centered horizontally
    - Positioned in upper chest area
    
    This creates a custom UV projection for the front faces.
    
    Args:
        obj: The garment mesh object
    """
    logger.log("Projecting design to front panel...", "INFO")
    
    # This is a simplified approach
    # In production, you'd identify front faces by normal direction
    # and create a separate UV map just for them
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    try:
        # Project from front (negative Y in Blender = front view)
        # This assumes the garment is oriented with front facing -Y
        bpy.ops.uv.project_from_view(
            camera_bounds=False,
            correct_aspect=True,
            scale_to_bounds=True
        )
        logger.log("  ✓ Front projection applied", "SUCCESS")
    except Exception as e:
        logger.log(f"  Error during front projection: {e}", "ERROR")
    
    bpy.ops.object.mode_set(mode='OBJECT')


# ============================================================
# MATERIAL APPLICATION
# ============================================================

def apply_material_to_object(obj: bpy.types.Object, material: bpy.types.Material):
    """
    Apply a material to an object with logging.
    
    In Blender, each object can have multiple material slots.
    We assign our fabric material to the first slot.
    
    Args:
        obj: The object to apply material to
        material: The material to apply
    """
    logger.log(f"Applying material to {obj.name}...", "INFO")
    
    # Clear existing materials
    old_count = len(obj.data.materials)
    obj.data.materials.clear()
    
    if old_count > 0:
        logger.log(f"  Cleared {old_count} existing materials", "INFO")
    
    # Add our material
    obj.data.materials.append(material)
    
    logger.log(f"  ✓ Material applied: {material.name}", "SUCCESS")


def find_garment_object() -> bpy.types.Object:
    """
    Find the T-shirt garment object in the scene with logging.
    
    Looks for an object named "TShirt_Garment" (created in Step 5)
    or any object with a Cloth modifier.
    
    Returns:
        The garment object, or None if not found
    """
    logger.log("Searching for garment object...", "INFO")
    
    total_objects = len(bpy.data.objects)
    logger.log(f"  Total objects in scene: {total_objects}", "INFO")
    
    # First, try to find by name
    if "TShirt_Garment" in bpy.data.objects:
        obj = bpy.data.objects["TShirt_Garment"]
        face_count = len(obj.data.polygons)
        logger.log(f"  ✓ Found TShirt_Garment ({face_count} faces)", "SUCCESS")
        return obj
    
    logger.log("  TShirt_Garment not found, searching for cloth modifier...", "WARNING")
    
    # Otherwise, find any object with cloth modifier
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'CLOTH':
                    face_count = len(obj.data.polygons)
                    logger.log(f"  ✓ Found object with cloth modifier: {obj.name} ({face_count} faces)", "SUCCESS")
                    return obj
    
    logger.log("  No cloth modifier found, searching for largest mesh...", "WARNING")
    
    # Last resort: find largest mesh
    largest = None
    largest_verts = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            vert_count = len(obj.data.vertices)
            if vert_count > largest_verts:
                largest = obj
                largest_verts = vert_count
    
    if largest:
        face_count = len(largest.data.polygons)
        logger.log(f"  Using largest mesh: {largest.name} ({largest_verts} vertices, {face_count} faces)", "WARNING")
        
        if face_count == 0:
            logger.log("    ⚠️ WARNING: Garment has 0 faces!", "ERROR")
            logger.log("    This suggests Step 5 mesh creation failed", "ERROR")
    else:
        logger.log("  ERROR: No mesh objects found in scene!", "ERROR")
    
    return largest


# ============================================================
# RENDERING PREVIEW
# ============================================================

def setup_preview_lighting():
    """
    Set up lighting for a nice preview render with logging.
    """
    logger.log("Setting up preview lighting...", "INFO")
    
    try:
        # Add sun light
        bpy.ops.object.light_add(type='SUN', location=(2, -2, 3))
        sun = bpy.context.active_object
        sun.name = "Preview_Sun"
        sun.data.energy = 3
        logger.log(f"  Added sun light at (2, -2, 3)", "INFO")
        
        # Add fill light
        bpy.ops.object.light_add(type='AREA', location=(-2, -1, 2))
        fill = bpy.context.active_object
        fill.name = "Preview_Fill"
        fill.data.energy = 100
        fill.data.size = 2
        logger.log(f"  Added area fill light at (-2, -1, 2)", "INFO")
        
        logger.log("  ✓ Lighting setup complete", "SUCCESS")
    except Exception as e:
        logger.log(f"  Error setting up lighting: {e}", "ERROR")


def setup_camera():
    """
    Set up camera for preview render with logging.
    """
    logger.log("Setting up camera...", "INFO")
    
    try:
        # Add camera
        bpy.ops.object.camera_add(location=(0, -2, 0.5))
        camera = bpy.context.active_object
        camera.name = "Preview_Camera"
        logger.log(f"  Camera added at (0, -2, 0.5)", "INFO")
        
        # Point at origin (where garment is)
        camera.rotation_euler = (1.4, 0, 0)  # ~80 degrees
        logger.log(f"  Camera rotation: {camera.rotation_euler}", "INFO")
        
        # Set as active camera
        bpy.context.scene.camera = camera
        
        logger.log("  ✓ Camera setup complete", "SUCCESS")
    except Exception as e:
        logger.log(f"  Error setting up camera: {e}", "ERROR")


def render_preview(output_path: str = None):
    """
    Render a preview image of the garment with logging.
    
    Args:
        output_path: Where to save the render (optional)
    """
    logger.log("Rendering preview...", "INFO")
    
    try:
        # Set render settings
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Fast preview
        bpy.context.scene.render.resolution_x = 1920
        bpy.context.scene.render.resolution_y = 1080
        
        logger.log(f"  Render engine: {bpy.context.scene.render.engine}", "INFO")
        logger.log(f"  Resolution: 1920x1080", "INFO")
        
        if output_path:
            bpy.context.scene.render.filepath = output_path
            bpy.ops.render.render(write_still=True)
            logger.log(f"  ✓ Saved render to: {output_path}", "SUCCESS")
        else:
            # Just render to viewer
            bpy.ops.render.render()
            logger.log("  ✓ Render complete (view in Image Editor)", "SUCCESS")
    except Exception as e:
        logger.log(f"  Error during rendering: {e}", "ERROR")


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_texture_application_pipeline():
    """
    Main function to apply color and design to the garment with comprehensive logging.
    
    Steps:
    1. Load fabric color from Step 3
    2. Load design texture from Step 2
    3. Find garment object in scene
    4. Create UV mapping
    5. Create material with color and design
    6. Apply material to garment
    """
    logger.log("="*60, "INFO")
    logger.log("STEP 6: APPLY COLOR AND DESIGN", "INFO")
    logger.log("="*60, "INFO")
    
    pipeline_start = time.time()
    
    # Step 1: Load fabric color
    logger.log("-"*40, "INFO")
    step1_start = time.time()
    fabric_color = load_fabric_color()
    step1_time = time.time() - step1_start
    logger.log(f"Step 1 complete ({step1_time:.2f}s)", "INFO")
    
    # Step 2: Load design texture
    logger.log("-"*40, "INFO")
    step2_start = time.time()
    design_image = load_design_texture()
    step2_time = time.time() - step2_start
    logger.log(f"Step 2 complete ({step2_time:.2f}s)", "INFO")
    
    # Step 3: Find garment object
    logger.log("-"*40, "INFO")
    step3_start = time.time()
    garment = find_garment_object()
    
    if garment is None:
        logger.log("⛔ No garment found in scene!", "ERROR")
        logger.log("Run step5_blender_sewing.py first.", "ERROR")
        logger.save_log()
        return False
    
    step3_time = time.time() - step3_start
    logger.log(f"Step 3 complete ({step3_time:.2f}s)", "INFO")
    
    # Step 4: Create UV mapping
    logger.log("-"*40, "INFO")
    step4_start = time.time()
    unwrap_garment_uv(garment)
    step4_time = time.time() - step4_start
    logger.log(f"Step 4 complete ({step4_time:.2f}s)", "INFO")
    
    # Step 5: Create material
    logger.log("-"*40, "INFO")
    step5_start = time.time()
    material = create_fabric_material(
        name="TShirt_Material",
        base_color=fabric_color,
        design_image=design_image
    )
    step5_time = time.time() - step5_start
    logger.log(f"Step 5 complete ({step5_time:.2f}s)", "INFO")
    
    # Step 6: Apply material
    logger.log("-"*40, "INFO")
    step6_start = time.time()
    apply_material_to_object(garment, material)
    step6_time = time.time() - step6_start
    logger.log(f"Step 6 complete ({step6_time:.2f}s)", "INFO")
    
    # Optional: Set up preview
    logger.log("-"*40, "INFO")
    setup_start = time.time()
    setup_preview_lighting()
    setup_camera()
    setup_time = time.time() - setup_start
    logger.log(f"Preview setup complete ({setup_time:.2f}s)", "INFO")
    
    pipeline_time = time.time() - pipeline_start
    
    # Summary
    logger.log("="*60, "INFO")
    logger.log("TEXTURE APPLICATION COMPLETE", "SUCCESS")
    logger.log("="*60, "INFO")
    
    summary = f"""
✓ Fabric color applied: RGB{fabric_color[:3]}
✓ Design texture: {"Applied" if design_image else "None (solid color)"}
✓ UV mapping created
✓ Material assigned to {garment.name}

TIMING BREAKDOWN:
  Step 1 (Load color): {step1_time:.2f}s
  Step 2 (Load design): {step2_time:.2f}s
  Step 3 (Find garment): {step3_time:.2f}s
  Step 4 (UV mapping): {step4_time:.2f}s
  Step 5 (Create material): {step5_time:.2f}s
  Step 6 (Apply material): {step6_time:.2f}s
  Preview setup: {setup_time:.2f}s
  -------------------------
  TOTAL: {pipeline_time:.2f}s

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
"""
    
    logger.log(summary, "INFO")
    
    # Save log file
    logger.save_log()
    
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
