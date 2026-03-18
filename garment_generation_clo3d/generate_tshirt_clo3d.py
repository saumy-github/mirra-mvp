"""
CLO3D T-Shirt Generator - Optimized for CLO3D Simulation
Creates lightweight T-shirt mesh suitable for CLO3D physics simulation
Subdivision Level 1 for balance between quality and performance
"""

import bpy
import bmesh
import math
from mathutils import Vector

OUTPUT_PATH = r"C:\Users\Anant\mirra-mvp\garment_generation_clo3d\tshirt_clo3d.glb"


def clear_scene():
    """Clear all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_realistic_tshirt():
    """
    Create a realistic T-shirt as a continuous mesh.
    Body forms a tube, sleeves properly integrated.
    Optimized for CLO3D simulation.
    """
    
    # Dimensions in CENTIMETERS for CLO3D compatibility
    body_width = 50.0         # HalfChestWidth: 50cm
    body_length = 70.0        # GarmentLength: 70cm
    body_depth = 18.0         # Front-to-back depth (estimated)
    
    waist_scale = 0.96        # Waist slightly narrower
    hem_scale = 1.00          # HemWidth matches chest: 50cm
    
    neck_radius = 9.0         # NeckWidth: 18cm (radius = 9cm)
    neck_depth_front = 9.0    # Neck.front: 9cm
    neck_depth_back = 3.0     # Neck.back: 3cm
    
    sleeve_length = 22.0      # SleeveLength: 22cm
    bicep_width = 36.0        # BicepWidth: 36cm
    sleeve_radius_shoulder = bicep_width / (2 * math.pi)  # Circumference to radius
    sleeve_radius_end = 7.0   # 7cm at wrist
    
    armhole_depth = 22.0      # ArmholeDepth: 22cm
    shoulder_width = 44.0     # ShoulderWidth: 44cm
    neckband_height = 4.0     # BandHeight: 4cm
    
    mesh = bpy.data.meshes.new("tshirt_mesh")
    obj = bpy.data.objects.new("tshirt", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Number of segments around body
    body_segments = 16
    
    # Create body as horizontal rings
    body_rings = []
    
    # Heights and scales for body rings
    ring_specs = [
        (0.00, hem_scale),       # Hem
        (0.20, waist_scale),     # Waist
        (0.40, 1.0),             # Mid chest
        (body_length - armhole_depth, 1.0),  # Armpit level
    ]
    
    for height, scale in ring_specs:
        ring = []
        for i in range(body_segments):
            angle = 2 * math.pi * i / body_segments
            # Elliptical cross-section (wider side-to-side, narrower front-to-back)
            x = (body_width / 2) * scale * math.cos(angle)
            y = (body_depth / 2) * scale * math.sin(angle)
            v = bm.verts.new((x, y, height))
            ring.append(v)
        body_rings.append(ring)
    
    # Create faces between rings
    for r in range(len(body_rings) - 1):
        ring1 = body_rings[r]
        ring2 = body_rings[r + 1]
        for i in range(body_segments):
            i_next = (i + 1) % body_segments
            bm.faces.new([ring1[i], ring1[i_next], ring2[i_next], ring2[i]])
    
    # DON'T close bottom hem - leave it open for wearability
    
    # Create shoulder/neck area
    armpit_ring = body_rings[-1]
    armpit_height = body_length - armhole_depth
    shoulder_height = body_length - 3.0  # 3cm below top
    
    # Shoulder ring (narrower for neck opening, wider at sides for sleeve attachment)
    shoulder_ring = []
    shoulder_radius = body_width / 2 * 0.85
    
    for i in range(body_segments):
        angle = 2 * math.pi * i / body_segments
        
        # Modify radius based on position
        # Wider at sides (±90°) for sleeve attachment
        # Narrower at front/back (0°, 180°) for neck
        side_factor = abs(math.cos(angle))  # 1 at sides, 0 at front/back
        r = shoulder_radius * (0.7 + 0.3 * side_factor)
        
        x = r * math.cos(angle)
        y = (body_depth / 2 * 0.75) * math.sin(angle)
        v = bm.verts.new((x, y, shoulder_height))
        shoulder_ring.append(v)
    
    # Connect armpit to shoulder
    for i in range(body_segments):
        i_next = (i + 1) % body_segments
        bm.faces.new([armpit_ring[i], armpit_ring[i_next], shoulder_ring[i_next], shoulder_ring[i]])
    
    # Create neckline opening with proper neckband
    neck_segments = 16
    neck_verts_inner = []  # Inner edge of neckband
    neck_verts_outer = []  # Outer edge connecting to body
    
    # Neckband dimensions
    neckband_width = neckband_height  # BandHeight: 4cm
    
    for i in range(neck_segments):
        angle = 2 * math.pi * i / neck_segments
        
        # Inner neckline (the actual opening)
        x_inner = neck_radius * math.cos(angle)
        y_inner = neck_radius * 0.8 * math.sin(angle)  # Slightly oval
        
        # Different depth for front vs back
        if math.sin(angle) > 0:  # Front half
            z = body_length - neck_depth_front * (1 - abs(math.cos(angle)) * 0.3)
        else:  # Back half
            z = body_length - neck_depth_back
        
        v_inner = bm.verts.new((x_inner, y_inner, z))
        neck_verts_inner.append(v_inner)
        
        # Outer neckband edge (connects to shoulder)
        x_outer = (neck_radius + neckband_width) * math.cos(angle)
        y_outer = (neck_radius + neckband_width) * 0.8 * math.sin(angle)
        z_outer = z + neckband_width * 0.5  # Slightly higher for natural look
        
        v_outer = bm.verts.new((x_outer, y_outer, z_outer))
        neck_verts_outer.append(v_outer)
    
    # Create neckband faces (tube between inner and outer)
    for i in range(neck_segments):
        i_next = (i + 1) % neck_segments
        bm.faces.new([
            neck_verts_inner[i],
            neck_verts_inner[i_next],
            neck_verts_outer[i_next],
            neck_verts_outer[i]
        ])
    
    # Connect shoulder ring to neckband outer edge
    for i in range(neck_segments):
        i_next = (i + 1) % neck_segments
        neck_angle = 2 * math.pi * i / neck_segments
        
        # Find closest shoulder vertex
        shoulder_idx = int((neck_angle / (2 * math.pi)) * body_segments) % body_segments
        shoulder_idx_next = (shoulder_idx + 1) % body_segments
        
        # Create face connecting neckband to shoulder
        try:
            bm.faces.new([
                shoulder_ring[shoulder_idx],
                shoulder_ring[shoulder_idx_next],
                neck_verts_outer[i_next],
                neck_verts_outer[i]
            ])
        except:
            # If quad fails, create triangles
            try:
                bm.faces.new([shoulder_ring[shoulder_idx], neck_verts_outer[i], neck_verts_outer[i_next]])
                bm.faces.new([shoulder_ring[shoulder_idx], neck_verts_outer[i_next], shoulder_ring[shoulder_idx_next]])
            except:
                pass
    
    # Create sleeves integrated with body
    def create_integrated_sleeve(side):
        """Create sleeve that merges perfectly with armhole"""
        
        sleeve_segments = 12
        
        # First, identify and extract the armhole vertices from body
        armhole_verts = []
        
        # Determine angle range for this side's armhole
        if side > 0:  # Right side (0° ± 45°)
            angle_range = (-math.pi/4, math.pi/4)
        else:  # Left side (180° ± 45°)
            angle_range = (3*math.pi/4, 5*math.pi/4)
        
        # Collect vertices from both armpit and shoulder rings that are on this side
        for ring in [armpit_ring, shoulder_ring]:
            for i, v in enumerate(ring):
                angle = 2 * math.pi * i / body_segments
                # Normalize angle to 0-2π
                angle = angle % (2 * math.pi)
                
                # Check if vertex is in the angle range for this side
                if side > 0:
                    if angle < angle_range[1] or angle > (2*math.pi + angle_range[0]):
                        armhole_verts.append(v)
                else:
                    if angle_range[0] <= angle <= angle_range[1]:
                        armhole_verts.append(v)
        
        # Sort armhole vertices by height (z coordinate) to create ordered ring
        armhole_verts.sort(key=lambda v: v.co.z, reverse=True)
        
        if len(armhole_verts) < 4:
            return  # Not enough vertices to create sleeve
        
        # Create sleeve attachment ring
        sleeve_base_ring = []
        
        center_x = side * body_width / 2
        center_y = 0
        center_z = (armpit_height + shoulder_height) / 2
        
        # Redistribute vertices evenly around the armhole
        for i in range(sleeve_segments):
            t = i / sleeve_segments
            
            # Interpolate between armhole vertices
            idx = int(t * (len(armhole_verts) - 1))
            idx_next = min(idx + 1, len(armhole_verts) - 1)
            frac = (t * (len(armhole_verts) - 1)) - idx
            
            # Interpolate position
            v1 = armhole_verts[idx].co
            v2 = armhole_verts[idx_next].co
            
            x = v1.x + (v2.x - v1.x) * frac
            y = v1.y + (v2.y - v1.y) * frac
            z = v1.z + (v2.z - v1.z) * frac
            
            v = bm.verts.new((x, y, z))
            sleeve_base_ring.append(v)
        
        # Now create the rest of the sleeve extending outward
        sleeve_rings = [sleeve_base_ring]
        num_rings = 4
        
        for r in range(1, num_rings):
            t = r / (num_rings - 1)
            
            # Calculate position along sleeve
            ring_x = center_x + side * sleeve_length * t
            ring_z = center_z - armhole_depth * 0.15 * t
            radius = sleeve_radius_shoulder - (sleeve_radius_shoulder - sleeve_radius_end) * t
            
            ring = []
            for i in range(sleeve_segments):
                angle = 2 * math.pi * i / sleeve_segments
                y = radius * math.cos(angle)
                z = ring_z + radius * math.sin(angle)
                v = bm.verts.new((ring_x, y, z))
                ring.append(v)
            sleeve_rings.append(ring)
        
        # Create faces along sleeve
        for r in range(len(sleeve_rings) - 1):
            ring1 = sleeve_rings[r]
            ring2 = sleeve_rings[r + 1]
            for i in range(sleeve_segments):
                i_next = (i + 1) % sleeve_segments
                if side > 0:
                    bm.faces.new([ring1[i], ring2[i], ring2[i_next], ring1[i_next]])
                else:
                    bm.faces.new([ring1[i], ring1[i_next], ring2[i_next], ring2[i]])
        
        # Connect sleeve base to armhole
        num_armhole = len(armhole_verts)
        
        for i in range(num_armhole):
            armhole_v = armhole_verts[i]
            armhole_v_next = armhole_verts[(i + 1) % num_armhole]
            
            # Find closest sleeve base vertices
            sleeve_idx = int((i / num_armhole) * sleeve_segments) % sleeve_segments
            sleeve_idx_next = int(((i + 1) / num_armhole) * sleeve_segments) % sleeve_segments
            
            if sleeve_idx != sleeve_idx_next:
                try:
                    if side > 0:
                        bm.faces.new([
                            armhole_v,
                            armhole_v_next,
                            sleeve_base_ring[sleeve_idx_next],
                            sleeve_base_ring[sleeve_idx]
                        ])
                    else:
                        bm.faces.new([
                            armhole_v,
                            sleeve_base_ring[sleeve_idx],
                            sleeve_base_ring[sleeve_idx_next],
                            armhole_v_next
                        ])
                except:
                    try:
                        if side > 0:
                            bm.faces.new([armhole_v, armhole_v_next, sleeve_base_ring[sleeve_idx]])
                        else:
                            bm.faces.new([armhole_v, sleeve_base_ring[sleeve_idx], armhole_v_next])
                    except:
                        pass
    
    # Create both sleeves
    create_integrated_sleeve(1)   # Right
    create_integrated_sleeve(-1)  # Left
    
    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Clean up and smooth
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Remove doubles to merge seam vertices
    bpy.ops.mesh.remove_doubles(threshold=2.0)  # 2cm threshold
    
    # Recalculate normals
    bpy.ops.mesh.normals_make_consistent(inside=False)
    
    # Additional subdivision pass for smoother seams
    bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0.3)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Add Subdivision Surface modifier - LEVEL 1 FOR CLO3D PERFORMANCE
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 1  # ⚡ REDUCED TO LEVEL 1 FOR CLO3D SIMULATION
    subsurf.render_levels = 1
    subsurf.quality = 4
    subsurf.subdivision_type = 'CATMULL_CLARK'
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=subsurf.name)
    
    # Final smoothing pass
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Smooth vertices to blend seams
    bpy.ops.mesh.vertices_smooth(factor=0.5, repeat=2)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    return obj


def create_material(color=(0.15, 0.15, 0.15, 1.0)):
    """Create fabric material."""
    mat = bpy.data.materials.new(name="tshirt_fabric")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.85
    return mat


def export_glb(obj, filepath):
    """Export as GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        use_selection=True,
        export_format='GLB',
        export_materials='EXPORT'
    )
    print(f"Exported GLB: {filepath}")


