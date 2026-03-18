"""
MIRAAA Mannequin Collision Test
Fits T-shirt onto a mannequin body using cloth physics simulation
"""

import bpy
import math

OUTPUT_PATH = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/tshirt_fitted.glb"
TSHIRT_PATH = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/tshirt_3d.glb"


def clear_scene():
    """Clear all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_mannequin():
    """Create a simple mannequin body for collision testing."""
    # Body measurements (slightly smaller than T-shirt for proper fit)
    torso_radius = 0.14  # 14cm radius (44cm circumference)
    torso_height = 0.65  # 65cm height
    shoulder_width = 0.40  # 40cm shoulder width
    neck_radius = 0.06  # 6cm neck radius
    neck_height = 0.12  # 12cm neck height
    arm_radius = 0.045  # 4.5cm arm radius
    arm_length = 0.25  # 25cm arm length
    
    # Create torso (main body cylinder)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=torso_radius,
        depth=torso_height,
        location=(0, 0, torso_height/2)
    )
    torso = bpy.context.active_object
    torso.name = "mannequin_torso"
    
    # Create neck
    bpy.ops.mesh.primitive_cylinder_add(
        radius=neck_radius,
        depth=neck_height,
        location=(0, 0, torso_height + neck_height/2)
    )
    neck = bpy.context.active_object
    neck.name = "mannequin_neck"
    
    # Create head (sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.10,
        location=(0, 0, torso_height + neck_height + 0.10)
    )
    head = bpy.context.active_object
    head.name = "mannequin_head"
    
    # Create left arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=arm_radius,
        depth=arm_length,
        location=(-(shoulder_width/2 + arm_length/2), 0, torso_height - 0.05),
        rotation=(0, math.radians(90), 0)
    )
    left_arm = bpy.context.active_object
    left_arm.name = "mannequin_left_arm"
    
    # Create right arm
    bpy.ops.mesh.primitive_cylinder_add(
        radius=arm_radius,
        depth=arm_length,
        location=((shoulder_width/2 + arm_length/2), 0, torso_height - 0.05),
        rotation=(0, math.radians(90), 0)
    )
    right_arm = bpy.context.active_object
    right_arm.name = "mannequin_right_arm"
    
    # Join all parts into one mannequin
    bpy.ops.object.select_all(action='DESELECT')
    torso.select_set(True)
    neck.select_set(True)
    head.select_set(True)
    left_arm.select_set(True)
    right_arm.select_set(True)
    bpy.context.view_layer.objects.active = torso
    bpy.ops.object.join()
    
    mannequin = bpy.context.active_object
    mannequin.name = "mannequin"
    
    # Add collision physics to mannequin
    bpy.context.view_layer.objects.active = mannequin
    bpy.ops.object.modifier_add(type='COLLISION')
    collision = mannequin.modifiers[-1]
    collision.settings.thickness_outer = 0.005  # 0.5cm collision margin
    collision.settings.cloth_friction = 10.0  # High friction for cloth
    
    # Create material for mannequin
    mat = bpy.data.materials.new(name="mannequin_material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.9, 0.85, 0.8, 1.0)  # Skin tone
        bsdf.inputs['Roughness'].default_value = 0.5
    mannequin.data.materials.append(mat)
    
    return mannequin


def load_tshirt():
    """Load the T-shirt GLB file."""
    bpy.ops.import_scene.gltf(filepath=TSHIRT_PATH)
    
    # Find the imported T-shirt object
    tshirt = None
    for obj in bpy.context.selected_objects:
        if 'tshirt' in obj.name.lower():
            tshirt = obj
            break
    
    if not tshirt:
        tshirt = bpy.context.selected_objects[0]
    
    tshirt.name = "tshirt"
    
    # Scale up slightly (T-shirt needs to be bigger than mannequin initially)
    tshirt.scale = (1.08, 1.08, 1.08)
    
    # Position T-shirt around mannequin
    tshirt.location = (0, 0, 0.05)  # Slightly higher
    
    return tshirt


def add_cloth_physics(tshirt):
    """Add cloth physics to T-shirt."""
    bpy.context.view_layer.objects.active = tshirt
    
    # Add cloth modifier
    bpy.ops.object.modifier_add(type='CLOTH')
    cloth = tshirt.modifiers[-1]
    
    # Cloth settings - cotton T-shirt properties
    cloth.settings.quality = 10  # Higher quality simulation
    cloth.settings.mass = 0.15  # 150g per m² (typical cotton)
    cloth.settings.air_damping = 1.0
    cloth.settings.bending_model = 'LINEAR'
    
    # Physical properties
    cloth.settings.tension_stiffness = 15  # Moderate stretch resistance
    cloth.settings.compression_stiffness = 15
    cloth.settings.shear_stiffness = 5  # Allow some shear for natural draping
    cloth.settings.bending_stiffness = 0.5  # Cotton bending
    
    # Damping
    cloth.settings.tension_damping = 5
    cloth.settings.compression_damping = 5
    cloth.settings.shear_damping = 5
    cloth.settings.bending_damping = 0.5
    
    # Collision settings
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.collision_quality = 5
    cloth.collision_settings.distance_min = 0.003  # 3mm minimum distance
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.self_distance_min = 0.002  # 2mm self collision
    
    # Gravity
    cloth.settings.use_pressure = False
    
    print(f"Cloth physics added to {tshirt.name}")


def setup_simulation():
    """Configure simulation settings."""
    scene = bpy.context.scene
    
    # Set frame range for simulation
    scene.frame_start = 1
    scene.frame_end = 150  # 5 seconds at 30fps
    scene.frame_current = 1
    
    # Enable gravity
    scene.use_gravity = True
    scene.gravity = (0, 0, -9.81)
    
    print("Simulation configured: 150 frames")


def run_simulation():
    """Run the cloth simulation."""
    print("\nRunning cloth simulation...")
    print("This may take a few minutes...")
    
    # Bake the simulation
    bpy.ops.ptcache.bake_all(bake=True)
    
    print("Simulation complete!")


def export_result(frame=150):
    """Export the fitted T-shirt at a specific frame."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    
    # Select only the T-shirt for export
    bpy.ops.object.select_all(action='DESELECT')
    tshirt = bpy.data.objects.get('tshirt')
    if tshirt:
        tshirt.select_set(True)
        bpy.context.view_layer.objects.active = tshirt
        
        # Apply cloth modifier to freeze simulation result
        bpy.ops.object.modifier_apply(modifier="Cloth")
        
        # Export
        bpy.ops.export_scene.gltf(
            filepath=OUTPUT_PATH,
            use_selection=True,
            export_format='GLB',
            export_materials='EXPORT',
            export_draco_mesh_compression_enable=True
        )
        
        print(f"\nExported fitted T-shirt to: {OUTPUT_PATH}")


