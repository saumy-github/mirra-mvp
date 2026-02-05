"""
MIRAAA Pipeline - Main Orchestrator

Complete pipeline for garment design automation:
1. Image Segmentation
2. Design/Print Extraction  
3. Fabric Color Extraction
4. Pattern Generation
5. Garment Assembly (Blender)

All measurements in centimeters (cm).
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from config import (
    PipelineConfig,
    Measurements,
    DEFAULT_CONFIG
)

from steps import (
    # Step 1
    GarmentSegmentor,
    segment_image,
    save_mask,
    
    # Step 2
    DesignExtractor,
    
    # Step 3
    FabricColorExtractor,
    
    # Step 4
    PatternGenerator,
    SVGExporter,
    
    # Step 5
    BlenderGarmentAssembler,
    assemble_garment
)


@dataclass
class PipelineResult:
    """Complete result from the MIRAAA pipeline"""
    success: bool
    message: str
    
    # Step results
    segmentation_valid: bool = False
    has_design: bool = False
    primary_color_hex: str = ""
    pattern_pieces_count: int = 0
    
    # Output paths
    output_directory: str = ""
    mask_path: str = ""
    fabric_mask_path: str = ""
    design_mask_path: str = ""
    colors_json_path: str = ""
    pattern_directory: str = ""
    blender_script_path: str = ""
    garment_config_path: str = ""
    
    # Timing
    total_time_seconds: float = 0.0
    step_times: Dict[str, float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MIRAAPipeline:
    """
    Main MIRAAA Pipeline orchestrator.
    
    Coordinates all 5 steps of the garment design automation pipeline.
    """
    
    VERSION = "2.0"
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.step_times = {}
        
    def run(
        self,
        image_path: str = "/Users/tanujsharma/Desktop/mirra-mvp/2D_to_3D_tshirt/minimal_pipeline/input_images/front.png",
        output_directory: str = "output",
        skip_assembly: bool = False
    ) -> PipelineResult:
        """
        Run the complete MIRAAA pipeline.
        
        Args:
            image_path: Path to the input garment image
            output_directory: Directory for all output files
            skip_assembly: Skip Blender assembly step (for testing)
            
        Returns:
            PipelineResult with all outputs and metadata
        """
        start_time = time.time()
        
        # Setup output directory
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = PipelineResult(
            success=False,
            message="Pipeline started",
            output_directory=str(output_dir),
            step_times={}
        )
        
        try:
            # ========================================
            # STEP 1: Segmentation
            # ========================================
            print("\n" + "="*50)
            print("STEP 1: Image Segmentation")
            print("="*50)
            
            step_start = time.time()
            
            seg_result = segment_image(
                image_path, 
                self.config.segmentation
            )
            
            self.step_times["segmentation"] = time.time() - step_start
            result.segmentation_valid = seg_result.is_valid
            
            if not seg_result.is_valid:
                result.message = f"Segmentation failed: {seg_result.validation_message}"
                return self._finalize_result(result, start_time)
            
            # Save mask
            mask_path = output_dir / "segmentation_mask.png"
            save_mask(seg_result.mask, str(mask_path))
            result.mask_path = str(mask_path)
            
            print(f"  ✓ Segmentation complete. Area: {seg_result.area_percent:.1f}%")
            
            # ========================================
            # STEP 2: Design Extraction
            # ========================================
            print("\n" + "="*50)
            print("STEP 2: Design/Print Extraction")
            print("="*50)
            
            step_start = time.time()
            
            design_extractor = DesignExtractor(self.config.design_extraction)
            design_result = design_extractor.extract(
                seg_result.original_image,
                seg_result.mask
            )
            
            self.step_times["design_extraction"] = time.time() - step_start
            result.has_design = design_result.has_design
            
            # Save masks
            import cv2
            fabric_mask_path = output_dir / "fabric_mask.png"
            design_mask_path = output_dir / "design_mask.png"
            
            cv2.imwrite(str(fabric_mask_path), design_result.fabric_mask)
            cv2.imwrite(str(design_mask_path), design_result.design_mask)
            
            result.fabric_mask_path = str(fabric_mask_path)
            result.design_mask_path = str(design_mask_path)
            
            print(f"  ✓ Design extraction complete.")
            print(f"    Has design: {design_result.has_design}")
            print(f"    Design coverage: {design_result.design_coverage_percent:.1f}%")
            
            # ========================================
            # STEP 3: Color Extraction
            # ========================================
            print("\n" + "="*50)
            print("STEP 3: Fabric Color Extraction")
            print("="*50)
            
            step_start = time.time()
            
            color_extractor = FabricColorExtractor(self.config.color_extraction)
            color_result = color_extractor.extract(
                seg_result.original_image,
                design_result.fabric_mask
            )
            
            self.step_times["color_extraction"] = time.time() - step_start
            
            if color_result.success:
                result.primary_color_hex = color_result.primary_color.hex_code
                
                # Save color data
                colors_path = output_dir / "colors.json"
                colors_data = {
                    "primary_color": color_result.primary_color.to_dict(),
                    "all_colors": [c.to_dict() for c in color_result.all_colors]
                }
                with open(colors_path, 'w') as f:
                    json.dump(colors_data, f, indent=2)
                result.colors_json_path = str(colors_path)
                
                # Save palette visualization
                palette = color_extractor.create_color_palette(color_result)
                cv2.imwrite(
                    str(output_dir / "color_palette.png"),
                    cv2.cvtColor(palette, cv2.COLOR_RGB2BGR)
                )
                
                print(f"  ✓ Color extraction complete.")
                print(f"    Primary color: {color_result.primary_color.hex_code}")
                print(f"    RGB: {color_result.primary_color.rgb}")
            else:
                print(f"  ⚠ Color extraction failed: {color_result.message}")
            
            # ========================================
            # STEP 4: Pattern Generation
            # ========================================
            print("\n" + "="*50)
            print("STEP 4: Pattern Generation")
            print("="*50)
            
            step_start = time.time()
            
            pattern_dir = output_dir / "patterns"
            pattern_dir.mkdir(exist_ok=True)
            
            pattern_generator = PatternGenerator(self.config.pattern_generation)
            pattern_set = pattern_generator.generate_all_pieces()
            
            # Export to SVG
            exporter = SVGExporter(str(pattern_dir))
            exported_paths = exporter.export_all(pattern_set)
            
            self.step_times["pattern_generation"] = time.time() - step_start
            
            result.pattern_pieces_count = len(pattern_set.pieces)
            result.pattern_directory = str(pattern_dir)
            
            print(f"  ✓ Pattern generation complete.")
            print(f"    Generated {len(pattern_set.pieces)} pattern pieces:")
            for name, piece in pattern_set.pieces.items():
                print(f"      - {name}: perimeter {piece.get_perimeter():.1f} cm")
            
            # ========================================
            # STEP 5: Garment Assembly
            # ========================================
            if not skip_assembly:
                print("\n" + "="*50)
                print("STEP 5: Garment Assembly (Blender)")
                print("="*50)
                
                step_start = time.time()
                
                assembly_dir = output_dir / "assembly"
                assembly_result = assemble_garment(
                    pattern_directory=str(pattern_dir),
                    output_directory=str(assembly_dir),
                    config=self.config.garment_assembly
                )
                
                self.step_times["garment_assembly"] = time.time() - step_start
                
                result.blender_script_path = assembly_result["blender_script"]
                result.garment_config_path = assembly_result["garment_tool_config"]
                
                print(f"  ✓ Assembly files generated.")
                print(f"    Blender script: {result.blender_script_path}")
                print(f"    GarmentTool config: {result.garment_config_path}")
                print(f"\n  To run in Blender:")
                print(f"    blender --background --python {result.blender_script_path}")
            else:
                print("\n  ⏭ Skipping Blender assembly step")
            
            # ========================================
            # Complete
            # ========================================
            result.success = True
            result.message = "Pipeline completed successfully"
            
        except Exception as e:
            result.success = False
            result.message = f"Pipeline error: {str(e)}"
            import traceback
            traceback.print_exc()
        
        return self._finalize_result(result, start_time)
    
    def _finalize_result(
        self, 
        result: PipelineResult, 
        start_time: float
    ) -> PipelineResult:
        """Finalize the result with timing information."""
        result.total_time_seconds = time.time() - start_time
        result.step_times = self.step_times.copy()
        
        # Save result summary
        if result.output_directory:
            summary_path = Path(result.output_directory) / "pipeline_result.json"
            with open(summary_path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*50)
        print("PIPELINE SUMMARY")
        print("="*50)
        print(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
        print(f"Message: {result.message}")
        print(f"Total time: {result.total_time_seconds:.2f}s")
        
        if result.step_times:
            print("\nStep timings:")
            for step, duration in result.step_times.items():
                print(f"  {step}: {duration:.2f}s")
        
        return result
    
    def run_pattern_only(
        self,
        output_directory: str = "output",
        custom_measurements: Optional[Dict[str, float]] = None
    ) -> PipelineResult:
        """
        Run only pattern generation (Steps 4-5).
        
        Useful when you already have measurements and just want patterns.
        
        Args:
            output_directory: Directory for output files
            custom_measurements: Optional dict of custom measurements
            
        Returns:
            PipelineResult with pattern outputs
        """
        start_time = time.time()
        
        # Update measurements if provided
        if custom_measurements:
            self.config.update_measurements(**custom_measurements)
        
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = PipelineResult(
            success=False,
            message="Pattern generation started",
            output_directory=str(output_dir),
            step_times={}
        )
        
        try:
            # Pattern Generation
            step_start = time.time()
            
            pattern_dir = output_dir / "patterns"
            pattern_generator = PatternGenerator(self.config.pattern_generation)
            pattern_set = pattern_generator.generate_all_pieces()
            
            exporter = SVGExporter(str(pattern_dir))
            exporter.export_all(pattern_set)
            
            self.step_times["pattern_generation"] = time.time() - step_start
            
            result.pattern_pieces_count = len(pattern_set.pieces)
            result.pattern_directory = str(pattern_dir)
            
            # Assembly files
            step_start = time.time()
            
            assembly_dir = output_dir / "assembly"
            assembly_result = assemble_garment(
                pattern_directory=str(pattern_dir),
                output_directory=str(assembly_dir),
                config=self.config.garment_assembly
            )
            
            self.step_times["garment_assembly"] = time.time() - step_start
            
            result.blender_script_path = assembly_result["blender_script"]
            result.garment_config_path = assembly_result["garment_tool_config"]
            
            result.success = True
            result.message = "Pattern generation completed"
            
        except Exception as e:
            result.message = f"Error: {str(e)}"
        
        return self._finalize_result(result, start_time)


def run_pipeline(
    image_path: str = "/Users/tanujsharma/Desktop/mirra-mvp/2D_to_3D_tshirt/minimal_pipeline/input_images/front.png",
    output_directory: str = "output",
    config: Optional[PipelineConfig] = None,
    skip_assembly: bool = False
) -> PipelineResult:
    """
    Convenience function to run the complete pipeline.
    
    Args:
        image_path: Path to input garment image
        output_directory: Directory for outputs
        config: Optional pipeline configuration
        skip_assembly: Skip Blender assembly step
        
    Returns:
        PipelineResult
    """
    pipeline = MIRAAPipeline(config)
    return pipeline.run(
        image_path=image_path,
        output_directory=output_directory,
        skip_assembly=skip_assembly
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MIRAAA Pipeline - Garment Design Automation"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input image path (optional for pattern-only mode)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory",
        default="output"
    )
    parser.add_argument(
        "--pattern-only",
        action="store_true",
        help="Generate patterns only (no image processing)"
    )
    parser.add_argument(
        "--skip-assembly",
        action="store_true",
        help="Skip Blender assembly step"
    )
    parser.add_argument(
        "--chest",
        type=float,
        help="Half chest width in cm"
    )
    parser.add_argument(
        "--length",
        type=float,
        help="Garment length in cm"
    )
    parser.add_argument(
        "--shoulder",
        type=float,
        help="Shoulder width in cm"
    )
    
    args = parser.parse_args()
    
    # Create config with custom measurements
    config = PipelineConfig()
    
    custom_measurements = {}
    if args.chest:
        custom_measurements['half_chest_width'] = args.chest
    if args.length:
        custom_measurements['garment_length'] = args.length
    if args.shoulder:
        custom_measurements['shoulder_width'] = args.shoulder
    
    if custom_measurements:
        config.update_measurements(**custom_measurements)
    
    # Run pipeline
    pipeline = MIRAAPipeline(config)
    
    if args.pattern_only:
        result = pipeline.run_pattern_only(
            output_directory=args.output,
            custom_measurements=custom_measurements
        )
    else:
        if not args.input:
            parser.error("Input image path is required (unless using --pattern-only)")
        
        result = pipeline.run(
            image_path=args.input,
            output_directory=args.output,
            skip_assembly=args.skip_assembly
        )
    
    # Exit with appropriate code
    exit(0 if result.success else 1)
