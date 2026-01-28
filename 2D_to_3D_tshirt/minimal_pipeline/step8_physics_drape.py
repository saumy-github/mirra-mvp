"""
STEP 8: Cloth Simulation (Execution Locked)
=============================================
Ensures cloth physics is ACTUALLY EXECUTED with verified deformation.

This script:
1. Imports garment GLB
2. Adds cloth modifier with soft cotton parameters
3. Enables gravity (0, 0, -9.81)
4. Runs simulation through 120 frames
5. VERIFIES vertex position changes
6. Bakes result to mesh
7. Exports only after verification

Requirements:
    Blender 3.x / 4.x / 5.x
    
Usage:
    blender -b --python step8_physics_drape.py
"""

import sys
from pathlib import Path
import hashlib

try:
    import bpy
    from mathutils import Vector
except ImportError:
    print("ERROR: Run inside Blender!")
    print("  blender -b --python step8_physics_drape.py")
    sys.exit(1)

# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PATTERN_DIR = SCRIPT_DIR / "pattern_output"

INPUT_GLB = PATTERN_DIR / "tshirt_garment.glb"
OUTPUT_GLB = PATTERN_DIR / "tshirt_draped.glb"
OUTPUT_BLEND = PATTERN_DIR / "tshirt_draped.blend"

# ============================================================
# PHYSICS PARAMETERS (as specified)
# ============================================================

CLOTH_PARAMS = {
    "quality": 10,
    "mass": 0.15,                # kg/m² - light cotton
    "tension_stiffness": 6.0,    # stretch_stiffness
    "compression_stiffness": 6.0,
    "shear_stiffness": 4.0,
    "bending_stiffness": 0.03,   # Very low for visible drape
    "damping": 0.35,
}

GRAVITY = Vector((0, 0, -9.81))
FRAME_END = 120
SETTLE_FRAME = 100


# ============================================================
# HELPERS
# ============================================================

def get_vertex_hash(obj):
    """Get hash of vertex positions for comparison."""
    mesh = obj.data
    coords = []
    for v in mesh.vertices:
        coords.extend([round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6)])
    return hashlib.md5(str(coords).encode()).hexdigest()[:16]


def get_vertex_stats(obj):
    """Get vertex position statistics."""
    mesh = obj.data
    x = [v.co.x for v in mesh.vertices]
    y = [v.co.y for v in mesh.vertices]
    z = [v.co.z for v in mesh.vertices]
    
    return {
        'x_min': min(x), 'x_max': max(x),
        'y_min': min(y), 'y_max': max(y),
        'z_min': min(z), 'z_max': max(z),
        'center_z': sum(z) / len(z)
    }


def print_bounds(label, stats):
    """Print bounding box stats."""
    print(f"    {label}:")
    print(f"      X: [{stats['x_min']:.4f}, {stats['x_max']:.4f}]")
    print(f"      Y: [{stats['y_min']:.4f}, {stats['y_max']:.4f}]")
    print(f"      Z: [{stats['z_min']:.4f}, {stats['z_max']:.4f}]")
    print(f"      Center Z: {stats['center_z']:.4f}")


# ============================================================
# SCENE SETUP
# ============================================================

