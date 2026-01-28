import bpy
import os

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

# =========================
# APPLY SCALE (CRITICAL)
# =========================
for obj in [garment, avatar]:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# =========================
# ADD COLLISION TO AVATAR
# =========================
collision = avatar.modifiers.new(name="Collision", type='COLLISION')

csettings = collision.settings
csettings.thickness_outer = 0.005
csettings.thickness_inner = 0.005
csettings.damping = 0.2

# =========================
# ADD CLOTH TO GARMENT (IF NEEDED)
# =========================
cloth = garment.modifiers.get("Cloth")
if cloth is None:
    cloth = garment.modifiers.new(name="Cloth", type='CLOTH')

settings = cloth.settings
settings.quality = 8
settings.mass = 0.15
settings.tension_stiffness = 6.0
settings.compression_stiffness = 6.0
settings.shear_stiffness = 4.0
settings.bending_stiffness = 0.03
settings.air_damping = 0.3

# =========================
# SCENE PHYSICS
# =========================
scene = bpy.context.scene
scene.use_gravity = True
scene.gravity = (0, 0, -9.81)

scene.frame_start = 1
scene.frame_end = 120

# =========================
# POSITION GARMENT ABOVE AVATAR (SAFETY)
# =========================
garment.location.z += 0.05

# =========================
# BAKE SIMULATION
# =========================
bpy.context.view_layer.objects.active = garment
bpy.ops.ptcache.free_bake_all()
bpy.ops.ptcache.bake_all(bake=True)

# =========================
# EXPORT FINAL GLB
# =========================
bpy.ops.export_scene.gltf(
    filepath=OUTPUT_GLB,
    export_format='GLB',
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT'
)

print("✅ Collision simulation complete.")
print(f"📦 Output saved to: {OUTPUT_GLB}")