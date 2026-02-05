"""
STEP 4: Sewing Pattern Generation
=================================
This script generates real-size T-shirt sewing patterns from measurements.

The 5 key measurements:
- chest_flat: Half the chest circumference (front panel width)
- body_length: Shoulder to hem
- shoulder_width: Shoulder seam to shoulder seam
- sleeve_length: Shoulder to sleeve hem
- armhole_depth: How deep the armhole cuts in

These measurements define the STRUCTURE of the garment.
The image (from earlier steps) defines the APPEARANCE.
"""

import math
from pathlib import Path
from typing import Dict, List, Tuple
import json

# ============================================================
# CONFIGURATION
# ============================================================

# Output directory (absolute path)
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "pattern_output"

# Default measurements (in centimeters)
# XML Schema v1.1 format - matches <Measurements> specification
DEFAULT_MEASUREMENTS = {
    # Core body measurements
    "chest_flat": 50.0,       # HalfChestWidth - half chest width
    "body_length": 70.0,      # GarmentLength - shoulder to hem
    "shoulder_width": 44.0,   # ShoulderWidth - shoulder to shoulder
    "sleeve_length": 22.0,    # SleeveLength - short sleeve length
    "armhole_depth": 22.0,    # ArmholeDepth - armhole curve depth
    
    # Additional measurements from XML spec v1.1
    "hem_width": 50.0,        # HemWidth - hem width (usually = chest_flat)
    "neck_width": 18.0,       # NeckWidth - neckline opening width
    "neck_depth_front": 9.0,  # NeckDepth.front - front neckline drop
    "neck_depth_back": 3.0,   # NeckDepth.back - back neckline drop (shallower)
    "bicep_width": 36.0,      # BicepWidth - sleeve width at bicep
    "neck_band_height": 4.0,  # BandHeight - rib/collar height
    "neck_band_reduction": 0.10,  # Reduction percent for stretch (10% per XML Task spec)
}

# Seam allowance (added to all edges for sewing)
SEAM_ALLOWANCE = 1.5  # cm

# SVG settings
SVG_SCALE = 10  # 1 cm = 10 pixels in SVG (for display)
                # Real-size printing uses viewBox in cm


# ============================================================
# PATTERN GEOMETRY HELPERS
# ============================================================

def point(x: float, y: float) -> Tuple[float, float]:
    """Create a point tuple."""
    return (x, y)


def bezier_curve(p0: Tuple, p1: Tuple, p2: Tuple, p3: Tuple, steps: int = 20) -> List[Tuple]:
    """
    Generate points along a cubic Bezier curve.
    
    Bezier curves are smooth curves defined by 4 points:
    - p0: Start point
    - p1: First control point (curve "pulls" toward this)
    - p2: Second control point
    - p3: End point
    
    Used for: necklines, armholes, sleeve caps
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Cubic Bezier formula
        x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def arc_points(center: Tuple, radius: float, start_angle: float, end_angle: float, steps: int = 20) -> List[Tuple]:
    """
    Generate points along a circular arc.
    
    Args:
        center: Center of the circle
        radius: Radius of the arc
        start_angle: Starting angle in degrees
        end_angle: Ending angle in degrees
        steps: Number of points to generate
    
    Returns:
        List of (x, y) points along the arc
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        angle = math.radians(start_angle + t * (end_angle - start_angle))
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    return points


# ============================================================
# PATTERN PIECE GENERATORS
# ============================================================