def main():
    print("=" * 60)
    print("MIRAAA Mannequin Collision Test")
    print("=" * 60)
    
    # Clear scene
    clear_scene()
    
    # Create mannequin
    print("\n1. Creating mannequin...")
    mannequin = create_mannequin()
    print(f"   Mannequin created: {mannequin.name}")
    
    # Load T-shirt
    print("\n2. Loading T-shirt...")
    tshirt = load_tshirt()
    print(f"   T-shirt loaded: {tshirt.name}")
    
    # Add cloth physics
    print("\n3. Adding cloth physics...")
    add_cloth_physics(tshirt)
    
    # Setup simulation
    print("\n4. Setting up simulation...")
    setup_simulation()
    
    # Run simulation
    print("\n5. Running simulation...")
    run_simulation()
    
    # Export result
    print("\n6. Exporting fitted T-shirt...")
    export_result(frame=150)
    
    print("\n" + "=" * 60)
    print("MANNEQUIN COLLISION TEST COMPLETE!")
    print("=" * 60)
    print(f"\nYou can:")
    print(f"  1. View the fitted T-shirt: {OUTPUT_PATH}")
    print(f"  2. Open this .blend file to see the full simulation")
    print(f"  3. Adjust frame number in export_result() to see different fit stages")


if __name__ == "__main__":
    main()
