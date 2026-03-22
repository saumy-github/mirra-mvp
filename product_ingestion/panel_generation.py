"""Canonical Step 2 panel generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from garment_measurements import GarmentMeasurements
from panels import DynamicPatternGenerator

from panel_export_dxf import export_panels_dxf
from panel_export_svg import export_panels_svg


@dataclass
class PanelGenerationResult:
    """Paths and metadata for generated panel outputs."""

    panels_dir: Path
    dxf_dir: Path
    svg_dir: Path
    metadata_path: Path
    panel_names: list[str]


def write_panel_metadata(generator: DynamicPatternGenerator, output_path: Path) -> Path:
    """Write canonical panel metadata at the app layer."""
    metadata = {
        "garment_type": "tshirt",
        "version": "2.0",
        "generation_type": "measurement-driven",
        "body_measurements": {
            "height_cm": generator.m.body_height,
            "chest_circumference_cm": generator.m.body_chest,
            "shoulder_width_cm": generator.m.body_shoulder,
        },
        "garment_measurements": {
            "half_chest_width": generator.m.half_chest_width,
            "garment_length": generator.m.garment_length,
            "shoulder_width": generator.m.shoulder_width,
            "neck_width": generator.m.neck_width,
            "sleeve_length": generator.m.sleeve_length,
            "bicep_width": generator.m.bicep_width,
            "armhole_depth": generator.m.armhole_depth,
            "seam_allowance": generator.m.seam_allowance,
        },
        "fit_details": {
            "fit_type": generator.m.fit_type,
            "ease_cm": generator.m.ease_cm,
        },
        "panel_info": {
            "coordinates": "seam_line",
            "seam_allowances_included": True,
            "seam_allowance_cm": generator.m.seam_allowance,
            "notes": "Panels are generated at seam line with seam allowances documented below.",
        },
        "seam_allowance_specifications": {
            "front_panel": {
                "bottom_edge": {"allowance_cm": 3.0, "type": "hem", "notes": "Double fold hem"},
                "side_seams": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both left and right sides"},
                "shoulder_seams": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both shoulders"},
                "armholes": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both armhole curves"},
                "neckline": {"allowance_cm": 0.5, "type": "binding", "notes": "Binding or ribbing applied"},
            },
            "back_panel": {
                "bottom_edge": {"allowance_cm": 3.0, "type": "hem", "notes": "Double fold hem"},
                "side_seams": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both left and right sides"},
                "shoulder_seams": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both shoulders"},
                "armholes": {"allowance_cm": 1.0, "type": "sewing", "notes": "Both armhole curves"},
                "neckline": {"allowance_cm": 0.5, "type": "binding", "notes": "Binding or ribbing applied"},
            },
            "sleeves": {
                "cuff_edge": {"allowance_cm": 2.0, "type": "hem", "notes": "Single or double fold"},
                "underarm_seam": {"allowance_cm": 1.0, "type": "sewing", "notes": "Sleeve seam"},
                "sleeve_cap": {"allowance_cm": 1.5, "type": "sewing", "notes": "Extra ease for setting into armhole"},
            },
        },
        "panel_pieces": list(generator.patterns.keys()),
        "seam_matching": {
            "armhole_length_cm": (generator.front_armhole_length + generator.back_armhole_length) / 2,
            "sleeve_cap_length_cm": generator.sleeve_cap_length,
            "ease_cm": generator.sleeve_cap_length - ((generator.front_armhole_length + generator.back_armhole_length) / 2),
            "status": "matched"
            if abs(generator.sleeve_cap_length - ((generator.front_armhole_length + generator.back_armhole_length) / 2)) <= 2.0
            else "mismatched",
        },
        "seam_connections": [
            {"type": "shoulder", "from": "front_panel", "to": "back_panel", "side": "left"},
            {"type": "shoulder", "from": "front_panel", "to": "back_panel", "side": "right"},
            {"type": "side_seam", "from": "front_panel", "to": "back_panel", "side": "left"},
            {"type": "side_seam", "from": "front_panel", "to": "back_panel", "side": "right"},
            {"type": "armhole", "from": "sleeve_left", "to": "front_panel+back_panel", "side": "left"},
            {"type": "armhole", "from": "sleeve_right", "to": "front_panel+back_panel", "side": "right"},
            {"type": "sleeve_seam", "from": "sleeve_left", "to": "sleeve_left"},
            {"type": "sleeve_seam", "from": "sleeve_right", "to": "sleeve_right"},
        ],
        "clo_import_notes": [
            "Panels are at seam line and are intended for CLO DXF import.",
            "CLO uses pattern terminology at the import boundary.",
            "Front and back shoulder lengths should match.",
            "Armhole curves should match sleeve cap circumference.",
        ],
    }

    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"  Wrote panel metadata: {output_path.name}")
    return output_path


def generate_panels(measurements: GarmentMeasurements, panels_dir: Path) -> PanelGenerationResult:
    """Generate panels and export DXF/SVG artifacts into the canonical layout."""
    panels_dir.mkdir(parents=True, exist_ok=True)
    dxf_dir = panels_dir / "dxf"
    svg_dir = panels_dir / "svg"
    dxf_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)

    generator = DynamicPatternGenerator(measurements)
    generator.patterns["front_panel"] = generator.generate_front_panel()
    generator.patterns["back_panel"] = generator.generate_back_panel()

    total_armhole = generator.front_armhole_length + generator.back_armhole_length
    armhole_per_sleeve = total_armhole / 2
    generator.patterns["sleeve_left"] = generator.generate_sleeve(target_armhole_length=armhole_per_sleeve)
    generator.patterns["sleeve_right"] = generator.generate_sleeve(target_armhole_length=armhole_per_sleeve)

    export_panels_dxf(generator.patterns, generator.m, dxf_dir)
    export_panels_svg(generator.patterns, svg_dir)
    metadata_path = write_panel_metadata(generator, panels_dir / "panel_metadata.json")

    return PanelGenerationResult(
        panels_dir=panels_dir,
        dxf_dir=dxf_dir,
        svg_dir=svg_dir,
        metadata_path=metadata_path,
        panel_names=list(generator.patterns.keys()),
    )