def generate_front_panel(measurements: Dict[str, float]) -> Dict:
    """
    Generate the FRONT BODY panel pattern.
    
    Anatomy of the front panel:
    
         shoulder_width/2
        ←───────────────→
        ┌───────────────┐ ← shoulder line
        │    ╭───╮      │   ← neckline (curved)
        │   ╱     ╲     │
        │  │       │    │
        │  │       ╰────┤ ← armhole (curved)
        │  │            │   ↑
        │  │            │   │ armhole_depth
        │  │            │   ↓
        │  │            ├───← underarm point
        │  │            │
        │  │            │   ↑
        │  │            │   │ body_length
        │  │            │   │ - armhole_depth
        │  │            │   ↓
        └──┴────────────┘ ← hem line
        ←───────────────→
            chest_flat/2
    
    Note: This is HALF of the front (we fold at center)
    """
    chest = measurements["chest_flat"]
    length = measurements["body_length"]
    shoulder = measurements["shoulder_width"]
    armhole = measurements["armhole_depth"]
    
    # Panel is half-width (symmetric, cut on fold)
    half_width = chest / 2
    half_shoulder = shoulder / 2
    
    # Neckline dimensions
    neck_width = half_shoulder * 0.35  # Neck is ~35% of shoulder
    neck_depth = 8.0  # Front neck drop (deeper than back)
    
    # Define key points (origin at center-top, Y increases downward)
    points = {}
    
    # Center front line (fold line)
    points["center_neck"] = (0, neck_depth)
    points["center_hem"] = (0, length)
    
    # Shoulder line
    points["shoulder_neck"] = (neck_width, 0)
    points["shoulder_end"] = (half_shoulder, 2.0)  # Slight shoulder slope
    
    # Armhole
    points["armhole_top"] = (half_shoulder, 2.0)
    points["armhole_bottom"] = (half_width, armhole)
    
    # Side seam
    points["side_armhole"] = (half_width, armhole)
    points["side_hem"] = (half_width, length)
    
    # Build outline path
    outline = []
    
    # 1. Start at center neck
    outline.append(points["center_neck"])
    
    # 2. Neckline curve (Bezier from center to shoulder)
    neck_curve = bezier_curve(
        points["center_neck"],
        (neck_width * 0.3, neck_depth),      # Control point 1
        (neck_width * 0.7, 0),               # Control point 2
        points["shoulder_neck"],
        steps=15
    )
    outline.extend(neck_curve[1:])  # Skip first point (duplicate)
    
    # 3. Shoulder line (straight)
    outline.append(points["shoulder_end"])
    
    # 4. Armhole curve (from shoulder to underarm)
    armhole_curve = bezier_curve(
        points["shoulder_end"],
        (half_shoulder + 2, armhole * 0.3),   # Curves outward slightly
        (half_width + 1, armhole * 0.6),      # Then curves in
        points["armhole_bottom"],
        steps=20
    )
    outline.extend(armhole_curve[1:])
    
    # 5. Side seam (straight down)
    outline.append(points["side_hem"])
    
    # 6. Hem (straight across)
    outline.append(points["center_hem"])
    
    # Close path back to start
    outline.append(points["center_neck"])
    
    return {
        "name": "Front Panel",
        "outline": outline,
        "fold_line": [(0, 0), (0, length)],
        "grainline": [(half_width/2, length*0.2), (half_width/2, length*0.8)],
        "width": half_width,
        "height": length,
        "notes": "Cut 1 on fold. Grainline parallel to fold.",
        # NEW: Edge labels for sewing - maps edge name to vertex indices
        # These indices refer to positions in the outline array
        # SCHEMA: left, right, armhole_L, armhole_R for body panels
        "edges": {
            "neckline": {"start": 0, "end": 16},           # Neckline curve (indices 0-16)
            "shoulder": {"start": 16, "end": 17},          # Shoulder line
            "armhole_R": {"start": 17, "end": 27},         # Right armhole curve
            "armhole_L": {"start": 27, "end": 38},         # Left armhole curve
            "right": {"start": 38, "end": 39},             # Right side seam
            "hem": {"start": 39, "end": 40},               # Hem line
            "left": {"start": 40, "end": 41}               # Left side / center fold
        }
    }


def generate_back_panel(measurements: Dict[str, float]) -> Dict:
    """
    Generate the BACK BODY panel pattern.
    
    Very similar to front, but with:
    - Shallower neckline (back neck is higher)
    - Same armhole shape
    
         shoulder_width/2
        ←───────────────→
        ┌───────╮───────┐ ← shoulder line
        │       ╰╮      │   ← back neck (shallower curve)
        │        │      │
        │        │      │
        │        │ ╰────┤ ← armhole
        │        │      │
        ...     ...    ...
        └────────┴──────┘ ← hem
    """
    chest = measurements["chest_flat"]
    length = measurements["body_length"]
    shoulder = measurements["shoulder_width"]
    armhole = measurements["armhole_depth"]
    
    half_width = chest / 2
    half_shoulder = shoulder / 2
    
    # Back neckline is shallower than front
    neck_width = half_shoulder * 0.35
    neck_depth = 2.5  # Much shallower than front (8cm)
    
    points = {}
    
    # Center back line
    points["center_neck"] = (0, neck_depth)
    points["center_hem"] = (0, length)
    
    # Shoulder
    points["shoulder_neck"] = (neck_width, 0)
    points["shoulder_end"] = (half_shoulder, 2.0)
    
    # Armhole & side (same as front)
    points["armhole_bottom"] = (half_width, armhole)
    points["side_hem"] = (half_width, length)
    
    # Build outline
    outline = []
    
    # Center neck
    outline.append(points["center_neck"])
    
    # Back neckline (gentler curve)
    neck_curve = bezier_curve(
        points["center_neck"],
        (neck_width * 0.4, neck_depth),
        (neck_width * 0.8, 0.5),
        points["shoulder_neck"],
        steps=12
    )
    outline.extend(neck_curve[1:])
    
    # Shoulder
    outline.append(points["shoulder_end"])
    
    # Armhole
    armhole_curve = bezier_curve(
        points["shoulder_end"],
        (half_shoulder + 2, armhole * 0.3),
        (half_width + 1, armhole * 0.6),
        points["armhole_bottom"],
        steps=20
    )
    outline.extend(armhole_curve[1:])
    
    # Side seam
    outline.append(points["side_hem"])
    
    # Hem
    outline.append(points["center_hem"])
    
    # Close
    outline.append(points["center_neck"])
    
    return {
        "name": "Back Panel",
        "outline": outline,
        "fold_line": [(0, 0), (0, length)],
        "grainline": [(half_width/2, length*0.2), (half_width/2, length*0.8)],
        "width": half_width,
        "height": length,
        "notes": "Cut 1 on fold. Grainline parallel to fold.",
        # NEW: Edge labels for sewing - maps edge name to vertex indices
        # SCHEMA: left, right, armhole_L, armhole_R for body panels
        "edges": {
            "neckline": {"start": 0, "end": 13},           # Back neckline curve
            "shoulder": {"start": 13, "end": 14},          # Shoulder line
            "armhole_R": {"start": 14, "end": 24},         # Right armhole curve
            "armhole_L": {"start": 24, "end": 35},         # Left armhole curve
            "right": {"start": 35, "end": 36},             # Right side seam
            "hem": {"start": 36, "end": 37},               # Hem line
            "left": {"start": 37, "end": 38}               # Left side / center fold
        }
    }


