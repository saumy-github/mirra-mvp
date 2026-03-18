import bpy
import bmesh
import os
import math
from mathutils import Vector

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

GARMENT_BLEND = os.path.join(INPUT_DIR, "garment.blend")
AVATAR_GLB = os.path.join(INPUT_DIR, "avatar.glb")
OUTPUT_GLB = os.path.join(OUTPUT_DIR, "fitted_garment.glb")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# SIMULATION PARAMETERS
# =========================
SIMULATION_FRAMES = 100  # Frames for cloth draping (not fitting)

print("=" * 60)
print("  GARMENT FITTING & COLLISION SIMULATION")
print("  Geometric Pre-Fit + Cloth Drape")
print("=" * 60)

# =========================
# RESET SCENE
# =========================
bpy.ops.wm.read_factory_settings(use_empty=True)

# =========================
# LOAD GARMENT .blend
# =========================
bpy.ops.wm.open_mainfile(filepath=GARMENT_BLEND)

# Identify garment object
garment = None
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        garment = obj
        break

if garment is None:
    raise RuntimeError("No garment mesh found in garment.blend")

print(f"\n✅ Loaded garment: {garment.name}")
print(f"   Vertices: {len(garment.data.vertices)}")

# =========================
# IMPORT AVATAR
# =========================
bpy.ops.import_scene.gltf(filepath=AVATAR_GLB)

avatar = None
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        avatar = obj
        break

if avatar is None:
    raise RuntimeError("No avatar mesh found in avatar.glb")

print(f"✅ Loaded avatar: {avatar.name}")
print(f"   Vertices: {len(avatar.data.vertices)}")

# =========================
# APPLY TRANSFORMS
# =========================
for obj in [garment, avatar]:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)

bpy.context.view_layer.update()


# =========================
# HELPER FUNCTIONS
# =========================
def get_mesh_bounds(obj):
    """Calculate world-space bounding box for an object."""
    mesh = obj.data
    verts_world = [obj.matrix_world @ v.co for v in mesh.vertices]
    
    if not verts_world:
        return None
    
    min_x = min(v.x for v in verts_world)
    max_x = max(v.x for v in verts_world)
    min_y = min(v.y for v in verts_world)
    max_y = max(v.y for v in verts_world)
    min_z = min(v.z for v in verts_world)
    max_z = max(v.z for v in verts_world)
    
    return {
        'min': Vector((min_x, min_y, min_z)),
        'max': Vector((max_x, max_y, max_z)),
        'center': Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2)),
        'size': Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    }


def get_avatar_torso_center(avatar):
    """Estimate the torso center position on the avatar."""
    bounds = get_mesh_bounds(avatar)
    height = bounds['size'].z
    
    # Torso center is approximately at 65-70% of total height
    torso_z = bounds['min'].z + height * 0.68
    
    return Vector((bounds['center'].x, bounds['center'].y, torso_z))


# =========================
# STEP 1: GEOMETRIC PRE-FIT WITH SHRINKWRAP
# =========================
print("\n" + "=" * 60)
print("STEP 1: GEOMETRIC PRE-FIT (Shrinkwrap)")
print("=" * 60)

# First, position garment roughly at avatar torso
avatar_bounds = get_mesh_bounds(avatar)
garment_bounds = get_mesh_bounds(garment)
torso_center = get_avatar_torso_center(avatar)

print(f"\n📐 Avatar bounds: {avatar_bounds['min']} to {avatar_bounds['max']}")
print(f"📐 Avatar torso center: {torso_center}")
print(f"📐 Garment bounds: {garment_bounds['min']} to {garment_bounds['max']}")

# Calculate initial positioning to place garment at torso
offset_x = torso_center.x - garment_bounds['center'].x
offset_y = torso_center.y - garment_bounds['center'].y

# Position garment top (neckline) near neck level (85% of avatar height)
neck_z = avatar_bounds['min'].z + avatar_bounds['size'].z * 0.85
offset_z = neck_z - garment_bounds['max'].z

garment.location.x += offset_x
garment.location.y += offset_y
garment.location.z += offset_z

# Apply the location
bpy.context.view_layer.objects.active = garment
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
bpy.context.view_layer.update()

print(f"\n✅ Positioned garment with offset: ({offset_x:.4f}, {offset_y:.4f}, {offset_z:.4f})")

# Now apply shrinkwrap to conform garment to avatar surface
bpy.context.view_layer.objects.active = garment
garment.select_set(True)

# Create vertex groups for different wrap intensities
# Neckline/shoulders: less wrapping to preserve shape
# Body/sleeves: full wrapping to conform