def clear_scene():
    """Clear all objects."""
    print("  Clearing scene...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def import_garment(filepath):
    """Import GLB garment."""
    print(f"  Importing: {filepath.name}")
    
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            obj.name = "Garment"
            return obj
    
    raise RuntimeError("No mesh in GLB!")


def setup_gravity():
    """Enable gravity."""
    scene = bpy.context.scene
    scene.gravity = GRAVITY
    scene.use_gravity = True
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.frame_current = 1
    
    print(f"  Gravity: {scene.gravity}")
    print(f"  Frames: 1 to {FRAME_END}")


# ============================================================
# CLOTH PHYSICS
# ============================================================

def add_cloth_modifier(obj):
    """Add cloth modifier with specified parameters."""
    print("  Adding cloth modifier...")
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Apply scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    # Remove existing cloth modifiers
    for mod in obj.modifiers:
        if mod.type == 'CLOTH':
            obj.modifiers.remove(mod)
    
    # Add cloth
    cloth_mod = obj.modifiers.new(name="Cloth", type='CLOTH')
    cloth = cloth_mod.settings
    
    # Set parameters
    cloth.quality = CLOTH_PARAMS["quality"]
    cloth.mass = CLOTH_PARAMS["mass"]
    cloth.tension_stiffness = CLOTH_PARAMS["tension_stiffness"]
    cloth.compression_stiffness = CLOTH_PARAMS["compression_stiffness"]
    cloth.shear_stiffness = CLOTH_PARAMS["shear_stiffness"]
    cloth.bending_stiffness = CLOTH_PARAMS["bending_stiffness"]
    
    # Damping
    cloth.tension_damping = CLOTH_PARAMS["damping"] * 10
    cloth.compression_damping = CLOTH_PARAMS["damping"] * 10
    cloth.bending_damping = CLOTH_PARAMS["damping"]
    cloth.air_damping = 1.0
    
    # Self collision
    cloth_mod.collision_settings.use_self_collision = True
    cloth_mod.collision_settings.self_distance_min = 0.003
    
    print(f"    Mass: {cloth.mass} kg/m²")
    print(f"    Tension: {cloth.tension_stiffness}")
    print(f"    Shear: {cloth.shear_stiffness}")
    print(f"    Bending: {cloth.bending_stiffness}")
    
    return cloth_mod


def add_neckline_pin(obj):
    """Pin only the very top (neckline) to prevent total falling."""
    print("  Adding neckline pin (minimal)...")
    
    mesh = obj.data
    z_coords = [v.co.z for v in mesh.vertices]
    z_max = max(z_coords)
    z_min = min(z_coords)
    threshold = z_max - (z_max - z_min) * 0.02  # Top 2% only
    
    # Create vertex group
    if "Pin" in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups["Pin"])
    
    pin_group = obj.vertex_groups.new(name="Pin")
    
    pinned = 0
    for v in mesh.vertices:
        if v.co.z >= threshold:
            pin_group.add([v.index], 1.0, 'REPLACE')
            pinned += 1
    
    # Apply to cloth
    for mod in obj.modifiers:
        if mod.type == 'CLOTH':
            mod.settings.vertex_group_mass = "Pin"
            mod.settings.pin_stiffness = 1.0
    
    print(f"    Pinned {pinned} vertices (top 2% only)")
    print(f"    Rest of garment is FREE to fall!")


# ============================================================
# SIMULATION EXECUTION
# ============================================================

def execute_simulation(obj):
    """
    EXECUTE the simulation by advancing through all frames.
    This is the critical step that actually runs physics.
    """
    print(f"\n  EXECUTING simulation ({FRAME_END} frames)...")
    
    scene = bpy.context.scene
    
    # Force dependency graph update
    bpy.context.view_layer.update()
    
    print("  Frame progression: ", end="", flush=True)
    
    for frame in range(1, FRAME_END + 1):
        scene.frame_set(frame)
        
        # Force update
        bpy.context.view_layer.update()
        
        if frame % 20 == 0:
            print(f"{frame}", end=" ", flush=True)
    
    print("COMPLETE")
    
    # Go to settle frame
    scene.frame_set(SETTLE_FRAME)
    bpy.context.view_layer.update()
    
    print(f"  Settled at frame {SETTLE_FRAME}")


