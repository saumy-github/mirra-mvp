"""
Step 5: Garment Assembly

Blender integration with GarmentTool addon for:
- Importing pattern pieces
- Defining stitch/seam connections
- Running cloth simulation
- Exporting final 3D mesh (GLB)

This module can be run as a Blender script or used as a library.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import sys
sys.path.append('..')
from config.pipeline_config import (
    GarmentAssemblyConfig, 
    StitchDefinition, 
    SimulationConfig
)


class StitchType(Enum):
    """Types of stitches for garment assembly"""
    SIDE_SEAM = "side_seam"
    SHOULDER = "shoulder"
    ARMHOLE = "armhole"
    NECK = "neck"
    HEM = "hem"


@dataclass
class EdgeDefinition:
    """Defines an edge on a pattern piece for stitching"""
    piece_name: str
    edge_name: str
    vertex_indices: List[int] = field(default_factory=list)
    
    
@dataclass
class SeamConnection:
    """Defines a seam connection between two edges"""
    stitch_type: StitchType
    edge_a: EdgeDefinition
    edge_b: EdgeDefinition
    stitch_spacing: float = 0.5  # cm
    stitch_strength: float = 1.0


@dataclass
class ClothSettings:
    """Cloth simulation settings for Blender"""
    quality: int = 5
    mass: float = 0.3  # kg/m²
    air_damping: float = 1.0
    bending_stiffness: float = 0.5
    tension_stiffness: float = 15.0
    compression_stiffness: float = 15.0
    shear_stiffness: float = 5.0
    
    # Collision settings
    collision_quality: int = 2
    collision_distance: float = 0.015
    self_collision: bool = False
    self_collision_distance: float = 0.015


class BlenderGarmentAssembler:
    """
    Handles garment assembly in Blender using GarmentTool addon.
    
    This class generates Blender Python scripts that can be executed
    within Blender to perform the assembly and simulation.
    """
    
    def __init__(self, config: Optional[GarmentAssemblyConfig] = None):
        self.config = config or GarmentAssemblyConfig()
        self.seams: List[SeamConnection] = []
        self.cloth_settings = ClothSettings()
        
    def setup_seams_from_config(self):
        """Setup seam connections from configuration."""
        for stitch in self.config.stitches:
            self.add_seam(
                stitch_type=StitchType(stitch.stitch_type),
                from_piece=stitch.from_piece,
                from_edge=stitch.from_edge,
                to_piece=stitch.to_piece,
                to_edge=stitch.to_edge
            )
    
    def add_seam(
        self,
        stitch_type: StitchType,
        from_piece: str,
        from_edge: str,
        to_piece: str,
        to_edge: str,
        spacing: float = 0.5,
        strength: float = 1.0
    ):
        """Add a seam connection between two edges."""
        seam = SeamConnection(
            stitch_type=stitch_type,
            edge_a=EdgeDefinition(piece_name=from_piece, edge_name=from_edge),
            edge_b=EdgeDefinition(piece_name=to_piece, edge_name=to_edge),
            stitch_spacing=spacing,
            stitch_strength=strength
        )
        self.seams.append(seam)
    
    def generate_blender_script(
        self,
        pattern_directory: str,
        output_path: str,
        output_format: str = "GLB"
    ) -> str:
        """
        Generate a Blender Python script for garment assembly.
        
        Args:
            pattern_directory: Directory containing SVG pattern files
            output_path: Path for the output 3D mesh
            output_format: Output format (GLB, FBX, OBJ)
            
        Returns:
            The generated Python script as a string
        """
        # Pre-generate the seams JSON
        seams_data = [
            {
                "type": seam.stitch_type.value,
                "from_piece": seam.edge_a.piece_name,
                "from_edge": seam.edge_a.edge_name,
                "to_piece": seam.edge_b.piece_name,
                "to_edge": seam.edge_b.edge_name,
                "spacing": seam.stitch_spacing,
                "strength": seam.stitch_strength
            }
            for seam in self.seams
        ]
        seams_json = json.dumps(seams_data, indent=4)
        
        # Cloth settings dict - use Python bool representation
        cloth_dict = {
            "quality": self.cloth_settings.quality,
            "mass": self.cloth_settings.mass,
            "air_damping": self.cloth_settings.air_damping,
            "bending_stiffness": self.cloth_settings.bending_stiffness,
            "tension_stiffness": self.cloth_settings.tension_stiffness,
            "compression_stiffness": self.cloth_settings.compression_stiffness,
            "shear_stiffness": self.cloth_settings.shear_stiffness,
            "self_collision": self.cloth_settings.self_collision,
        }
        # Convert to Python code format (True/False instead of true/false)
        cloth_json = json.dumps(cloth_dict, indent=4).replace('true', 'True').replace('false', 'False')
        
        script = f'''"""