mesh = garment.data
garment_bounds = get_mesh_bounds(garment)
garment_height = garment_bounds['size'].z

# Create vertex group for shrinkwrap weighting
vg_shrink = garment.vertex_groups.new(name="ShrinkWeight")

for vert in mesh.vertices:
    world_pos = garment.matrix_world @ vert.co
    
    # Normalize Z position within garment
    z_normalized = (world_pos.z - garment_bounds['min'].z) / garment_height if garment_height > 0 else 0.5
    
    # Top 15%: neckline - less shrinkwrap to preserve opening
    # Bottom 85%: body - more shrinkwrap to conform
    if z_normalized > 0.85:
        # Neckline: minimal shrinkwrap
        weight = 0.2
    elif z_normalized > 0.70:
        # Shoulders: moderate shrinkwrap
        weight = 0.5
    else:
        # Body and sleeves: full shrinkwrap
        weight = 1.0
    
    vg_shrink.add([vert.index], weight, 'REPLACE')

print("✅ Created shrinkwrap weight map")

# Add shrinkwrap modifier
shrinkwrap = garment.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
shrinkwrap.target = avatar
shrinkwrap.wrap_method = 'NEAREST_SURFACEPOINT'
shrinkwrap.wrap_mode = 'OUTSIDE'  # Keep garment outside the body
shrinkwrap.offset = 0.008  # Small offset to prevent z-fighting (8mm)
shrinkwrap.vertex_group = "ShrinkWeight"

print("✅ Added shrinkwrap modifier")

# Apply the shrinkwrap to bake the fit permanently
bpy.ops.object.modifier_apply(modifier="Shrinkwrap")
bpy.context.view_layer.update()

print("✅ Applied shrinkwrap - garment is now geometrically fitted")


# =========================
# STEP 2: FIT VALIDATION
# =========================
print("\n" + "=" * 60)
print("STEP 2: FIT VALIDATION")
print("=" * 60)

def validate_fit(garment, avatar):
    """Validate that the garment is correctly positioned on the avatar."""
    bpy.context.view_layer.update()
    
    garment_bounds = get_mesh_bounds(garment)
    avatar_bounds = get_mesh_bounds(avatar)
    
    issues = []
    
    # Check 1: Garment center should be near avatar torso
    avatar_torso_z = avatar_bounds['min'].z + avatar_bounds['size'].z * 0.68
    garment_center_z = garment_bounds['center'].z
    
    z_diff = abs(garment_center_z - avatar_torso_z)
    if z_diff > avatar_bounds['size'].z * 0.15:
        issues.append(f"Garment center too far from torso (diff: {z_diff:.4f})")
    else:
        print(f"   ✓ Garment center aligned with torso (diff: {z_diff:.4f})")
    
    # Check 2: Neckline should be near neck level
    neck_z = avatar_bounds['min'].z + avatar_bounds['size'].z * 0.85
    neckline_z = garment_bounds['max'].z
    
    neck_diff = abs(neckline_z - neck_z)
    if neck_diff > avatar_bounds['size'].z * 0.10:
        issues.append(f"Neckline not at neck level (diff: {neck_diff:.4f})")
    else:
        print(f"   ✓ Neckline at neck level (diff: {neck_diff:.4f})")
    
    # Check 3: Garment should overlap avatar horizontally
    overlap_x = min(garment_bounds['max'].x, avatar_bounds['max'].x) - max(garment_bounds['min'].x, avatar_bounds['min'].x)
    if overlap_x < avatar_bounds['size'].x * 0.5:
        issues.append(f"Insufficient horizontal overlap")
    else:
        print(f"   ✓ Good horizontal overlap ({overlap_x:.4f})")
    
    # Check 4: Garment should not have fallen below waist
    waist_z = avatar_bounds['min'].z + avatar_bounds['size'].z * 0.50
    if garment_bounds['min'].z < waist_z - 0.05:
        print(f"   ⚠ Garment extends below waist (expected for T-shirt)")
    else:
        print(f"   ✓ Garment hem at appropriate level")
    
    if issues:
        print("\n⚠️ FIT VALIDATION WARNINGS:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\n✅ All fit checks passed!")
    
    return len(issues) == 0

fit_valid = validate_fit(garment, avatar)


# =========================
# STEP 3: CLOTH SIMULATION FOR DRAPE
# =========================
print("\n" + "=" * 60)
print("STEP 3: CLOTH SIMULATION (Drape Only)")
print("=" * 60)
print("Note: Garment is already fitted. Physics adds natural drape.")