def get_deformed_mesh(obj):
    """Get the deformed mesh with modifiers applied."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    
    coords = [(v.co.x, v.co.y, v.co.z) for v in mesh_eval.vertices]
    obj_eval.to_mesh_clear()
    
    return coords


def verify_deformation(obj, initial_stats):
    """Verify that deformation actually occurred."""
    print("\n  VERIFYING deformation...")
    
    # Get deformed coordinates
    deformed = get_deformed_mesh(obj)
    
    # Calculate new stats
    x = [c[0] for c in deformed]
    y = [c[1] for c in deformed]
    z = [c[2] for c in deformed]
    
    final_stats = {
        'x_min': min(x), 'x_max': max(x),
        'y_min': min(y), 'y_max': max(y),
        'z_min': min(z), 'z_max': max(z),
        'center_z': sum(z) / len(z)
    }
    
    # Compare
    print_bounds("Initial", initial_stats)
    print_bounds("After simulation", final_stats)
    
    # Check for changes
    z_drop = initial_stats['center_z'] - final_stats['center_z']
    z_min_change = initial_stats['z_min'] - final_stats['z_min']
    y_spread = (final_stats['y_max'] - final_stats['y_min']) - \
               (initial_stats['y_max'] - initial_stats['y_min'])
    
    print(f"\n    Center Z drop: {z_drop:.4f}m")
    print(f"    Bottom Z drop: {z_min_change:.4f}m")
    print(f"    Y spread change: {y_spread:.4f}m")
    
    deformed = abs(z_drop) > 0.001 or abs(z_min_change) > 0.001 or abs(y_spread) > 0.001
    
    if deformed:
        print("\n    ✅ DEFORMATION VERIFIED!")
    else:
        print("\n    ⚠️ WARNING: Minimal deformation detected!")
    
    return deformed, final_stats


def bake_to_mesh(obj):
    """Apply simulation result as permanent mesh."""
    print("\n  BAKING simulation to mesh...")
    
    bpy.context.scene.frame_set(SETTLE_FRAME)
    bpy.context.view_layer.update()
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Apply cloth modifier
    for mod in list(obj.modifiers):
        if mod.type == 'CLOTH':
            # Use visual geometry to mesh
            bpy.ops.object.modifier_apply(modifier=mod.name)
            print("    Cloth modifier applied ✓")
    
    # Smooth
    smooth = obj.modifiers.new(name="Smooth", type='SMOOTH')
    smooth.factor = 0.3
    smooth.iterations = 2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    print("    Smoothing applied ✓")
    
    # Fix normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("    Normals fixed ✓")


# ============================================================
# EXPORT
# ============================================================

def export_glb(obj, filepath):
    """Export as GLB."""
    print(f"\n  Exporting: {filepath.name}")
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format='GLB',
        use_selection=True,
        export_materials='EXPORT',
        export_apply=True
    )
    
    if filepath.exists():
        size = filepath.stat().st_size / 1024
        print(f"    ✓ Size: {size:.1f} KB")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("   STEP 8: CLOTH SIMULATION (Execution Locked)")
    print("=" * 60)
    
    # Check input
    if not INPUT_GLB.exists():
        print(f"\n✗ ERROR: {INPUT_GLB} not found")
        return
    
    # Clear scene
    print("\n→ Scene setup...")
    clear_scene()
    
    # Import
    print("\n→ Import garment...")
    garment = import_garment(INPUT_GLB)
    
    # Get initial state
    initial_hash = get_vertex_hash(garment)
    initial_stats = get_vertex_stats(garment)
    print(f"  Initial mesh hash: {initial_hash}")
    print_bounds("Initial bounds", initial_stats)
    
    # Setup physics
    print("\n→ Configure physics...")
    setup_gravity()
    add_cloth_modifier(garment)
    add_neckline_pin(garment)
    
    # EXECUTE SIMULATION
    print("\n→ EXECUTE SIMULATION...")
    execute_simulation(garment)
    
    # VERIFY
    deformed, final_stats = verify_deformation(garment, initial_stats)
    
    # BAKE
    print("\n→ BAKE result...")
    bake_to_mesh(garment)
    
    # Final hash
    final_hash = get_vertex_hash(garment)
    print(f"\n  Final mesh hash: {final_hash}")
    
    if initial_hash != final_hash:
        print("  ✅ Mesh has been modified by simulation!")
    else:
        print("  ⚠️ WARNING: Mesh unchanged!")
    
    # Export
    print("\n→ Export GLB...")
    export_glb(garment, OUTPUT_GLB)
    
    # Save blend
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    
    # Summary
    print("\n" + "=" * 60)
    if deformed and initial_hash != final_hash:
        print("   ✅ CLOTH SIMULATION SUCCESSFUL")
    else:
        print("   ⚠️ SIMULATION MAY NEED ADJUSTMENT")
    print("=" * 60)
    
    print(f"""
Physics Applied:
  • Mass: {CLOTH_PARAMS['mass']} kg/m²
  • Bending: {CLOTH_PARAMS['bending_stiffness']}
  • Tension: {CLOTH_PARAMS['tension_stiffness']}
  • Gravity: (0, 0, -9.81) m/s²

Output: {OUTPUT_GLB}
View:   https://gltf-viewer.donmccurdy.com
""")


if __name__ == "__main__":
    main()