MIRAAA Pipeline - Blender Garment Assembly Script
Auto-generated script for garment assembly with GarmentTool

Run this script in Blender:
    blender --background --python garment_assemble.py
"""

import bpy
import os
import math
from pathlib import Path

# Configuration
PATTERN_DIR = r"{pattern_directory}"
OUTPUT_PATH = r"{output_path}"
OUTPUT_FORMAT = "{output_format}"

# Pattern pieces to import
PATTERN_PIECES = [
    "front_bodice",
    "back_bodice", 
    "sleeve",
    "neck_band"
]

# Seam definitions
SEAMS = {seams_json}

# Cloth simulation settings
CLOTH_SETTINGS = {cloth_json}

FRAME_START = {self.config.simulation.frame_start}
FRAME_END = {self.config.simulation.frame_end}


def clear_scene():
    """Clear the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Also remove any imported collections
    for col in bpy.data.collections:
        if col.name != 'Scene Collection':
            bpy.data.collections.remove(col)


def import_svg_pattern(svg_path: str, name: str) -> bpy.types.Object:
    """Import an SVG file and convert to mesh with proper faces."""
    # Store existing objects before import
    existing_objects = set(bpy.data.objects.keys())
    
    # Import SVG
    bpy.ops.import_curve.svg(filepath=svg_path)
    
    # Find newly imported objects
    new_objects = [obj for obj in bpy.data.objects if obj.name not in existing_objects]
    
    if not new_objects:
        print(f"Warning: No objects imported from {{svg_path}}")
        return None
    
    # Select all new curve objects
    bpy.ops.object.select_all(action='DESELECT')
    curve_objects = []
    for obj in new_objects:
        if obj.type == 'CURVE':
            obj.select_set(True)
            curve_objects.append(obj)
    
    if not curve_objects:
        print(f"Warning: No curve objects found in {{svg_path}}")
        return None
    
    # Set the first selected as active
    bpy.context.view_layer.objects.active = curve_objects[0]
    
    # Join all curves into one if multiple
    if len(curve_objects) > 1:
        bpy.ops.object.join()
    
    curve_obj = bpy.context.active_object
    curve_obj.name = name + "_curve"
    
    # Set curve to 2D and filled
    curve_obj.data.dimensions = '2D'
    curve_obj.data.fill_mode = 'BOTH'
    
    # Give it slight extrusion to make it visible
    curve_obj.data.extrude = 0.01  # 1cm thickness
    
    # Convert curve to mesh
    bpy.ops.object.convert(target='MESH')
    
    # Get mesh object
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    
    # Scale UP by 10 - Blender SVG import scales down significantly
    # This makes garment ~70cm wide which is realistic for a t-shirt
    mesh_obj.scale = (10, 10, 10)
    bpy.ops.object.transform_apply(scale=True)
    
    # Add a basic material so it's visible
    mat = bpy.data.materials.new(name=f"{{name}}_material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)  # Light gray
    mesh_obj.data.materials.append(mat)
    
    print(f"Imported {{name}}: {{len(mesh_obj.data.vertices)}} vertices, {{len(mesh_obj.data.polygons)}} faces, dimensions: {{mesh_obj.dimensions}}")
    
    return mesh_obj


def position_pattern_pieces(pieces: dict):
    """Position pattern pieces in 3D space for assembly."""
    
    # Front bodice - centered, facing forward
    if "front_bodice" in pieces and pieces["front_bodice"] is not None:
        obj = pieces["front_bodice"]
        obj.location = (0, 0.5, 0)
        obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Back bodice - behind front
    if "back_bodice" in pieces and pieces["back_bodice"] is not None:
        obj = pieces["back_bodice"]
        obj.location = (0, -0.5, 0)
        obj.rotation_euler = (math.radians(90), 0, math.radians(180))
    
    # Sleeves
    if "sleeve" in pieces and pieces["sleeve"] is not None:
        obj = pieces["sleeve"]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Create a copy for the right sleeve
        bpy.ops.object.duplicate()
        right_sleeve = bpy.context.active_object
        right_sleeve.name = "sleeve_right"
        pieces["sleeve_right"] = right_sleeve
        
        # Position sleeves
        obj.name = "sleeve_left"
        obj.location = (-1.5, 0, 0)
        obj.rotation_euler = (math.radians(90), 0, math.radians(90))
        
        right_sleeve.location = (1.5, 0, 0)
        right_sleeve.rotation_euler = (math.radians(90), 0, math.radians(-90))
    
    # Neck band
    if "neck_band" in pieces and pieces["neck_band"] is not None:
        obj = pieces["neck_band"]
        obj.location = (0, 0, 1.5)
        obj.rotation_euler = (0, 0, 0)


def setup_cloth_simulation(obj: bpy.types.Object):
    """Add cloth simulation modifier to an object."""
    if obj is None:
        print("Warning: Cannot setup cloth on None object")
        return
    
    if obj.type != 'MESH':
        print(f"Warning: Object {{obj.name}} is not a mesh, skipping cloth")
        return
    
    # Make sure object is active and selected
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Add cloth modifier
    cloth_mod = obj.modifiers.new(name="Cloth", type='CLOTH')
    
    if cloth_mod is None:
        print(f"Warning: Could not create cloth modifier for {{obj.name}}")
        return
    
    cloth = cloth_mod.settings
    
    # Apply settings
    cloth.quality = CLOTH_SETTINGS["quality"]
    cloth.mass = CLOTH_SETTINGS["mass"]
    cloth.air_damping = CLOTH_SETTINGS["air_damping"]
    
    # Stiffness
    cloth.tension_stiffness = CLOTH_SETTINGS["tension_stiffness"]
    cloth.compression_stiffness = CLOTH_SETTINGS["compression_stiffness"]
    cloth.shear_stiffness = CLOTH_SETTINGS["shear_stiffness"]
    cloth.bending_stiffness = CLOTH_SETTINGS["bending_stiffness"]
    
    # Collision settings
    cloth_mod.collision_settings.use_self_collision = CLOTH_SETTINGS["self_collision"]


def create_sewing_springs(pieces: dict):
    """
    Create sewing springs between pattern pieces.
    Uses vertex groups to define seam edges.
    """
    for seam in SEAMS:
        from_piece = seam["from_piece"]
        to_piece = seam["to_piece"]
        
        # Handle combined pieces (e.g., "front_bodice + back_bodice")
        if "+" in to_piece:
            # This would require more complex handling
            # For now, we'll create springs to the primary piece
            to_piece = to_piece.split("+")[0].strip()
        
        if from_piece in pieces and to_piece in pieces:
            create_spring_constraint(
                pieces[from_piece],
                pieces[to_piece],
                seam["from_edge"],
                seam["to_edge"]
            )


def create_spring_constraint(obj_a, obj_b, edge_a, edge_b):
    """Create spring constraints between two edges."""
    # This is a simplified version - GarmentTool provides better sewing
    # For production, use the GarmentTool addon's sewing features
    
    # Create an empty to parent both objects for simulation
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    empty = bpy.context.active_object
    empty.name = f"seam_{{obj_a.name}}_to_{{obj_b.name}}"
    
    # In a real implementation, you would:
    # 1. Identify matching vertices on both edges
    # 2. Create sewing springs between corresponding vertices
    # 3. Use GarmentTool's sewing functionality
    
    print(f"Created seam: {{obj_a.name}}.{{edge_a}} -> {{obj_b.name}}.{{edge_b}}")


def bake_simulation():
    """Bake the cloth simulation."""
    bpy.context.scene.frame_start = FRAME_START
    bpy.context.scene.frame_end = FRAME_END
    
    # Bake all cloth simulations
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            if mod.type == 'CLOTH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.ptcache.bake_all(bake=True)
                break
    
    # Go to final frame
    bpy.context.scene.frame_set(FRAME_END)


def apply_modifiers_and_join(pieces: dict) -> bpy.types.Object:
    """Apply modifiers and join all pieces into single mesh."""
    
    # Select all pattern pieces
    bpy.ops.object.select_all(action='DESELECT')
    
    for name, obj in pieces.items():
        obj.select_set(True)
        
        # Apply cloth modifier
        bpy.context.view_layer.objects.active = obj
        for mod in obj.modifiers:
            if mod.type == 'CLOTH':
                bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # Join all pieces
    if pieces:
        first_piece = list(pieces.values())[0]
        bpy.context.view_layer.objects.active = first_piece
        bpy.ops.object.join()
        
        joined_obj = bpy.context.active_object
        joined_obj.name = "garment"
        return joined_obj
    
    return None


def export_mesh(obj: bpy.types.Object, output_path: str, format: str):
    """Export the final mesh."""
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    if format.upper() == "GLB":
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            use_selection=True,
            export_format='GLB'
        )
    elif format.upper() == "FBX":
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=True
        )
    elif format.upper() == "OBJ":
        bpy.ops.export_scene.obj(
            filepath=output_path,
            use_selection=True
        )
    
    print(f"Exported: {{output_path}}")


