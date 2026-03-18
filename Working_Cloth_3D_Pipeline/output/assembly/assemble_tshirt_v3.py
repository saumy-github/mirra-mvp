"""
MIRAAA T-Shirt Assembly v3 - Proper T-shirt with correct sleeves, waist, and neckline
"""

import bpy
import bmesh
import math
from mathutils import Vector

OUTPUT_PATH = "/Users/tanujsharma/Desktop/Miraaaaaa/Miraa_new/output/assembly/tshirt_3d.glb"


def clear_scene():
    """Clear all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_tshirt():
    """Create a proper T-shirt mesh with correct proportions."""
    
    # T-shirt dimensions (meters)
    body_width = 0.52       # 52cm chest width
    body_length = 0.68      # 68cm body length
    body_depth = 0.22       # 22cm front-to-back
    
    waist_width = 0.50      # 50cm waist (slightly narrower than chest)
    hem_width = 0.54        # 54cm hem (slightly wider)
    
    shoulder_width = 0.48   # 48cm shoulder to shoulder
    neck_width = 0.18       # 18cm neck opening
    neck_depth_front = 0.10 # 10cm front neck drop
    neck_depth_back = 0.03  # 3cm back neck drop
    
    sleeve_length = 0.22    # 22cm sleeve length
    sleeve_opening = 0.16   # 16cm sleeve opening at shoulder
    sleeve_end = 0.14       # 14cm sleeve end opening
    
    armhole_height = 0.22   # 22cm armhole depth from shoulder
    
    # Number of segments for roundness
    body_segments = 12      # Around the body
    sleeve_segments = 8     # Around the sleeve
    
    mesh = bpy.data.meshes.new("tshirt_mesh")
    obj = bpy.data.objects.new("tshirt", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create body vertices in horizontal rings
    body_rings = []
    
    # Heights for body rings (from bottom to top)
    heights = [
        (0.00, hem_width, body_depth),           # Hem
        (0.15, waist_width * 0.98, body_depth * 0.95),  # Lower body
        (0.30, waist_width, body_depth * 0.92),  # Waist
        (0.45, body_width * 0.98, body_depth * 0.95),  # Upper body
        (body_length - armhole_height, body_width, body_depth),  # Armpit level
    ]
    
    for height, width, depth in heights:
        ring = []
        for i in range(body_segments):
            angle = 2 * math.pi * i / body_segments
            x = (width / 2) * math.cos(angle)
            y = (depth / 2) * math.sin(angle)
            v = bm.verts.new((x, y, height))
            ring.append(v)
        body_rings.append(ring)
    
    # Create faces between body rings
    for r in range(len(body_rings) - 1):
        ring1 = body_rings[r]
        ring2 = body_rings[r + 1]
        for i in range(body_segments):
            i_next = (i + 1) % body_segments
            bm.faces.new([ring1[i], ring1[i_next], ring2[i_next], ring2[i]])
    
    # Close the bottom (hem)
    bm.faces.new(body_rings[0])
    
    # Create shoulder/neck area
    armpit_ring = body_rings[-1]
    
    # Shoulder ring (narrower, at shoulder height)
    shoulder_height = body_length - 0.02  # 2cm below top
    shoulder_ring = []
    for i in range(body_segments):
        angle = 2 * math.pi * i / body_segments
        # Narrower at shoulders, wider at front/back for armholes
        if abs(math.cos(angle)) > 0.5:  # Side areas (armholes)
            r = shoulder_width / 2 * 0.7
        else:  # Front and back
            r = shoulder_width / 2
        x = r * math.cos(angle)
        y = (body_depth / 2 * 0.8) * math.sin(angle)
        v = bm.verts.new((x, y, shoulder_height))
        shoulder_ring.append(v)
    
    # Connect armpit to shoulder
    for i in range(body_segments):
        i_next = (i + 1) % body_segments
        bm.faces.new([armpit_ring[i], armpit_ring[i_next], shoulder_ring[i_next], shoulder_ring[i]])
    
    # Create neckline
    neck_segments = 16
    neck_ring = []
    for i in range(neck_segments):
        angle = 2 * math.pi * i / neck_segments
        x = (neck_width / 2) * math.cos(angle)
        y = (neck_width / 2 * 0.8) * math.sin(angle)
        
        # Vary height for front/back neck drop
        if math.sin(angle) > 0:  # Front
            z = body_length - neck_depth_front * (1 - abs(math.cos(angle)))
        else:  # Back
            z = body_length - neck_depth_back * (1 - abs(math.cos(angle)))
        
        v = bm.verts.new((x, y, z))
        neck_ring.append(v)
    
    # Create shoulder surface (connect shoulder ring to neck ring)
    # This is complex - we need to create a surface with hole for neck
    # Split into front and back panels
    
    # Find indices for front/back/sides of shoulder ring
    front_shoulder = [i for i in range(body_segments) if shoulder_ring[i].co.y > 0]
    back_shoulder = [i for i in range(body_segments) if shoulder_ring[i].co.y < 0]
    
    # Find indices for front/back of neck ring
    front_neck = [i for i in range(neck_segments) if neck_ring[i].co.y > 0]
    back_neck = [i for i in range(neck_segments) if neck_ring[i].co.y < 0]
    
    # Create center top vertex for each shoulder area
    v_top_left = bm.verts.new((-shoulder_width/3, 0, body_length - 0.01))
    v_top_right = bm.verts.new((shoulder_width/3, 0, body_length - 0.01))
    
    # Connect shoulder to neck with triangular faces
    # Front panel
    for i in range(len(front_neck) - 1):
        bm.faces.new([neck_ring[front_neck[i]], neck_ring[front_neck[i+1]], v_top_right if front_neck[i] < neck_segments//4 else v_top_left])
    
    # Back panel  
    for i in range(len(back_neck) - 1):
        bm.faces.new([neck_ring[back_neck[i]], v_top_right if back_neck[i] > neck_segments*3//4 else v_top_left, neck_ring[back_neck[i+1]]])
    
    # Connect shoulder ring outer edge to center tops
    for i in front_shoulder:
        i_next = (i + 1) % body_segments
        if i_next in front_shoulder:
            if shoulder_ring[i].co.x < 0:
                bm.faces.new([shoulder_ring[i], shoulder_ring[i_next], v_top_left])
            else:
                bm.faces.new([shoulder_ring[i], shoulder_ring[i_next], v_top_right])
    
    for i in back_shoulder:
        i_next = (i + 1) % body_segments
        if i_next in back_shoulder:
            if shoulder_ring[i].co.x < 0:
                bm.faces.new([shoulder_ring[i], v_top_left, shoulder_ring[i_next]])
            else:
                bm.faces.new([shoulder_ring[i], v_top_right, shoulder_ring[i_next]])
    
    # Connect tops to neck
    bm.faces.new([v_top_left, v_top_right, neck_ring[0]])
    bm.faces.new([v_top_left, neck_ring[neck_segments//2], v_top_right])
    
    # ========== SLEEVES ==========
    # Create proper tube sleeves
    
    def create_sleeve(side):
        """Create a sleeve on the given side (1 = right, -1 = left)"""
        sleeve_rings = []
        
        # Sleeve attachment point (at armpit level)
        armpit_z = body_length - armhole_height
        attach_x = side * (body_width / 2)
        
        # Create rings along the sleeve
        num_rings = 5
        for r in range(num_rings):
            t = r / (num_rings - 1)  # 0 to 1
            
            # Position along sleeve
            ring_x = attach_x + side * (sleeve_length * t)
            ring_z = armpit_z + armhole_height * 0.5 * (1 - t * 0.3)  # Slight downward angle
            
            # Radius tapers from shoulder to end
            radius = (sleeve_opening / 2) * (1 - t * 0.2) + (sleeve_end / 2) * t * 0.2
            radius = sleeve_opening / 2 - (sleeve_opening - sleeve_end) / 2 * t
            
            ring = []
            for i in range(sleeve_segments):
                angle = 2 * math.pi * i / sleeve_segments
                # Sleeve is oriented along X axis
                y = radius * math.cos(angle)
                z = ring_z + radius * math.sin(angle)
                v = bm.verts.new((ring_x, y, z))
                ring.append(v)
            sleeve_rings.append(ring)
        
        # Create faces between sleeve rings
        for r in range(len(sleeve_rings) - 1):
            ring1 = sleeve_rings[r]
            ring2 = sleeve_rings[r + 1]
            for i in range(sleeve_segments):
                i_next = (i + 1) % sleeve_segments
                if side > 0:
                    bm.faces.new([ring1[i], ring2[i], ring2[i_next], ring1[i_next]])
                else:
                    bm.faces.new([ring1[i], ring1[i_next], ring2[i_next], ring2[i]])
        
        # Close sleeve end
        end_ring = sleeve_rings[-1]
        if side > 0:
            bm.faces.new(end_ring[::-1])
        else:
            bm.faces.new(end_ring)
        
        # Connect sleeve to body at armpit
        # Find the body vertices near the armpit
        first_ring = sleeve_rings[0]
        armpit_verts = [v for v in armpit_ring if (v.co.x * side) > body_width * 0.3]
        
        # Sort by angle
        armpit_verts.sort(key=lambda v: math.atan2(v.co.z - armpit_z, v.co.y))
        
        # Connect with faces
        if len(armpit_verts) >= 2 and len(first_ring) >= 2:
            # Simple connection - top and bottom of sleeve to armpit
            for i in range(min(len(armpit_verts) - 1, sleeve_segments // 2)):
                si = i * 2 % sleeve_segments
                si_next = (si + 1) % sleeve_segments
                try:
                    if side > 0:
                        bm.faces.new([armpit_verts[i], first_ring[si], first_ring[si_next], armpit_verts[i + 1]])
                    else:
                        bm.faces.new([armpit_verts[i], armpit_verts[i + 1], first_ring[si_next], first_ring[si]])
                except:
                    pass
        
        return sleeve_rings
    
    # Create both sleeves
    right_sleeve = create_sleeve(1)
    left_sleeve = create_sleeve(-1)
    
    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Clean up mesh
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Remove doubles
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    
    # Fill holes
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=12)
    
    # Recalculate normals
    bpy.ops.mesh.normals_make_consistent(inside=False)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return obj


def create_tshirt_simple():
    """Create T-shirt using Blender primitives for cleaner result."""
    
    # Body dimensions
    body_width = 0.52
    body_length = 0.68
    body_depth = 0.20
    
    sleeve_length = 0.20
    sleeve_radius = 0.08
    
    neck_radius = 0.09
    
    # Create body as a cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=body_width/2,
        depth=body_length,
        vertices=24,
        location=(0, 0, body_length/2)
    )
    body = bpy.context.active_object
    body.name = "tshirt_body"
    
    # Scale to make it elliptical (front-back thinner)
    body.scale = (1, body_depth/body_width, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    # Create neck hole (to subtract)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=neck_radius,
        depth=0.15,
        vertices=16,
        location=(0, 0, body_length + 0.02)
    )
    neck_cut = bpy.context.active_object
    neck_cut.name = "neck_cut"
    
    # Create sleeves as cylinders
    # Right sleeve
    bpy.ops.mesh.primitive_cylinder_add(
        radius=sleeve_radius,
        depth=sleeve_length,
        vertices=12,
        location=(body_width/2 + sleeve_length/2, 0, body_length * 0.75)
    )
    right_sleeve = bpy.context.active_object
    right_sleeve.name = "right_sleeve"
    right_sleeve.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    
    # Left sleeve
    bpy.ops.mesh.primitive_cylinder_add(
        radius=sleeve_radius,
        depth=sleeve_length,
        vertices=12,
        location=(-body_width/2 - sleeve_length/2, 0, body_length * 0.75)
    )
    left_sleeve = bpy.context.active_object
    left_sleeve.name = "left_sleeve"
    left_sleeve.rotation_euler = (0, math.radians(-90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    
    # Use Boolean union to properly merge sleeves with body
    # Right sleeve union
    bool_right = body.modifiers.new(name="Union_Right", type='BOOLEAN')
    bool_right.operation = 'UNION'
    bool_right.object = right_sleeve
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=bool_right.name)
    bpy.data.objects.remove(right_sleeve, do_unlink=True)
    
    # Left sleeve union
    bool_left = body.modifiers.new(name="Union_Left", type='BOOLEAN')
    bool_left.operation = 'UNION'
    bool_left.object = left_sleeve
    bpy.ops.object.modifier_apply(modifier=bool_left.name)
    bpy.data.objects.remove(left_sleeve, do_unlink=True)
    
    tshirt = body
    tshirt.name = "tshirt"
    
    # Boolean subtract neck hole
    bool_mod = tshirt.modifiers.new(name="Neck", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = neck_cut
    bpy.context.view_layer.objects.active = tshirt
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    
    # Delete the cutter
    bpy.data.objects.remove(neck_cut, do_unlink=True)
    
    # Clean up mesh
    bpy.context.view_layer.objects.active = tshirt
    tshirt.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Add subdivision for smoothness
    subsurf = tshirt.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2
    bpy.ops.object.modifier_apply(modifier=subsurf.name)
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    return tshirt


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
    print(f"Exported: {filepath}")


def main():
    print("=" * 50)
    print("MIRAAA T-Shirt 3D Assembly v3")
    print("=" * 50)
    
    clear_scene()
    
    print("\nCreating T-shirt with proper sleeves...")
    tshirt = create_tshirt_simple()
    
    # Add material
    mat = create_material(color=(0.15, 0.15, 0.15, 1.0))
    tshirt.data.materials.append(mat)
    
    print(f"\nFinal T-shirt: {len(tshirt.data.vertices)} vertices, {len(tshirt.data.polygons)} faces")
    print(f"Dimensions: {tshirt.dimensions}")
    
    export_glb(tshirt, OUTPUT_PATH)
    
    print("\n" + "=" * 50)
    print("T-SHIRT COMPLETE!")
    print("=" * 50)


if __name__ == "__main__":
    main()