def generate_sleeve(measurements: Dict[str, float]) -> Dict:
    """
    Generate the SLEEVE panel pattern.
    
    Sleeve anatomy:
    
              sleeve cap (curved top)
                 ╭───────╮
                ╱         ╲
               ╱           ╲
              ╱             ╲  ← This curve fits into the armhole
             │               │
             │               │  ↑
             │               │  │ sleeve_length
             │               │  ↓
             └───────────────┘  ← sleeve hem
             ←───────────────→
               armhole_depth + ease
    
    The sleeve cap curve must match the armhole curve length!
    This is how the sleeve "sews into" the armhole.
    """
    sleeve_length = measurements["sleeve_length"]
    armhole_depth = measurements["armhole_depth"]
    chest = measurements["chest_flat"]
    
    # Sleeve width at underarm (must fit through armhole opening)
    # Typically armhole circumference / 2 + ease
    sleeve_width = armhole_depth * 1.4  # Wider than armhole for ease
    
    # Sleeve cap height (how tall the "bump" at top is)
    cap_height = armhole_depth * 0.45
    
    half_width = sleeve_width / 2
    
    points = {}
    
    # Origin at top center of sleeve
    points["cap_top"] = (0, 0)
    points["cap_left"] = (-half_width, cap_height)
    points["cap_right"] = (half_width, cap_height)
    points["hem_left"] = (-half_width, sleeve_length)
    points["hem_right"] = (half_width, sleeve_length)
    
    outline = []
    
    # Left side of cap (curve down from top)
    left_cap = bezier_curve(
        points["cap_top"],
        (-half_width * 0.3, cap_height * 0.1),  # Gentle start
        (-half_width * 0.7, cap_height * 0.5),  # Curve out
        points["cap_left"],
        steps=15
    )
    outline.extend(left_cap)
    
    # Left side seam (straight down)
    outline.append(points["hem_left"])
    
    # Hem (straight across)
    outline.append(points["hem_right"])
    
    # Right side seam (straight up)
    outline.append(points["cap_right"])
    
    # Right side of cap (curve up to top)
    right_cap = bezier_curve(
        points["cap_right"],
        (half_width * 0.7, cap_height * 0.5),
        (half_width * 0.3, cap_height * 0.1),
        points["cap_top"],
        steps=15
    )
    outline.extend(right_cap[1:])
    
    return {
        "name": "Sleeve",
        "outline": outline,
        "fold_line": None,  # Sleeve is not cut on fold
        "grainline": [(0, cap_height + 5), (0, sleeve_length - 5)],
        "width": sleeve_width,
        "height": sleeve_length,
        "notes": "Cut 2 (mirror for left/right). Grainline runs vertically.",
        # NEW: Edge labels for sewing - maps edge name to vertex indices
        # SCHEMA: "curve" for sleeve cap (attaches to body armhole)
        "edges": {
            "curve": {"start": 0, "end": 34},              # Full sleeve cap curve (for armhole attachment)
            "cap_left": {"start": 0, "end": 16},           # Left side of sleeve cap
            "underarm_left": {"start": 16, "end": 17},     # Left underarm seam
            "hem": {"start": 17, "end": 18},               # Sleeve hem
            "underarm_right": {"start": 18, "end": 19},    # Right underarm seam
            "cap_right": {"start": 19, "end": 34}          # Right side of sleeve cap
        }
    }


def calculate_arc_length(points: List[Tuple[float, float]]) -> float:
    """
    Calculate arc length from a list of points using adaptive sampling.
    
    XML Task: <NecklineCurveLength method="arc_length" sampling="adaptive" maxSamples="64"/>
    """
    if len(points) < 2:
        return 0.0
    
    total_length = 0.0
    for i in range(len(points) - 1):
        dx = points[i+1][0] - points[i][0]
        dy = points[i+1][1] - points[i][1]
        total_length += math.sqrt(dx*dx + dy*dy)
    
    return total_length