def main():
    """Main assembly pipeline."""
    print("Starting MIRAAA Garment Assembly...")
    
    # Clear scene
    clear_scene()
    
    # Import pattern pieces
    pieces = {{}}
    for piece_name in PATTERN_PIECES:
        svg_path = os.path.join(PATTERN_DIR, f"{{piece_name}}.svg")
        if os.path.exists(svg_path):
            print(f"Importing: {{piece_name}}")
            result = import_svg_pattern(svg_path, piece_name)
            if result is not None:
                pieces[piece_name] = result
        else:
            print(f"Warning: {{svg_path}} not found")
    
    if not pieces:
        print("Error: No pattern pieces imported successfully")
        return
    
    # Filter out None values
    pieces = {{k: v for k, v in pieces.items() if v is not None}}
    
    # Position pieces
    position_pattern_pieces(pieces)
    
    # Setup cloth simulation
    for name, obj in pieces.items():
        if obj is not None:
            setup_cloth_simulation(obj)
    
    # Create sewing connections
    create_sewing_springs(pieces)
    
    # Run simulation
    print("Baking cloth simulation...")
    bake_simulation()
    
    # Finalize and export
    print("Finalizing mesh...")
    garment = apply_modifiers_and_join(pieces)
    
    if garment:
        export_mesh(garment, OUTPUT_PATH, OUTPUT_FORMAT)
        print("Assembly complete!")
    else:
        print("Error: No garment mesh created")


