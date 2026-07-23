"""Canonical Step 2 panel generation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

try:
    from .garment_measurements import GarmentMeasurements
    from .panels import DynamicPatternGenerator
    from .panel_export_dxf import export_panels_dxf
    from .panel_export_svg import export_panels_svg
except ImportError:
    from garment_measurements import GarmentMeasurements  # type: ignore
    from panels import DynamicPatternGenerator  # type: ignore
    from panel_export_dxf import export_panels_dxf  # type: ignore
    from panel_export_svg import export_panels_svg  # type: ignore


@dataclass
class PanelGenerationResult:
    """Paths and metadata for generated panel outputs."""

    panels_dir: Path
    dxf_dir: Path
    svg_dir: Path
    metadata_path: Path
    manifest_path: Path
    panel_names: list[str]
    layouts: dict = None   # piece_name → PieceLayout; used by texture_projection


def write_edge_manifest(generator: DynamicPatternGenerator, output_path: Path) -> Path:
    """Write edge_manifest.json — maps each piece's named edges to CLO indices.

    The manifest is used by the VTO seam builder to wire seams by name rather
    than by hardcoded integer indices.  Whenever the DXF geometry changes
    (new curve type, edge split/merge) only the manifest needs updating, not
    seams.py.
    """
    manifest: dict[str, list[dict]] = {}
    for piece_name, layout in generator.layouts.items():
        manifest[piece_name] = layout.edge_manifest()

    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Wrote edge manifest: {output_path.name}")
    return output_path


def write_panel_metadata(generator: DynamicPatternGenerator, output_path: Path) -> Path:
    """Write canonical panel metadata JSON."""
    cfg = generator.cfg
    avg_armhole = (generator.front_armhole_length + generator.back_armhole_length) / 2
    actual_ease = generator.sleeve_cap_length - avg_armhole

    metadata = {
        "garment_type": "tshirt",
        "version": "3.0",
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
            "neck_depth_front": generator.m.neck_depth_front,
            "neck_depth_back": generator.m.neck_depth_back,
            "sleeve_length": generator.m.sleeve_length,
            "bicep_width": generator.m.bicep_width,
            "armhole_depth": generator.m.armhole_depth,
            "seam_allowance": generator.m.seam_allowance,
        },
        "fit_details": {
            "fit_type": generator.m.fit_type,
            "ease_cm": generator.m.ease_cm,
        },
        "curve_config": {
            "cap_ease_cm": cfg.cap_ease_cm,
            "cap_ease_tolerance_cm": cfg.cap_ease_tolerance_cm,
            "shoulder_crown_cm": cfg.shoulder_crown_cm,
            "side_waist_suppression_cm": cfg.side_waist_suppression_cm,
            "front_armhole": {
                "hollow_position_frac": cfg.front_armhole.hollow_position_frac,
                "hollow_depth_frac": cfg.front_armhole.hollow_depth_frac,
                "shoulder_flare_frac": cfg.front_armhole.shoulder_flare_frac,
            },
            "back_armhole": {
                "hollow_position_frac": cfg.back_armhole.hollow_position_frac,
                "hollow_depth_frac": cfg.back_armhole.hollow_depth_frac,
                "shoulder_flare_frac": cfg.back_armhole.shoulder_flare_frac,
            },
        },
        "panel_info": {
            "coordinates": "seam_line",
            "seam_allowances_included": True,
            "seam_allowance_cm": generator.m.seam_allowance,
            "dxf_curve_entities": "SPLINE",
            "notes": (
                "Curved edges exported as DXF SPLINE entities (not POLYLINE). "
                "Each SPLINE entity = one CLO seam edge. "
                "Edge indices in edge_manifest.json match CLO 0-based edge numbering."
            ),
        },
        "seam_matching": {
            "front_armhole_cm": round(generator.front_armhole_length, 3),
            "back_armhole_cm": round(generator.back_armhole_length, 3),
            "avg_armhole_cm": round(avg_armhole, 3),
            "sleeve_cap_cm": round(generator.sleeve_cap_length, 3),
            "ease_cm": round(actual_ease, 3),
            "target_ease_cm": cfg.cap_ease_cm,
            "status": (
                "matched"
                if abs(actual_ease - cfg.cap_ease_cm) <= cfg.cap_ease_tolerance_cm * 2
                else "mismatched"
            ),
        },
        "seam_allowance_specifications": {
            "front_panel": {
                "bottom_edge": {"allowance_cm": 3.0, "type": "hem"},
                "side_seams": {"allowance_cm": 1.0, "type": "sewing"},
                "shoulder_seams": {"allowance_cm": 1.0, "type": "sewing"},
                "armholes": {"allowance_cm": 1.0, "type": "sewing"},
                "neckline": {"allowance_cm": 0.5, "type": "binding"},
            },
            "back_panel": {
                "bottom_edge": {"allowance_cm": 3.0, "type": "hem"},
                "side_seams": {"allowance_cm": 1.0, "type": "sewing"},
                "shoulder_seams": {"allowance_cm": 1.0, "type": "sewing"},
                "armholes": {"allowance_cm": 1.0, "type": "sewing"},
                "neckline": {"allowance_cm": 0.5, "type": "binding"},
            },
            "sleeves": {
                "cuff_edge": {"allowance_cm": 2.0, "type": "hem"},
                "underarm_seam": {"allowance_cm": 1.0, "type": "sewing"},
                "sleeve_cap": {"allowance_cm": 1.5, "type": "sewing"},
            },
        },
        "panel_pieces": list(generator.layouts.keys()),
        "seam_connections": [
            {"type": "shoulder",   "from": "front_panel", "to": "back_panel",  "side": "right", "front_edge": 3, "back_edge": 3},
            {"type": "shoulder",   "from": "front_panel", "to": "back_panel",  "side": "left",  "front_edge": 5, "back_edge": 5},
            {"type": "side_seam",  "from": "front_panel", "to": "back_panel",  "side": "right", "front_edge": 1, "back_edge": 1},
            {"type": "side_seam",  "from": "front_panel", "to": "back_panel",  "side": "left",  "front_edge": 7, "back_edge": 7},
            {"type": "armhole",    "from": "sleeve_right", "cap_edge": 2, "to": "front_panel", "body_edge": 2},
            {"type": "armhole",    "from": "sleeve_right", "cap_edge": 3, "to": "back_panel",  "body_edge": 2},
            {"type": "armhole",    "from": "sleeve_left",  "cap_edge": 3, "to": "front_panel", "body_edge": 6},
            {"type": "armhole",    "from": "sleeve_left",  "cap_edge": 2, "to": "back_panel",  "body_edge": 6},
            {"type": "sleeve_seam", "from": "sleeve_left",  "edge_a": 1, "edge_b": 4},
            {"type": "sleeve_seam", "from": "sleeve_right", "edge_a": 1, "edge_b": 4},
        ],
        "clo_import_notes": [
            "DXF units: millimetres (doc.units = MM).  Import scale = 0.1 in CLO.",
            "CutLine layer: one entity per seam edge (SPLINE or LINE).",
            "Edge indices are 0-based and match edge_manifest.json.",
            "Sleeve cap arc > armhole arc by ~cap_ease_cm for 3D curvature.",
        ],
    }

    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"  Wrote panel metadata: {output_path.name}")
    return output_path


def generate_panels(measurements: GarmentMeasurements, panels_dir: Path) -> PanelGenerationResult:
    """Generate panels and export DXF/SVG/manifest artifacts."""
    panels_dir.mkdir(parents=True, exist_ok=True)
    dxf_dir = panels_dir / "dxf"
    svg_dir = panels_dir / "svg"
    dxf_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)

    generator = DynamicPatternGenerator(measurements)
    generator.generate_front_panel()
    generator.generate_back_panel()

    total_armhole = generator.front_armhole_length + generator.back_armhole_length
    armhole_per_sleeve = total_armhole / 2

    generator.generate_sleeve(piece_name="sleeve_left",  target_armhole_length=armhole_per_sleeve)
    generator.generate_sleeve(piece_name="sleeve_right", target_armhole_length=armhole_per_sleeve)

    export_panels_dxf(generator.layouts, generator.m, dxf_dir)
    export_panels_svg(generator.layouts, svg_dir)

    metadata_path = write_panel_metadata(generator, panels_dir / "panel_metadata.json")
    manifest_path = write_edge_manifest(generator, panels_dir / "edge_manifest.json")

    return PanelGenerationResult(
        panels_dir=panels_dir,
        dxf_dir=dxf_dir,
        svg_dir=svg_dir,
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        panel_names=list(generator.layouts.keys()),
        layouts=generator.layouts,
    )