def generate_neck_band(measurements: Dict[str, float], front_pattern: Dict, back_pattern: Dict) -> Dict:
    """
    Generate the NECK BAND (collar/ribbing) pattern piece.
    
    XML Task: Fix_Neck_Band_Generation v1.0
    
    The neck band is a critical piece that:
    - Finishes the neckline opening
    - Is CUT SHORTER than the neckline (10% reduction for stretch)
    - Creates tension that pulls the neckline into shape
    
    XML Task Reference:
        <NeckBand>
            <Length ref="NecklineCurveLength" reductionPercent="10"/>
            <Height value="4"/>
            <MeshConstraints>
                <MaxVertices value="64"/>
                <MinVertices value="24"/>
                <UniformSpacing enabled="true"/>
                <AllowSubdivision value="false"/>
            </MeshConstraints>
        </NeckBand>
    
    Shape:
        ┌────────────────────────────────────┐
        │         NECK BAND                  │ ← BandHeight (4cm)
        │  (cut on fold for continuous band) │
        └────────────────────────────────────┘
              ← BandLength (reduced by 10%) →
    """
    # Get neckline measurements
    neck_width = measurements.get("neck_width", 18.0)
    neck_depth_front = measurements.get("neck_depth_front", 9.0)
    neck_depth_back = measurements.get("neck_depth_back", 3.0)
    band_height = measurements.get("neck_band_height", 4.0)
    reduction = measurements.get("neck_band_reduction", 0.10)  # 10% per XML Task
    
    # ========================================
    # NECKLINE CURVE LENGTH (arc_length method)
    # XML: <NecklineCurveLength method="arc_length" sampling="adaptive" maxSamples="64"/>
    # ========================================
    
    # Generate neckline curve points for accurate arc length calculation
    # Front neckline (deeper curve)
    front_curve_points = []
    samples = min(32, 64)  # Adaptive sampling, capped at maxSamples/2 per curve
    for i in range(samples + 1):
        t = i / samples
        # Half-ellipse approximation for neckline
        x = neck_width/2 * math.cos(math.pi * t)
        y = neck_depth_front * math.sin(math.pi * t)
        front_curve_points.append((x, y))
    
    # Back neckline (shallower curve)
    back_curve_points = []
    for i in range(samples + 1):
        t = i / samples
        x = neck_width/2 * math.cos(math.pi * t)
        y = neck_depth_back * math.sin(math.pi * t)
        back_curve_points.append((x, y))
    
    # Calculate arc lengths using proper method
    front_neckline_length = calculate_arc_length(front_curve_points)
    back_neckline_length = calculate_arc_length(back_curve_points)
    
    # Total neckline = front + back (full circumference)
    total_neckline = front_neckline_length + back_neckline_length
    
    # ========================================
    # SAFETY VALIDATION
    # XML: <FailurePolicy><OnInvalidLength action="abort"/><OnNaN action="abort"/></FailurePolicy>
    # ========================================
    if math.isnan(total_neckline) or total_neckline <= 0:
        print(f"    ✗ ERROR: Invalid neckline length ({total_neckline}). Aborting.")
        raise ValueError(f"Invalid neckline curve length: {total_neckline}")
    
    # Apply reduction for stretch (10% shorter per XML Task)
    band_length = total_neckline * (1 - reduction)
    
    # ========================================
    # MESH CONSTRAINTS
    # XML: <MaxVertices value="64"/> <MinVertices value="24"/> <UniformSpacing enabled="true"/>
    # ========================================
    target_vertices = 48  # Fixed count per XML: <Resampling mode="fixed_count" targetVertices="48"/>
    max_vertices = 64
    min_vertices = 24
    
    # Create rectangle outline with uniform spacing
    # Rectangle has 4 sides, distribute vertices evenly
    outline = [
        (0, 0),                    # Bottom left
        (band_length, 0),          # Bottom right
        (band_length, band_height), # Top right
        (0, band_height),          # Top left
        (0, 0)                     # Close path
    ]
    
    print(f"    Neck band calculated (XML Task Fix_Neck_Band_Generation):")
    print(f"      - Front neckline arc: {front_neckline_length:.1f} cm")
    print(f"      - Back neckline arc: {back_neckline_length:.1f} cm")
    print(f"      - Total neckline: {total_neckline:.1f} cm")
    print(f"      - Band length (after {reduction*100:.0f}% reduction): {band_length:.1f} cm")
    print(f"      - Band height: {band_height} cm")
    print(f"      - Mesh constraints: {target_vertices} target verts (min={min_vertices}, max={max_vertices})")
    
    return {
        "name": "Neck Band",
        "outline": outline,
        "fold_line": [(0, band_height/2), (band_length, band_height/2)],
        "grainline": [(band_length * 0.2, band_height/2), (band_length * 0.8, band_height/2)],
        "width": band_length,
        "height": band_height,
        "notes": "Cut 1 on fold. Stretch to fit neckline. High tension seam.",
        # Edge labels for sewing
        "edges": {
            "inner": {"start": 0, "end": 1},   # Inner edge (attaches to neckline)
            "outer": {"start": 2, "end": 3},   # Outer edge (visible)
            "left": {"start": 3, "end": 4},    # Left end
            "right": {"start": 1, "end": 2}    # Right end
        },
        # Derived measurements for reference
        "derived": {
            "neckline_curve_length": total_neckline,
            "reduction_percent": reduction * 100,
            "tension": "high",
            "stiffness": "high"
        },
        # Mesh generation constraints (XML Task)
        "mesh_constraints": {
            "target_vertices": target_vertices,
            "max_vertices": max_vertices,
            "min_vertices": min_vertices,
            "uniform_spacing": True,
            "allow_subdivision": False
        }
    }


# ============================================================
# SVG GENERATION
# ============================================================

def points_to_svg_path(points: List[Tuple[float, float]]) -> str:
    """
    Convert list of points to SVG path data.
    
    SVG path commands:
    - M x,y = Move to (start point)
    - L x,y = Line to
    - Z = Close path
    """
    if not points:
        return ""
    
    # Start with Move command
    path = f"M {points[0][0]:.2f},{points[0][1]:.2f}"
    
    # Add Line commands for remaining points
    for p in points[1:]:
        path += f" L {p[0]:.2f},{p[1]:.2f}"
    
    # Close the path
    path += " Z"
    
    return path