if __name__ == "__main__":
    main()
'''
        return script
    
    def save_assembly_script(
        self,
        pattern_directory: str,
        output_directory: str,
        output_name: str = "garment"
    ) -> str:
        """
        Save the Blender assembly script to a file.
        
        Args:
            pattern_directory: Directory containing SVG patterns
            output_directory: Directory for output files
            output_name: Base name for output files
            
        Returns:
            Path to the saved script
        """
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_mesh_path = str(output_dir / f"{output_name}.glb")
        script_path = output_dir / f"{output_name}_assemble.py"
        
        script = self.generate_blender_script(
            pattern_directory=pattern_directory,
            output_path=output_mesh_path,
            output_format=self.config.output_format
        )
        
        with open(script_path, 'w') as f:
            f.write(script)
        
        print(f"Blender script saved: {script_path}")
        return str(script_path)
    
    def generate_garment_tool_json(
        self,
        pattern_directory: str,
        output_directory: str
    ) -> str:
        """
        Generate a JSON configuration file for GarmentTool addon.
        
        This can be imported directly into GarmentTool for assembly.
        """
        config = {
            "version": "1.0",
            "name": "MIRAAA Generated Garment",
            "patterns": {
                "directory": pattern_directory,
                "pieces": [
                    {"name": "front_bodice", "file": "front_bodice.svg"},
                    {"name": "back_bodice", "file": "back_bodice.svg"},
                    {"name": "sleeve", "file": "sleeve.svg", "mirror": True},
                    {"name": "neck_band", "file": "neck_band.svg"}
                ]
            },
            "seams": [
                {
                    "name": seam.stitch_type.value,
                    "from": {
                        "piece": seam.edge_a.piece_name,
                        "edge": seam.edge_a.edge_name
                    },
                    "to": {
                        "piece": seam.edge_b.piece_name,
                        "edge": seam.edge_b.edge_name
                    },
                    "properties": {
                        "spacing": seam.stitch_spacing,
                        "strength": seam.stitch_strength
                    }
                }
                for seam in self.seams
            ],
            "simulation": {
                "enabled": self.config.simulation.cloth_enabled,
                "frames": {
                    "start": self.config.simulation.frame_start,
                    "end": self.config.simulation.frame_end
                },
                "cloth": {
                    "quality": self.cloth_settings.quality,
                    "mass": self.cloth_settings.mass,
                    "stiffness": {
                        "tension": self.cloth_settings.tension_stiffness,
                        "compression": self.cloth_settings.compression_stiffness,
                        "shear": self.cloth_settings.shear_stiffness,
                        "bending": self.cloth_settings.bending_stiffness
                    }
                },
                "self_collision": self.config.simulation.self_collision_enabled
            },
            "export": {
                "format": self.config.output_format,
                "directory": output_directory
            }
        }
        
        output_path = Path(output_directory) / "garment_config.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"GarmentTool config saved: {output_path}")
        return str(output_path)


def assemble_garment(
    pattern_directory: str,
    output_directory: str,
    config: Optional[GarmentAssemblyConfig] = None
) -> Dict[str, str]:
    """
    Convenience function for garment assembly.
    
    Args:
        pattern_directory: Directory containing SVG patterns
        output_directory: Directory for output files
        config: Optional assembly configuration
        
    Returns:
        Dictionary with paths to generated files
    """
    assembler = BlenderGarmentAssembler(config)
    assembler.setup_seams_from_config()
    
    # Generate outputs
    script_path = assembler.save_assembly_script(
        pattern_directory=pattern_directory,
        output_directory=output_directory,
        output_name="garment"
    )
    
    config_path = assembler.generate_garment_tool_json(
        pattern_directory=pattern_directory,
        output_directory=output_directory
    )
    
    return {
        "blender_script": script_path,
        "garment_tool_config": config_path,
        "expected_output": os.path.join(output_directory, "garment.glb")
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate garment assembly files")
    parser.add_argument(
        "pattern_dir",
        help="Directory containing SVG pattern files"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory",
        default="assembly_output"
    )
    
    args = parser.parse_args()
    
    result = assemble_garment(
        pattern_directory=args.pattern_dir,
        output_directory=args.output
    )
    
    print("\nGenerated files:")
    for key, path in result.items():
        print(f"  {key}: {path}")
    
    print(f"\nTo run the assembly in Blender:")
    print(f"  blender --background --python {result['blender_script']}")
