"""
Analyze the baked simulation to see what's wrong
"""
import bpy
import math

print("\n" + "="*60)
print("   SIMULATION ANALYSIS")
print("="*60)

scene = bpy.context.scene
garment = bpy.data.objects["TShirt_Garment"]

# Check at key frames
test_frames = [1, 30, 75, 150]

print("\nGarment position over time:")
print(f"{'Frame':<8} {'Z (height)':<15} {'X-spread':<15} {'Y-spread':<15}")
print("-" * 60)

for frame in test_frames:
    scene.frame_set(frame)
    
    # Get bounding box after cloth deformation
    mesh = garment.data
    if len(mesh.vertices) == 0:
        continue
    
    # Calculate bounds
    coords = [garment.matrix_world @ v.co for v in mesh.vertices]
    
    min_x = min(c.x for c in coords)
    max_x = max(c.x for c in coords)
    min_y = min(c.y for c in coords)
    max_y = max(c.y for c in coords)
    min_z = min(c.z for c in coords)
    max_z = max(c.z for c in coords)
    
    avg_z = sum(c.z for c in coords) / len(coords)
    x_spread = max_x - min_x
    y_spread = max_y - min_y
    
    print(f"{frame:<8} {avg_z:>6.2f}m (avg)    {x_spread:>6.2f}m          {y_spread:>6.2f}m")

# Check cloth settings
print("\n" + "="*60)
print("   CLOTH SETTINGS (might need adjustment)")
print("="*60)

cloth_mod = None
for mod in garment.modifiers:
    if mod.type == 'CLOTH':
        cloth_mod = mod
        break

if cloth_mod:
    settings = cloth_mod.settings
    
    print(f"\nPhysics parameters:")
    print(f"  Quality: {settings.quality} (higher = more stable)")
    print(f"  Mass: {settings.mass} kg/m²")
    print(f"  Tension stiffness: {settings.tension_stiffness} (lower = more floppy)")
    print(f"  Bending stiffness: {settings.bending_stiffness}")
    print(f"  Gravity: {settings.effector_weights.gravity}x")
    
    print(f"\nSewing springs:")
    print(f"  Enabled: {settings.use_sewing_springs}")
    if settings.use_sewing_springs:
        print(f"  Max force: {settings.sewing_force_max}")
        print(f"  Shrink min: {settings.shrink_min}")
        
        if settings.sewing_force_max > 50:
            print(f"  ⚠ WARNING: Sewing force {settings.sewing_force_max} is VERY HIGH!")
            print(f"     This can cause pieces to spin/twist violently")
            print(f"     Recommended: 10-25 for gentle joining")
    
    print(f"\nCollision:")
    print(f"  Self collision: {settings.use_self_collision}")
    print(f"  Distance: {settings.collision_quality if hasattr(settings, 'collision_quality') else 'N/A'}")
    
    if not settings.use_self_collision:
        print(f"  ⚠ WARNING: Self-collision is OFF!")
        print(f"     Sleeves can pass through body without this")

# Check vertex groups
print("\n" + "="*60)
print("   SEAM VERTEX GROUPS")
print("="*60)

sewing_groups = [vg for vg in garment.vertex_groups if 'sew_' in vg.name]
print(f"\nFound {len(sewing_groups)} sewing groups:")
for vg in sewing_groups:
    # Count vertices in group
    count = sum(1 for v in mesh.vertices if vg.index in [g.group for g in v.groups])
    print(f"  {vg.name}: {count} vertices")

if len(sewing_groups) == 0:
    print("  ❌ NO SEWING GROUPS FOUND!")
    print("     Pieces won't join without vertex groups")

# Check for issues
print("\n" + "="*60)
print("   DIAGNOSIS")
print("="*60)

issues = []
fixes = []

# Check if garment is falling
scene.frame_set(1)
z_start = sum((garment.matrix_world @ v.co).z for v in mesh.vertices) / len(mesh.vertices)
scene.frame_set(150)
z_end = sum((garment.matrix_world @ v.co).z for v in mesh.vertices) / len(mesh.vertices)

if abs(z_start - z_end) < 0.1:
    issues.append("Garment barely moved vertically")
    fixes.append("Increase gravity or reduce stiffness")
else:
    print(f"\n✓ Garment fell {z_start - z_end:.2f}m (good!)")

if cloth_mod and cloth_mod.settings.sewing_force_max > 50:
    issues.append(f"Sewing force too high ({cloth_mod.settings.sewing_force_max})")
    fixes.append("Reduce sewing force to 15-25")

if cloth_mod and not cloth_mod.settings.use_self_collision:
    issues.append("Self-collision disabled")
    fixes.append("Enable self-collision to prevent pieces passing through each other")

if len(sewing_groups) < 4:
    issues.append(f"Only {len(sewing_groups)} sewing groups (expected 8)")
    fixes.append("Re-run setup to create proper seam groups")

if issues:
    print("\n❌ PROBLEMS DETECTED:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print("\n🔧 RECOMMENDED FIXES:")
    for i, fix in enumerate(fixes, 1):
        print(f"  {i}. {fix}")
else:
    print("\n✓ No obvious issues detected")
    print("  The simulation might just need better initial positioning")

print("\n" + "="*60)
