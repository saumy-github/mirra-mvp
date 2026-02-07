"""
COMPREHENSIVE DIAGNOSTIC SCRIPT FOR BLENDER STEP 5
Run this in Blender Python Console to diagnose why simulation isn't working
"""

import bpy

print("="*70)
print("BLENDER SCENE DIAGNOSTIC - DETAILED ANALYSIS")
print("="*70)

# ============================================
# 1. CHECK GARMENT OBJECT
# ============================================
print("\n" + "="*70)
print("1. GARMENT MESH ANALYSIS")
print("="*70)

garment = bpy.data.objects.get('TShirt_Garment')
if not garment:
    print("❌ CRITICAL: TShirt_Garment not found!")
    print("Available objects:", [obj.name for obj in bpy.data.objects])
else:
    print(f"✓ Found: {garment.name}")
    print(f"  Type: {garment.type}")
    print(f"  Location: {garment.location}")
    print(f"  Dimensions: {garment.dimensions}")
    
    mesh = garment.data
    print(f"\nMesh Statistics:")
    print(f"  Vertices: {len(mesh.vertices)}")
    print(f"  Edges: {len(mesh.edges)}")
    print(f"  Faces: {len(mesh.polygons)}")
    
    if len(mesh.polygons) == 0:
        print("  ❌ CRITICAL: NO FACES! Cloth needs faces to simulate")
        print("     The mesh is just edges, no surface area")
    else:
        print(f"  ✓ Has {len(mesh.polygons)} faces")
    
    print(f"\nVertex Groups:")
    if len(garment.vertex_groups) == 0:
        print("  ⚠ No vertex groups (sewing won't work)")
    else:
        for vg in garment.vertex_groups:
            print(f"  - {vg.name}")

# ============================================
# 2. CHECK CLOTH MODIFIER
# ============================================
print("\n" + "="*70)
print("2. CLOTH MODIFIER CHECK")
print("="*70)

if garment:
    cloth_mod = None
    for mod in garment.modifiers:
        print(f"Modifier: {mod.name} (type: {mod.type})")
        if mod.type == 'CLOTH':
            cloth_mod = mod
    
    if not cloth_mod:
        print("❌ CRITICAL: NO CLOTH MODIFIER!")
        print("   Adding it now...")
        cloth_mod = garment.modifiers.new('Cloth', 'CLOTH')
    else:
        print(f"✓ Cloth modifier exists: {cloth_mod.name}")
    
    if cloth_mod:
        settings = cloth_mod.settings
        print(f"\nCloth Settings:")
        print(f"  Quality: {settings.quality}")
        print(f"  Mass: {settings.mass}")
        print(f"  Gravity: {settings.effector_weights.gravity}")
        print(f"  Tension Stiffness: {settings.tension_stiffness}")
        print(f"  Compression Stiffness: {settings.compression_stiffness}")
        print(f"  Bending Stiffness: {settings.bending_stiffness}")
        print(f"  Use Sewing: {settings.use_sewing_springs}")
        if settings.use_sewing_springs:
            print(f"    Sewing Force: {settings.sewing_force_max}")
        
        print(f"\nCache Status:")
        print(f"  Is Baked: {cloth_mod.point_cache.is_baked}")
        print(f"  Frame Start: {cloth_mod.point_cache.frame_start}")
        print(f"  Frame End: {cloth_mod.point_cache.frame_end}")
        
        # Check if cloth is pinned
        if settings.vertex_group_mass:
            print(f"  ⚠ Pin Group: {settings.vertex_group_mass}")
            print(f"     If all vertices are pinned, nothing will move!")

# ============================================
# 3. CHECK GRAVITY & SCENE PHYSICS
# ============================================
print("\n" + "="*70)
print("3. SCENE PHYSICS & GRAVITY")
print("="*70)

scene = bpy.context.scene
print(f"Gravity: {scene.gravity}")
if scene.gravity[2] == 0:
    print("❌ CRITICAL: Z-gravity is 0! Cloth won't fall")
    print("   Setting gravity to -9.8...")
    scene.gravity = (0, 0, -9.8)
else:
    print(f"✓ Gravity enabled: {scene.gravity[2]} m/s²")

print(f"\nTimeline:")
print(f"  Current Frame: {scene.frame_current}")
print(f"  Frame Range: {scene.frame_start} to {scene.frame_end}")
print(f"  FPS: {scene.render.fps}")

# ============================================
# 4. CHECK AVATAR COLLISION
# ============================================
print("\n" + "="*70)
print("4. AVATAR COLLISION")
print("="*70)