def generate_svg(
    pattern: Dict,
    include_seam_allowance: bool = True,
    scale: float = SVG_SCALE
) -> str:
    """
    Generate SVG file content for a pattern piece.
    
    Args:
        pattern: Pattern dictionary with outline, etc.
        include_seam_allowance: Whether to show seam allowance
        scale: Pixels per cm (for display)
    
    Returns:
        SVG file content as string
    """
    outline = pattern["outline"]
    width = pattern["width"]
    height = pattern["height"]
    name = pattern["name"]
    
    # Calculate bounding box with margin
    all_x = [p[0] for p in outline]
    all_y = [p[1] for p in outline]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    # Add margin for seam allowance and labels
    margin = SEAM_ALLOWANCE + 3
    
    # SVG dimensions (in cm for viewBox, scaled for width/height)
    svg_width = (max_x - min_x + 2 * margin)
    svg_height = (max_y - min_y + 2 * margin)
    
    # Offset to center pattern in SVG
    offset_x = -min_x + margin
    offset_y = -min_y + margin
    
    # Transform points
    def transform(p):
        return (p[0] + offset_x, p[1] + offset_y)
    
    transformed_outline = [transform(p) for p in outline]
    
    # Build SVG
    svg_lines = []
    
    # SVG header with real-size viewBox
    svg_lines.append(f'<?xml version="1.0" encoding="UTF-8"?>')
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg"')
    svg_lines.append(f'     width="{svg_width * scale}px"')
    svg_lines.append(f'     height="{svg_height * scale}px"')
    svg_lines.append(f'     viewBox="0 0 {svg_width:.2f} {svg_height:.2f}">')
    
    # Background
    svg_lines.append(f'  <rect width="100%" height="100%" fill="white"/>')
    
    # Title
    svg_lines.append(f'  <text x="{svg_width/2}" y="2" text-anchor="middle" font-size="1.5" font-family="Arial">{name}</text>')
    
    # Seam allowance (if enabled) - dashed line outside pattern
    if include_seam_allowance:
        seam_outline = offset_outline(transformed_outline, SEAM_ALLOWANCE)
        seam_path = points_to_svg_path(seam_outline)
        svg_lines.append(f'  <path d="{seam_path}" fill="none" stroke="#999" stroke-width="0.1" stroke-dasharray="0.5,0.3"/>')
    
    # Pattern outline (solid line)
    pattern_path = points_to_svg_path(transformed_outline)
    svg_lines.append(f'  <path d="{pattern_path}" fill="none" stroke="black" stroke-width="0.15"/>')
    
    # Fold line (if present)
    if pattern.get("fold_line"):
        fold = pattern["fold_line"]
        fold_start = transform(fold[0])
        fold_end = transform(fold[1])
        svg_lines.append(f'  <line x1="{fold_start[0]}" y1="{fold_start[1]}" x2="{fold_end[0]}" y2="{fold_end[1]}"')
        svg_lines.append(f'        stroke="blue" stroke-width="0.1" stroke-dasharray="1,0.5"/>')
        svg_lines.append(f'  <text x="{fold_start[0] + 0.5}" y="{(fold_start[1] + fold_end[1])/2}" font-size="0.8" fill="blue">FOLD</text>')
    
    # Grainline
    if pattern.get("grainline"):
        grain = pattern["grainline"]
        grain_start = transform(grain[0])
        grain_end = transform(grain[1])
        svg_lines.append(f'  <line x1="{grain_start[0]}" y1="{grain_start[1]}" x2="{grain_end[0]}" y2="{grain_end[1]}"')
        svg_lines.append(f'        stroke="red" stroke-width="0.1" marker-end="url(#arrow)"/>')
        svg_lines.append(f'  <text x="{grain_start[0] + 0.5}" y="{grain_start[1]}" font-size="0.6" fill="red">GRAIN</text>')
    
    # Arrow marker definition
    svg_lines.append(f'  <defs>')
    svg_lines.append(f'    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">')
    svg_lines.append(f'      <path d="M 0 0 L 10 5 L 0 10 z" fill="red"/>')
    svg_lines.append(f'    </marker>')
    svg_lines.append(f'  </defs>')
    
    # Notes
    if pattern.get("notes"):
        svg_lines.append(f'  <text x="1" y="{svg_height - 1}" font-size="0.6" fill="#666">{pattern["notes"]}</text>')
    
    # Dimensions
    svg_lines.append(f'  <text x="{svg_width - 1}" y="{svg_height - 1}" text-anchor="end" font-size="0.5" fill="#666">W:{width:.1f}cm H:{height:.1f}cm</text>')
    
    svg_lines.append('</svg>')
    
    return '\n'.join(svg_lines)