def export_obj(obj, filepath):
    """Export as OBJ."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_materials=True,
        export_uv=True,
        export_normals=True,
        export_triangulated_mesh=False
    )
    print(f"Exported OBJ: {filepath}")


def main():
    print("=" * 60)
    print("CLO3D T-Shirt Generator - Optimized for Simulation")
    print("Subdivision Level 1 (Low Poly)")
    print("=" * 60)
    
    clear_scene()
    
    print("\nCreating optimized T-shirt for CLO3D...")
    tshirt = create_realistic_tshirt()
    
    # Add material
    mat = create_material(color=(0.12, 0.12, 0.12, 1.0))
    tshirt.data.materials.append(mat)
    
    print(f"\nFinal T-shirt:")
    print(f"  Vertices: {len(tshirt.data.vertices)}")
    print(f"  Faces: {len(tshirt.data.polygons)}")
    print(f"  Estimated Triangles: {len(tshirt.data.polygons) * 2}")
    print(f"  Dimensions: {tshirt.dimensions}")
    
    # Export both formats
    glb_path = OUTPUT_PATH
    obj_path = OUTPUT_PATH.replace('.glb', '.obj')
    
    export_glb(tshirt, glb_path)
    export_obj(tshirt, obj_path)
    
    print("\n" + "=" * 60)
    print("✅ CLO3D-OPTIMIZED T-SHIRT COMPLETE!")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  GLB: {glb_path}")
    print(f"  OBJ: {obj_path}")
    print(f"\nThis mesh should simulate smoothly in CLO3D!")


if __name__ == "__main__":
    main()