# Add collision to avatar
collision = avatar.modifiers.new(name="Collision", type='COLLISION')
csettings = collision.settings
csettings.thickness_outer = 0.004
csettings.thickness_inner = 0.004
csettings.damping = 0.3
csettings.use_culling = True

print("✅ Added collision modifier to avatar")

# Add cloth to garment
bpy.context.view_layer.objects.active = garment
cloth = garment.modifiers.new(name="Cloth", type='CLOTH')

settings = cloth.settings
settings.quality = 8
settings.mass = 0.18  # Light cotton T-shirt
settings.tension_stiffness = 10.0  # Fairly stiff fabric
settings.compression_stiffness = 10.0
settings.shear_stiffness = 6.0
settings.bending_stiffness = 0.1
settings.tension_damping = 5.0
settings.compression_damping = 5.0
settings.shear_damping = 5.0
settings.bending_damping = 0.5
settings.air_damping = 1.0  # Helps stabilize

# Self collision
cloth.collision_settings.use_self_collision = True
cloth.collision_settings.self_friction = 3.0
cloth.collision_settings.self_distance_min = 0.003

# Create pin group for neckline to prevent sliding
vg_pins = garment.vertex_groups.new(name="ClothPins")
mesh = garment.data
garment_bounds = get_mesh_bounds(garment)

pinned_count = 0
for vert in mesh.vertices:
    world_pos = garment.matrix_world @ vert.co
    z_normalized = (world_pos.z - garment_bounds['min'].z) / garment_bounds['size'].z if garment_bounds['size'].z > 0 else 0
    
    # Pin only the very top edge (neckline) to prevent sliding
    if z_normalized > 0.95:
        vg_pins.add([vert.index], 1.0, 'REPLACE')
        pinned_count += 1

settings.vertex_group_mass = "ClothPins"
settings.pin_stiffness = 5.0  # Moderate pinning

print(f"✅ Added cloth modifier with {pinned_count} pinned vertices at neckline")

# Scene physics settings
scene = bpy.context.scene
scene.use_gravity = True
scene.gravity = (0, 0, -9.81)
scene.frame_start = 1
scene.frame_end = SIMULATION_FRAMES

print(f"📽️ Simulation frames: 1 to {SIMULATION_FRAMES}")


# =========================
# STEP 4: BAKE SIMULATION
# =========================
print("\n" + "=" * 60)
print("STEP 4: BAKE SIMULATION")
print("=" * 60)

print("⏳ Baking cloth simulation...")
bpy.context.view_layer.objects.active = garment
bpy.ops.ptcache.free_bake_all()
bpy.ops.ptcache.bake_all(bake=True)
print("✅ Simulation baked")

# Go to final frame and apply
scene.frame_set(SIMULATION_FRAMES)
bpy.ops.object.modifier_apply(modifier="Cloth")
print(f"✅ Applied cloth at frame {SIMULATION_FRAMES}")


# =========================
# STEP 5: FINAL VALIDATION
# =========================
print("\n" + "=" * 60)
print("STEP 5: FINAL VALIDATION")
print("=" * 60)

final_garment_bounds = get_mesh_bounds(garment)
final_avatar_bounds = get_mesh_bounds(avatar)

print(f"📐 Final garment bounds:")
print(f"   Z range: [{final_garment_bounds['min'].z:.4f}, {final_garment_bounds['max'].z:.4f}]")
print(f"   Center: {final_garment_bounds['center']}")

# Check garment hasn't fallen off
torso_z = final_avatar_bounds['min'].z + final_avatar_bounds['size'].z * 0.68
if abs(final_garment_bounds['center'].z - torso_z) < final_avatar_bounds['size'].z * 0.2:
    print("✅ Garment remains fitted on torso")
else:
    print("⚠️ Garment may have shifted during simulation")


# =========================
# STEP 6: EXPORT
# =========================
print("\n" + "=" * 60)
print("STEP 6: EXPORT")
print("=" * 60)

# Deselect all, select only garment
bpy.ops.object.select_all(action='DESELECT')
garment.select_set(True)
bpy.context.view_layer.objects.active = garment

# Clean up vertex groups (optional, keeps mesh clean)
for vg in list(garment.vertex_groups):
    garment.vertex_groups.remove(vg)

bpy.ops.export_scene.gltf(
    filepath=OUTPUT_GLB,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT'
)

print(f"✅ Exported fitted garment to: {OUTPUT_GLB}")

print("\n" + "=" * 60)
print("  ✅ GARMENT FITTING COMPLETE")
print("=" * 60)
print(f"📦 Output: {OUTPUT_GLB}")
print("=" * 60)