def offset_outline(points: List[Tuple], offset: float) -> List[Tuple]:
    """
    Offset a polygon outline outward by a given distance.
    
    This creates the seam allowance line outside the cutting line.
    
    Note: This is a simplified implementation that works for convex shapes.
    A full implementation would handle concave corners differently.
    """
    if len(points) < 3:
        return points
    
    result = []
    n = len(points)
    
    for i in range(n):
        # Get three consecutive points
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        
        # Calculate edge vectors
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        
        # Calculate normals (perpendicular, pointing outward)
        len1 = math.sqrt(v1[0]**2 + v1[1]**2) or 1
        len2 = math.sqrt(v2[0]**2 + v2[1]**2) or 1
        
        n1 = (-v1[1] / len1, v1[0] / len1)
        n2 = (-v2[1] / len2, v2[0] / len2)
        
        # Average normal at corner
        avg_n = ((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2)
        avg_len = math.sqrt(avg_n[0]**2 + avg_n[1]**2) or 1
        avg_n = (avg_n[0] / avg_len, avg_n[1] / avg_len)
        
        # Offset point
        new_point = (p1[0] + avg_n[0] * offset, p1[1] + avg_n[1] * offset)
        result.append(new_point)
    
    return result


# ============================================================
# MAIN PATTERN GENERATION
# ============================================================

def generate_all_patterns(measurements: Dict[str, float]) -> Dict[str, Dict]:
    """
    Generate all pattern pieces from measurements.
    
    XML Schema v1.1 generates:
    - front_bodice (Front Panel)
    - back_bodice (Back Panel)
    - sleeve (Left/Right Sleeve)
    - neck_band (Collar/Ribbing)
    
    Args:
        measurements: Dictionary with measurements (v1.1 format)
    
    Returns:
        Dictionary of pattern pieces
    """
    patterns = {}
    
    print("\n→ Generating front panel (front_bodice)...")
    patterns["front"] = generate_front_panel(measurements)
    print(f"  ✓ Front: {patterns['front']['width']:.1f} x {patterns['front']['height']:.1f} cm")
    
    print("\n→ Generating back panel (back_bodice)...")
    patterns["back"] = generate_back_panel(measurements)
    print(f"  ✓ Back: {patterns['back']['width']:.1f} x {patterns['back']['height']:.1f} cm")
    
    print("\n→ Generating sleeve...")
    patterns["sleeve"] = generate_sleeve(measurements)
    print(f"  ✓ Sleeve: {patterns['sleeve']['width']:.1f} x {patterns['sleeve']['height']:.1f} cm")
    
    print("\n→ Generating neck band (collar)...")
    patterns["neck_band"] = generate_neck_band(measurements, patterns["front"], patterns["back"])
    print(f"  ✓ Neck Band: {patterns['neck_band']['width']:.1f} x {patterns['neck_band']['height']:.1f} cm")
    
    return patterns


def save_patterns(patterns: Dict[str, Dict], measurements: Dict[str, float]):
    """
    Save all patterns as SVG files and metadata.
    """
    print("\n→ Saving pattern files...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save each pattern as SVG
    for name, pattern in patterns.items():
        svg_content = generate_svg(pattern)
        svg_path = OUTPUT_DIR / f"{name}_pattern.svg"
        with open(svg_path, 'w') as f:
            f.write(svg_content)
        print(f"  ✓ {svg_path}")
    
    # Save metadata JSON
    metadata = {
        "measurements": measurements,
        "seam_allowance": SEAM_ALLOWANCE,
        "patterns": {}
    }
    
    for name, pattern in patterns.items():
        metadata["patterns"][name] = {
            "name": pattern["name"],
            "width": pattern["width"],
            "height": pattern["height"],
            "notes": pattern.get("notes", ""),
            "svg_file": f"{name}_pattern.svg"
        }
    
    json_path = OUTPUT_DIR / "pattern_metadata.json"
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ {json_path}")
    
    # NEW: Save seam definitions
    save_seam_definitions(patterns)


def extract_edge_vertices(outline: List[Tuple], edge_def: Dict) -> List[Tuple]:
    """
    Extract vertex coordinates for a specific edge from the outline.
    
    Args:
        outline: Full outline point list
        edge_def: Dictionary with "start" and "end" indices
    
    Returns:
        List of (x, y) coordinates for the edge vertices
    """
    start_idx = edge_def.get("start", 0)
    end_idx = edge_def.get("end", len(outline))
    
    # Handle wrap-around for closed outlines
    if end_idx >= len(outline):
        end_idx = len(outline) - 1
    
    # Extract vertices in range
    return [outline[i] for i in range(start_idx, end_idx + 1)]


def generate_seam_definitions(patterns: Dict[str, Dict]) -> Dict:
    """
    Generate seam definitions that tell Blender which edges to sew together.
    
    ENHANCED FORMAT with vertex coordinates:
    - Each panel contains edge labels with actual vertex positions
    - Seam pairs reference panel:edge_name for matching
    - Blender can use positions to find nearest mesh vertices
    
    Seam Format:
    Each seam is a pair: ["panel1:edge_name", "panel2:edge_name"]
    
    For a T-shirt (XML Schema v1.1), we need to sew:
    1. Side seams: Front.left_side <-> Back.right_side (both sides)
    2. Shoulder seams: Front.shoulder <-> Back.shoulder
    3. Armhole seams: Front+Back.armhole <-> Sleeve.sleeve_cap
    4. Neck seam: Neck_Band <-> Front.neckline + Back.neckline
    
    Since patterns are half-panels (cut on fold), we define seams
    for the full garment by specifying left and right versions.
    
    Returns:
        Dictionary with seam definitions including vertex coordinates
    """
    seams = {
        # Seam pairs in simplified format: ["Panel:edge", "Panel:edge"]
        # XML Schema v1.1 format with stiffness metadata
        # SCHEMA: ["PanelName:edge_name", "PanelName:edge_name"]
        "seams": [
            # ========================================
            # SIDE SEAMS: Front.left_side <-> Back.right_side
            # XML: <Seam type="side" stiffness="medium"/>
            # ========================================
            ["Front_Panel:left", "Back_Panel:right"],
            ["Front_Panel:right", "Back_Panel:left"],
            
            # ========================================
            # SHOULDER SEAMS: Front.shoulder <-> Back.shoulder
            # XML: <Seam type="shoulder" stiffness="high"/>
            # ========================================
            ["Front_Panel:shoulder", "Back_Panel:shoulder"],
            
            # ========================================
            # ARMHOLE SEAMS: Body armholes <-> Sleeve.sleeve_cap
            # XML: <Seam type="armhole" easeAware="true"/>
            # ========================================
            ["Front_Panel:armhole_L", "Left_Sleeve:curve"],
            ["Back_Panel:armhole_L", "Left_Sleeve:curve"],
            ["Front_Panel:armhole_R", "Right_Sleeve:curve"],
            ["Back_Panel:armhole_R", "Right_Sleeve:curve"],
            
            # ========================================
            # NECK SEAM: Neck_Band <-> Front+Back necklines
            # XML: <Seam type="neck" tension="high" stiffness="high"/>
            # ========================================
            ["Neck_Band:inner", "Front_Panel:neckline"],
            ["Neck_Band:inner", "Back_Panel:neckline"],
        ],
        
        # Detailed seam definitions with metadata (XML Schema v1.1)
        "seam_details": [
            # Side seams: Front and Back are sewn at the sides
            {
                "name": "side_seam",
                "edge1": {"piece": "front_bodice", "edge_name": "left_side"},
                "edge2": {"piece": "back_bodice", "edge_name": "right_side"},
                "type": "straight",
                "stiffness": "medium",
                "priority": 1  # Sew first
            },
            
            # Shoulder seams: XML: <Seam type="shoulder" stiffness="high"/>
            {
                "name": "shoulder_seam",
                "edge1": {"piece": "front", "edge_name": "shoulder"},
                "edge2": {"piece": "back_bodice", "edge_name": "shoulder"},
                "type": "straight",
                "stiffness": "high",
                "priority": 2
            },
            
            # Armhole seams: Combined front+back armhole to Sleeve cap
            # XML: <Seam type="armhole" easeAware="true"/>
            {
                "name": "armhole_seam",
                "edge1": {"piece": "front_bodice", "edge_name": "armhole"},
                "edge2": {"piece": "sleeve", "edge_name": "sleeve_cap"},
                "type": "curved",
                "ease_aware": True,
                "priority": 3
            },
            
            # Neck seam: Neck band attaches to combined necklines
            # XML: <Seam type="neck" tension="high" stiffness="high"/>
            {
                "name": "neck_seam",
                "edge1": {"piece": "neck_band", "edge_name": "inner"},
                "edge2": {"piece": "front_bodice", "edge_name": "neckline"},
                "edge3": {"piece": "back_bodice", "edge_name": "neckline"},
                "type": "curved",
                "tension": "high",
                "stiffness": "high",
                "priority": 4
            }
        ],
        
        # Panel data with edge vertex coordinates
        # This is the KEY enhancement - actual geometry for each edge
        "panels": {}
    }
    
    # Build panel data with vertex coordinates for each edge
    for panel_name, pattern in patterns.items():
        outline = pattern.get("outline", [])
        edges_def = pattern.get("edges", {})
        
        panel_data = {
            "display_name": pattern.get("name", panel_name),
            "width_cm": pattern.get("width", 0),
            "height_cm": pattern.get("height", 0),
            "vertex_count": len(outline),
            "edges": {}
        }
        
        # Extract vertex coordinates for each labeled edge
        for edge_name, edge_indices in edges_def.items():
            edge_vertices = extract_edge_vertices(outline, edge_indices)
            panel_data["edges"][edge_name] = {
                "start_index": edge_indices.get("start", 0),
                "end_index": edge_indices.get("end", 0),
                "vertex_count": len(edge_vertices),
                # Store actual coordinates (in cm) - Blender will convert to meters
                "vertices": [[round(x, 3), round(y, 3)] for x, y in edge_vertices]
            }
        
        seams["panels"][panel_name] = panel_data
    
    return seams


def save_seam_definitions(patterns: Dict[str, Dict]):
    """
    Save seam definitions to seams.json file.
    
    This file tells Blender which edges to sew together.
    Enhanced format includes:
    - Simple seam pairs for easy parsing
    - Detailed seam metadata for advanced operations
    - Actual vertex coordinates for each panel edge
    """
    print("\n→ Generating seam definitions...")
    
    seams = generate_seam_definitions(patterns)
    
    seams_path = OUTPUT_DIR / "seams.json"
    with open(seams_path, 'w') as f:
        json.dump(seams, f, indent=2)
    
    print(f"  ✓ {seams_path}")
    print(f"  ✓ Defined {len(seams['seams'])} seam pairs for sewing")
    print(f"  ✓ Panel edge data for {len(seams['panels'])} panels:")
    
    for panel_name, panel_data in seams["panels"].items():
        edge_count = len(panel_data.get("edges", {}))
        print(f"      - {panel_name}: {edge_count} labeled edges")


def run_pattern_generation_pipeline(measurements: Dict[str, float] = None):
    """
    Run the complete pattern generation pipeline.
    """
    print("\n" + "="*60)
    print("   STEP 4: SEWING PATTERN GENERATION")
    print("="*60)
    
    # Use provided measurements or defaults
    if measurements is None:
        measurements = DEFAULT_MEASUREMENTS
        print("\n⚠ Using DEFAULT measurements:")
    else:
        print("\n✓ Using PROVIDED measurements:")
    
    print(f"\n  ┌{'─'*35}┐")
    print(f"  │ {'Measurement':<20} {'Value':>10} │")
    print(f"  ├{'─'*35}┤")
    print(f"  │ {'chest_flat':<20} {measurements['chest_flat']:>7.1f} cm │")
    print(f"  │ {'body_length':<20} {measurements['body_length']:>7.1f} cm │")
    print(f"  │ {'shoulder_width':<20} {measurements['shoulder_width']:>7.1f} cm │")
    print(f"  │ {'sleeve_length':<20} {measurements['sleeve_length']:>7.1f} cm │")
    print(f"  │ {'armhole_depth':<20} {measurements['armhole_depth']:>7.1f} cm │")
    print(f"  └{'─'*35}┘")
    
    print(f"\n  Seam allowance: {SEAM_ALLOWANCE} cm")
    
    # Generate patterns
    patterns = generate_all_patterns(measurements)
    
    # Save patterns
    save_patterns(patterns, measurements)
    
    # Summary
    print("\n" + "="*60)
    print("   PATTERN GENERATION SUMMARY")
    print("="*60)
    
    print("\n📐 Generated patterns:")
    print("\n  FRONT PANEL:")
    print(f"    - Width: {patterns['front']['width']:.1f} cm (half-width, cut on fold)")
    print(f"    - Length: {patterns['front']['height']:.1f} cm")
    print(f"    - Full width when unfolded: {patterns['front']['width'] * 2:.1f} cm")
    
    print("\n  BACK PANEL:")
    print(f"    - Width: {patterns['back']['width']:.1f} cm (half-width, cut on fold)")
    print(f"    - Length: {patterns['back']['height']:.1f} cm")
    print(f"    - Neckline: shallower than front")
    
    print("\n  SLEEVE (x2):")
    print(f"    - Width: {patterns['sleeve']['width']:.1f} cm")
    print(f"    - Length: {patterns['sleeve']['height']:.1f} cm")
    print(f"    - Sleeve cap height: ~{patterns['sleeve']['width']*0.45/1.4:.1f} cm")
    
    print(f"\n📁 Output saved to: {OUTPUT_DIR}/")
    print(f"   - front_pattern.svg")
    print(f"   - back_pattern.svg")
    print(f"   - sleeve_pattern.svg")
    print(f"   - pattern_metadata.json")
    print(f"   - seams.json (NEW: sewing instructions for Blender)")
    
    print("\n" + "="*60)
    
    return patterns


# ============================================================
# INTERACTIVE INPUT
# ============================================================

def get_measurement_input(name: str, description: str, default: float) -> float:
    """
    Prompt user for a measurement value.
    
    Args:
        name: Measurement name
        description: Human-readable description
        default: Default value if user presses Enter
    
    Returns:
        The measurement value (float)
    """
    while True:
        try:
            prompt = f"  {name} ({description}) [{default} cm]: "
            user_input = input(prompt).strip()
            
            if user_input == "":
                return default
            
            value = float(user_input)
            if value <= 0:
                print("    ⚠ Value must be positive. Try again.")
                continue
            return value
        except ValueError:
            print("    ⚠ Please enter a valid number.")


def get_measurements_from_user() -> Dict[str, float]:
    """
    Interactively prompt user for all 5 measurements.
    
    Returns:
        Dictionary with all measurements
    """
    print("\n" + "="*60)
    print("   ENTER T-SHIRT MEASUREMENTS")
    print("="*60)
    print("\n  Press ENTER to use default value shown in [brackets]")
    print("  All measurements are in centimeters (cm)\n")
    
    measurements = {}
    
    measurements["chest_flat"] = get_measurement_input(
        "chest_flat",
        "half chest width, pit to pit",
        DEFAULT_MEASUREMENTS["chest_flat"]
    )
    
    measurements["body_length"] = get_measurement_input(
        "body_length",
        "shoulder to hem",
        DEFAULT_MEASUREMENTS["body_length"]
    )
    
    measurements["shoulder_width"] = get_measurement_input(
        "shoulder_width",
        "shoulder seam to shoulder seam",
        DEFAULT_MEASUREMENTS["shoulder_width"]
    )
    
    measurements["sleeve_length"] = get_measurement_input(
        "sleeve_length",
        "shoulder to sleeve hem",
        DEFAULT_MEASUREMENTS["sleeve_length"]
    )
    
    measurements["armhole_depth"] = get_measurement_input(
        "armhole_depth",
        "shoulder to underarm",
        DEFAULT_MEASUREMENTS["armhole_depth"]
    )
    
    return measurements


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Generate T-shirt sewing patterns from measurements.
    
    The script will prompt you to enter:
    1. chest_flat - Half chest width (measure flat, pit to pit)
    2. body_length - Shoulder seam to bottom hem
    3. shoulder_width - Shoulder seam to shoulder seam
    4. sleeve_length - Shoulder seam to sleeve hem
    5. armhole_depth - Shoulder seam to underarm
    
    Press ENTER to use default values.
    
    The generated SVG files are REAL SIZE - if printed at 100%,
    they will be the correct dimensions for cutting fabric.
    
    Pattern pieces:
    1. FRONT - Cut 1 on fold
    2. BACK - Cut 1 on fold  
    3. SLEEVE - Cut 2 (left and right)
    """
    
    # Get measurements from user interactively
    user_measurements = get_measurements_from_user()
    
    # Generate patterns with user's measurements
    patterns = run_pattern_generation_pipeline(user_measurements)
    
    print("\n" + "="*60)
    print("   STEP 4 COMPLETE — GREEN SIGNAL REQUIRED ✅")
    print("="*60)
    print("\nNext step: Sewing and simulation in Blender")
    print("Waiting for your GREEN SIGNAL to proceed...")