avatar = bpy.data.objects.get('Avatar_Smooth_Collision')
if not avatar:
    print("⚠ Avatar not found")
    print("Available objects:", [obj.name for obj in bpy.data.objects if 'Avatar' in obj.name])
else:
    print(f"✓ Found: {avatar.name}")
    print(f"  Location: {avatar.location}")
    print(f"  Dimensions: {avatar.dimensions}")
    
    has_collision = False
    for mod in avatar.modifiers:
        print(f"  Modifier: {mod.name} (type: {mod.type})")
        if mod.type == 'COLLISION':
            has_collision = True
            print(f"    Thickness: {mod.settings.thickness_outer}")
            print(f"    Friction: {mod.settings.friction_factor}")
            print(f"    Damping: {mod.settings.damping}")
    
    if not has_collision:
        print("  ❌ NO COLLISION MODIFIER!")
        print("     Adding it now...")
        coll = avatar.modifiers.new('Collision', 'COLLISION')
        print("     ✓ Added collision")

# ============================================
# 5. CHECK MESH POSITION RELATIVE TO AVATAR
# ============================================
print("\n" + "="*70)
print("5. SPATIAL RELATIONSHIP")
print("="*70)

if garment and avatar:
    g_loc = garment.location
    a_loc = avatar.location
    
    print(f"Garment location: {g_loc}")
    print(f"Avatar location: {a_loc}")
    print(f"Distance: {(g_loc - a_loc).length:.3f} meters")
    
    # Check if garment is above avatar
    if g_loc.z < a_loc.z:
        print(f"⚠ WARNING: Garment Z ({g_loc.z:.3f}) is BELOW avatar Z ({a_loc.z:.3f})")
        print(f"   Garment should start above avatar to fall onto it")

# ============================================
# 6. VERTEX POSITION SAMPLING
# ============================================
print("\n" + "="*70)
print("6. VERTEX POSITION SAMPLES (first 5)")
print("="*70)

if garment:
    mesh = garment.data
    for i, v in enumerate(mesh.vertices[:5]):
        world_co = garment.matrix_world @ v.co
        print(f"  Vertex {i}: local={v.co} world={world_co}")

# ============================================
# 7. SIMULATION TEST
# ============================================
print("\n" + "="*70)
print("7. QUICK SIMULATION TEST")
print("="*70)

print("Going to frame 1...")
bpy.context.scene.frame_set(1)

if garment and cloth_mod:
    # Get vertex position at frame 1
    v0_frame1 = garment.matrix_world @ mesh.vertices[0].co
    print(f"Vertex 0 at frame 1: {v0_frame1}")
    
    # Jump to frame 10
    print("Jumping to frame 10...")
    bpy.context.scene.frame_set(10)
    v0_frame10 = garment.matrix_world @ mesh.vertices[0].co
    print(f"Vertex 0 at frame 10: {v0_frame10}")
    
    # Check if it moved
    distance = (v0_frame10 - v0_frame1).length
    print(f"\nMovement: {distance:.6f} meters")
    
    if distance < 0.001:
        print("❌ PROBLEM: Vertex didn't move!")
        print("\nPossible causes:")
        print("  1. Mesh has no faces (just edges)")
        print("  2. All vertices are pinned")
        print("  3. Gravity is 0")
        print("  4. Cloth settings too stiff")
        print("  5. Cache is baked and frozen")
    else:
        print(f"✓ Vertex moved {distance:.6f}m - simulation working!")

# ============================================
# 8. RECOMMENDATIONS
# ============================================
print("\n" + "="*70)
print("8. RECOMMENDED FIXES")
print("="*70)

fixes = []

if garment and len(garment.data.polygons) == 0:
    fixes.append("CRITICAL: Add faces to mesh - cloth needs surface area")
    fixes.append("  Run: bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.fill()")

if not cloth_mod:
    fixes.append("Add cloth modifier to garment")

if cloth_mod and settings.effector_weights.gravity == 0:
    fixes.append("Enable gravity in cloth settings")

if scene.gravity[2] == 0:
    fixes.append("Enable scene gravity: bpy.context.scene.gravity = (0, 0, -9.8)")

if not has_collision:
    fixes.append("Add collision to avatar")

if cloth_mod and cloth_mod.point_cache.is_baked:
    fixes.append("Clear baked cache: bpy.ops.ptcache.free_bake_all()")

if fixes:
    print("\n🔧 APPLY THESE FIXES:\n")
    for i, fix in enumerate(fixes, 1):
        print(f"{i}. {fix}")
else:
    print("✓ No obvious issues detected")
    print("  If simulation still doesn't work, check:")
    print("  - Are panels positioned correctly?")
    print("  - Is timeline playing properly?")
    print("  - Try resetting cache and re-simulating")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
