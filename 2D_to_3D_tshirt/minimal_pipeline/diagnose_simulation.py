"""
Diagnose why the cloth simulation isn't visible/working
"""
import bpy

print("\n" + "="*60)
print("   SIMULATION DIAGNOSTIC")
print("="*60)

# Check if objects exist
garment = bpy.data.objects.get("TShirt_Garment")
avatar = bpy.data.objects.get("Avatar_Smooth_Collision")

if not garment:
    print("\n❌ ERROR: TShirt_Garment not found in scene!")
    print("Available objects:", list(bpy.data.objects.keys()))
    exit(1)

if not avatar:
    print("\n❌ ERROR: Avatar_Smooth_Collision not found!")
    print("Available objects:", list(bpy.data.objects.keys()))
    exit(1)

print(f"\n✓ Found TShirt_Garment")
print(f"✓ Found Avatar_Smooth_Collision")

# Check visibility
print(f"\n--- VISIBILITY ---")
print(f"Garment hide_viewport: {garment.hide_viewport}")
print(f"Garment hide_render: {garment.hide_render}")
print(f"Garment visible in viewport: {not garment.hide_get()}")

if garment.hide_viewport or garment.hide_get():
    print("\n🔧 FIX: Unhiding garment...")
    garment.hide_viewport = False
    garment.hide_render = False
    garment.hide_set(False)
    print("✓ Garment unhidden")

# Check positions
print(f"\n--- POSITIONS ---")
print(f"Garment location: X={garment.location.x:.2f}, Y={garment.location.y:.2f}, Z={garment.location.z:.2f}")
print(f"Avatar location:  X={avatar.location.x:.2f}, Y={avatar.location.y:.2f}, Z={avatar.location.z:.2f}")

if abs(garment.location.z - avatar.location.z) < 0.1:
    print("\n⚠ WARNING: Garment and avatar are at same height!")
    print("  Garment should be ABOVE avatar (Z = 0.73m, Avatar Z = 0m)")
    print("\n🔧 FIX: Repositioning...")
    garment.location.z = 0.73
    avatar.location.z = 0
    print(f"✓ Garment moved to Z={garment.location.z}")
    print(f"✓ Avatar at Z={avatar.location.z}")

# Check mesh
print(f"\n--- MESH ---")
mesh = garment.data
print(f"Vertices: {len(mesh.vertices)}")
print(f"Faces: {len(mesh.polygons)}")

if len(mesh.polygons) == 0:
    print("❌ ERROR: Garment has NO FACES! Cannot simulate empty mesh.")
    exit(1)

# Check cloth modifier
print(f"\n--- CLOTH MODIFIER ---")
cloth_mod = None
for mod in garment.modifiers:
    if mod.type == 'CLOTH':
        cloth_mod = mod
        break

if not cloth_mod:
    print("❌ ERROR: No cloth modifier found!")
    print(f"Available modifiers: {[m.name for m in garment.modifiers]}")
    exit(1)

print(f"✓ Cloth modifier found: {cloth_mod.name}")
print(f"  Quality: {cloth_mod.settings.quality}")
print(f"  Mass: {cloth_mod.settings.mass}")
print(f"  Gravity: {cloth_mod.settings.effector_weights.gravity}")
print(f"  Sewing: {cloth_mod.settings.use_sewing_springs}")

if cloth_mod.settings.use_sewing_springs:
    print(f"  Sewing force: {cloth_mod.settings.sewing_force_max}")

# Check collision
print(f"\n--- AVATAR COLLISION ---")
has_collision = False
for mod in avatar.modifiers:
    if mod.type == 'COLLISION':
        has_collision = True
        print(f"✓ Collision modifier found")
        print(f"  Thickness: {mod.settings.thickness_outer}")
        break

if not has_collision:
    print("⚠ WARNING: Avatar has no collision modifier!")
    print("  Adding collision...")
    coll = avatar.modifiers.new(name="Collision", type='COLLISION')
    coll.settings.thickness_outer = 0.02
    print("✓ Collision added")

# Check cache
print(f"\n--- SIMULATION CACHE ---")
cache = cloth_mod.point_cache
print(f"Cache baked: {cache.is_baked}")
print(f"Cache frames: {cache.frame_start} to {cache.frame_end}")

if cache.is_baked:
    print("✓ Simulation was baked (pre-calculated)")
    print("  → Just press SPACEBAR to play")
else:
    print("⚠ Simulation NOT baked")
    print("  → Press SPACEBAR and Blender will calculate on-the-fly (slower)")

# Check scene settings
print(f"\n--- SCENE SETTINGS ---")
scene = bpy.context.scene
print(f"Current frame: {scene.frame_current}")
print(f"Frame range: {scene.frame_start} to {scene.frame_end}")
print(f"Gravity: {scene.gravity}")

# Set to frame 1 for testing
scene.frame_set(1)
print(f"\n✓ Set to frame 1")

# Save changes
print(f"\n--- SAVING FIXES ---")
bpy.ops.wm.save_mainfile()
print("✓ Saved file with fixes applied")

print("\n" + "="*60)
print("   DIAGNOSTIC COMPLETE")
print("="*60)
print("""
NEXT STEPS:
1. Re-open the file in Blender
2. You should now see the garment ABOVE the avatar
3. Press SPACEBAR - garment should fall downward
4. Watch frames 1-150

If still nothing moves, the simulation needs to be re-baked.
""")
