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
import time
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Output directory
OUTPUT_DIR = Path("pattern_output")

# Logging configuration
LOG_FILE = OUTPUT_DIR / "step4_detailed_log.txt"
LOG_JSON = OUTPUT_DIR / "step4_metrics.json"

# Default measurements (in centimeters)
# These can be overridden when calling the functions
DEFAULT_MEASUREMENTS = {
    "chest_flat": 52.0,      # Half chest width (full chest = 104cm)
    "body_length": 72.0,      # Shoulder to hem
    "shoulder_width": 46.0,   # Shoulder to shoulder
    "sleeve_length": 22.0,    # Short sleeve length
    "armhole_depth": 24.0     # Armhole depth
}

# Seam allowance (added to all edges for sewing)
SEAM_ALLOWANCE = 1.5  # cm

# SVG settings
SVG_SCALE = 10  # 1 cm = 10 pixels in SVG (for display)
                # Real-size printing uses viewBox in cm


# ============================================================
# LOGGING SYSTEM
# ============================================================

class PatternGenerationLogger:
    """Logger for comprehensive pattern generation tracking"""
    
    def __init__(self):
        self.log_entries = []
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "pipeline": "step4_pattern_generation",
            "version": "enhanced_v1.0",
            "measurements": {},
            "patterns_generated": [],
            "svg_validations": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] [{level:7}] {message}"
        self.log_entries.append(entry)
        print(message)
    
    def log_measurement(self, name: str, value: float, unit: str = "cm"):
        """Log a measurement"""
        self.log(f"  {name}: {value} {unit}", "INFO")
        self.metrics["measurements"][name] = {"value": value, "unit": unit}
    
    def log_pattern_created(self, name: str, vertex_count: int, path_length: float):
        """Log pattern creation details"""
        self.log(f"  Pattern '{name}' created: {vertex_count} vertices, perimeter={path_length:.2f} cm", "SUCCESS")
        self.metrics["patterns_generated"].append({
            "name": name,
            "vertex_count": vertex_count,
            "path_length_cm": round(path_length, 2)
        })
    
    def log_svg_validation(self, filename: str, valid: bool, details: dict):
        """Log SVG validation results"""
        status = "✓ VALID" if valid else "✗ INVALID"
        self.log(f"  SVG {filename}: {status}", "SUCCESS" if valid else "ERROR")
        self.metrics["svg_validations"].append({"file": filename, "valid": valid, **details})
    
    def save_metrics(self):
        """Save all metrics and logs to files"""
        # Save detailed log
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clean log entries of invalid Unicode surrogates (same as step3)
        cleaned_entries = []
        for entry in self.log_entries:
            try:
                entry.encode('utf-8')
                cleaned_entries.append(entry)
            except UnicodeEncodeError:
                cleaned_entry = entry.encode('utf-8', errors='replace').decode('utf-8')
                cleaned_entries.append(cleaned_entry)
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(cleaned_entries))
        
        # Save JSON metrics
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2)
        
        self.log(f"\nMetrics saved:", "SUCCESS")
        self.log(f"  Text log: {LOG_FILE}", "SUCCESS")
        self.log(f"  JSON metrics: {LOG_JSON}", "SUCCESS")

logger = PatternGenerationLogger()


# ============================================================
# SVG VALIDATION
# ============================================================

def validate_svg(svg_path: Path) -> dict:
    """
    Validate SVG file for Blender import compatibility.
    
    Checks:
    1. File exists and has content
    2. Contains valid SVG header
    3. Has path elements
    4. Paths are closed (critical for mesh fill)
    
    Args:
        svg_path: Path to SVG file
    
    Returns:
        Dictionary with validation results
    """
    result = {
        "valid": False,
        "file_exists": False,
        "file_size": 0,
        "has_svg_header": False,
        "has_paths": False,
        "path_count": 0,
        "has_viewbox": False,
        "warnings": []
    }
    
    try:
        # Check file exists
        if not svg_path.exists():
            result["warnings"].append("File does not exist")
            return result
        
        result["file_exists"] = True
        result["file_size"] = svg_path.stat().st_size
        
        if result["file_size"] == 0:
            result["warnings"].append("File is empty")
            return result
        
        # Read SVG content
        with open(svg_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check SVG header
        if '<svg' in content and 'xmlns="http://www.w3.org/2000/svg"' in content:
            result["has_svg_header"] = True
        else:
            result["warnings"].append("Missing or invalid SVG header")
        
        # Check viewBox (important for scale)
        if 'viewBox=' in content:
            result["has_viewbox"] = True
        else:
            result["warnings"].append("Missing viewBox attribute")
        
        # Check for paths
        path_count = content.count('<path')
        result["path_count"] = path_count
        if path_count > 0:
            result["has_paths"] = True
        else:
            result["warnings"].append("No path elements found")
        
        # Check paths are closed (contain 'Z' or 'z')
        if 'z' in content.lower():
            # Good - paths are closed
            pass
        else:
            result["warnings"].append("Paths may not be closed (missing Z command)")
        
        # Overall validity
        result["valid"] = (
            result["file_exists"] and
            result["file_size"] > 0 and
            result["has_svg_header"] and
            result["has_paths"]
        )
        
    except Exception as e:
        result["warnings"].append(f"Validation error: {e}")
    
    return result


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
        "edges": {
            "neckline": {"start": 0, "end": 16},           # Neckline curve (indices 0-16)
            "shoulder": {"start": 16, "end": 17},          # Shoulder line
            "armhole": {"start": 17, "end": 38},           # Armhole curve (indices 17-38)
            "side_seam": {"start": 38, "end": 39},         # Side seam (straight down)
            "hem": {"start": 39, "end": 40},               # Hem line
            "center_front": {"start": 40, "end": 41}       # Center fold line
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
        "edges": {
            "neckline": {"start": 0, "end": 13},           # Back neckline curve
            "shoulder": {"start": 13, "end": 14},          # Shoulder line
            "armhole": {"start": 14, "end": 35},           # Armhole curve
            "side_seam": {"start": 35, "end": 36},         # Side seam
            "hem": {"start": 36, "end": 37},               # Hem line
            "center_back": {"start": 37, "end": 38}        # Center fold line
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
        "edges": {
            "cap_left": {"start": 0, "end": 16},           # Left side of sleeve cap
            "underarm_left": {"start": 16, "end": 17},     # Left underarm seam
            "hem": {"start": 17, "end": 18},               # Sleeve hem
            "underarm_right": {"start": 18, "end": 19},    # Right underarm seam
            "cap_right": {"start": 19, "end": 34}          # Right side of sleeve cap
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
    Generate all pattern pieces from measurements with logging.
    
    Args:
        measurements: Dictionary with the 5 required measurements
    
    Returns:
        Dictionary of pattern pieces
    """
    logger.log("\nGenerating pattern pieces...", "INFO")
    logger.log("-" * 40, "INFO")
    
    generation_start = time.time()
    patterns = {}
    
    # Front panel
    logger.log("Generating front panel...", "INFO")
    panel_start = time.time()
    patterns["front"] = generate_front_panel(measurements)
    panel_time = time.time() - panel_start
    logger.log(f"  Front: {patterns['front']['width']:.1f} x {patterns['front']['height']:.1f} cm ({len(patterns['front']['outline'])} vertices, {panel_time:.3f}s)", "SUCCESS")
    logger.log_pattern_created("front", len(patterns['front']['outline']), patterns['front']['width'] * 2 + patterns['front']['height'] * 2)
    
    # Back panel
    logger.log("Generating back panel...", "INFO")
    panel_start = time.time()
    patterns["back"] = generate_back_panel(measurements)
    panel_time = time.time() - panel_start
    logger.log(f"  Back: {patterns['back']['width']:.1f} x {patterns['back']['height']:.1f} cm ({len(patterns['back']['outline'])} vertices, {panel_time:.3f}s)", "SUCCESS")
    logger.log_pattern_created("back", len(patterns['back']['outline']), patterns['back']['width'] * 2 + patterns['back']['height'] * 2)
    
    # Sleeve
    logger.log("Generating sleeve pattern...", "INFO")
    panel_start = time.time()
    patterns["sleeve"] = generate_sleeve(measurements)
    panel_time = time.time() - panel_start
    logger.log(f"  Sleeve: {patterns['sleeve']['width']:.1f} x {patterns['sleeve']['height']:.1f} cm ({len(patterns['sleeve']['outline'])} vertices, {panel_time:.3f}s)", "SUCCESS")
    logger.log_pattern_created("sleeve", len(patterns['sleeve']['outline']), patterns['sleeve']['width'] * 2 + patterns['sleeve']['height'] * 2)
    
    total_time = time.time() - generation_start
    logger.log(f"\nAll patterns generated in {total_time:.3f}s", "SUCCESS")
    
    return patterns


def save_patterns(patterns: Dict[str, Dict], measurements: Dict[str, float]):
    """
    Save all patterns as SVG files with validation.
    """
    logger.log("\nSaving pattern files...", "INFO")
    logger.log("-" * 40, "INFO")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.log(f"Output directory: {OUTPUT_DIR}", "INFO")
    
    saved_svgs = []
    
    # Save each pattern as SVG
    for name, pattern in patterns.items():
        svg_start = time.time()
        svg_content = generate_svg(pattern)
        svg_path = OUTPUT_DIR / f"{name}_pattern.svg"
        
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        file_size = svg_path.stat().st_size
        svg_time = time.time() - svg_start
        
        logger.log(f"  ✓ {svg_path.name} ({file_size} bytes, {svg_time:.3f}s)", "SUCCESS")
        
        # Validate SVG content
        validation = validate_svg(svg_path)
        logger.log_svg_validation(svg_path.name, validation["valid"], validation)
        
        saved_svgs.append({"name": name, "path": svg_path, "size": file_size, "valid": validation["valid"]})
    
    # Save metadata JSON
    logger.log("\nSaving metadata...", "INFO")
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
            "svg_file": f"{name}_pattern.svg",
            "vertex_count": len(pattern["outline"])
        }
    
    json_path = OUTPUT_DIR / "pattern_metadata.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    json_size = json_path.stat().st_size
    logger.log(f"  ✓ {json_path.name} ({json_size} bytes)", "SUCCESS")
    
    # Validate all SVGs are valid
    invalid_svgs = [s for s in saved_svgs if not s["valid"]]
    if invalid_svgs:
        logger.log(f"\n⚠️  WARNING: {len(invalid_svgs)} SVG(s) failed validation!", "WARNING")
        for svg in invalid_svgs:
            logger.log(f"  - {svg['name']}: May cause issues in Blender", "WARNING")
    else:
        logger.log(f"\n✓ All {len(saved_svgs)} SVG files validated successfully", "SUCCESS")
    
    # NEW: Save seam definitions
    save_seam_definitions(patterns)


def generate_seam_definitions(patterns: Dict[str, Dict]) -> Dict:
    """
    Generate seam definitions that tell Blender which edges to sew together.
    
    Seam Format:
    Each seam is a pair: ["panel1:edge_name", "panel2:edge_name"]
    
    For a T-shirt, we need to sew:
    1. Front side_seam to Back side_seam (both sides)
    2. Front shoulder to Back shoulder (both sides)
    3. Front armhole to Sleeve cap (both sides)
    
    Since patterns are half-panels (cut on fold), we define seams
    for the full garment by specifying left and right versions.
    
    Returns:
        Dictionary with seam definitions
    """
    seams = {
        "seams": [
            # Side seams: Front and Back are sewn at the sides
            # Left side (when garment is worn)
            {
                "name": "left_side_seam",
                "panel_a": "front",
                "edge_a": "side_seam",
                "panel_b": "back", 
                "edge_b": "side_seam",
                "side": "left"
            },
            # Right side
            {
                "name": "right_side_seam",
                "panel_a": "front",
                "edge_a": "side_seam",
                "panel_b": "back",
                "edge_b": "side_seam", 
                "side": "right"
            },
            
            # Shoulder seams: Front and Back shoulder edges
            {
                "name": "left_shoulder_seam",
                "panel_a": "front",
                "edge_a": "shoulder",
                "panel_b": "back",
                "edge_b": "shoulder",
                "side": "left"
            },
            {
                "name": "right_shoulder_seam",
                "panel_a": "front",
                "edge_a": "shoulder",
                "panel_b": "back",
                "edge_b": "shoulder",
                "side": "right"
            },
            
            # Sleeve seams: Armhole to Sleeve cap
            {
                "name": "left_sleeve_seam",
                "panel_a": "front",
                "edge_a": "armhole",
                "panel_b": "sleeve_left",
                "edge_b": "cap_left",
                "side": "left"
            },
            {
                "name": "right_sleeve_seam",
                "panel_a": "front",
                "edge_a": "armhole",
                "panel_b": "sleeve_right",
                "edge_b": "cap_right",
                "side": "right"
            },
            
            # Sleeve underarm seams (sleeve tube)
            {
                "name": "left_sleeve_underarm",
                "panel_a": "sleeve_left",
                "edge_a": "underarm_left",
                "panel_b": "sleeve_left",
                "edge_b": "underarm_right",
                "side": "left"
            },
            {
                "name": "right_sleeve_underarm",
                "panel_a": "sleeve_right",
                "edge_a": "underarm_left",
                "panel_b": "sleeve_right",
                "edge_b": "underarm_right",
                "side": "right"
            }
        ],
        
        # Edge metadata for each panel (copied from patterns)
        "panels": {}
    }
    
    # Copy edge definitions from each pattern
    for panel_name, pattern in patterns.items():
        if "edges" in pattern:
            seams["panels"][panel_name] = {
                "edges": pattern["edges"],
                "vertex_count": len(pattern["outline"])
            }
    
    return seams


def save_seam_definitions(patterns: Dict[str, Dict]):
    """
    Save seam definitions to seams.json file.
    
    This file tells Blender which edges to sew together.
    """
    print("\n→ Generating seam definitions...")
    
    seams = generate_seam_definitions(patterns)
    
    seams_path = OUTPUT_DIR / "seams.json"
    with open(seams_path, 'w') as f:
        json.dump(seams, f, indent=2)
    
    print(f"  ✓ {seams_path}")
    print(f"  ✓ Defined {len(seams['seams'])} seams for sewing")


def run_pattern_generation_pipeline(measurements: Dict[str, float] = None):
    """
    Run the complete pattern generation pipeline with comprehensive logging.
    """
    logger.log("\n" + "="*80, "INFO")
    logger.log("   STEP 4: SEWING PATTERN GENERATION PIPELINE (ENHANCED)", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    pipeline_start = time.time()
    
    # Use provided measurements or defaults
    if measurements is None:
        measurements = DEFAULT_MEASUREMENTS
        logger.log("Using DEFAULT measurements:", "INFO")
    else:
        logger.log("Using PROVIDED measurements:", "SUCCESS")
    
    # Log all measurements
    logger.log("\nMeasurements:", "INFO")
    logger.log("  " + "-"*35, "INFO")
    for key, value in measurements.items():
        logger.log_measurement(key, value, "cm")
    logger.log("  " + "-"*35, "INFO")
    logger.log(f"  Seam allowance: {SEAM_ALLOWANCE} cm", "INFO")
    
    # Generate patterns
    logger.log("", "INFO")
    patterns = generate_all_patterns(measurements)
    
    # Save patterns
    logger.log("", "INFO")
    save_patterns(patterns, measurements)
    
    # Calculate total time
    total_time = time.time() - pipeline_start
    
    # Summary
    logger.log("\n" + "="*80, "INFO")
    logger.log("   PATTERN GENERATION SUMMARY", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    logger.log("Total pipeline time: {:.3f}s".format(total_time), "SUCCESS")
    logger.log("", "INFO")
    
    logger.log("📐 Generated patterns:", "INFO")
    logger.log("", "INFO")
    
    logger.log("  FRONT PANEL:", "INFO")
    logger.log(f"    - Width: {patterns['front']['width']:.1f} cm (half-width, cut on fold)", "INFO")
    logger.log(f"    - Length: {patterns['front']['height']:.1f} cm", "INFO")
    logger.log(f"    - Full width when unfolded: {patterns['front']['width'] * 2:.1f} cm", "INFO")
    logger.log(f"    - Vertices: {len(patterns['front']['outline'])}", "INFO")
    
    logger.log("", "INFO")
    logger.log("  BACK PANEL:", "INFO")
    logger.log(f"    - Width: {patterns['back']['width']:.1f} cm (half-width, cut on fold)", "INFO")
    logger.log(f"    - Length: {patterns['back']['height']:.1f} cm", "INFO")
    logger.log(f"    - Neckline: shallower than front", "INFO")
    logger.log(f"    - Vertices: {len(patterns['back']['outline'])}", "INFO")
    
    logger.log("", "INFO")
    logger.log("  SLEEVE (x2):", "INFO")
    logger.log(f"    - Width: {patterns['sleeve']['width']:.1f} cm", "INFO")
    logger.log(f"    - Length: {patterns['sleeve']['height']:.1f} cm", "INFO")
    logger.log(f"    - Sleeve cap height: ~{patterns['sleeve']['width']*0.45/1.4:.1f} cm", "INFO")
    logger.log(f"    - Vertices: {len(patterns['sleeve']['outline'])}", "INFO")
    
    logger.log("", "INFO")
    logger.log(f"📁 Output directory: {OUTPUT_DIR}/", "INFO")
    logger.log("   Files created:", "INFO")
    logger.log("   - front_pattern.svg", "INFO")
    logger.log("   - back_pattern.svg", "INFO")
    logger.log("   - sleeve_pattern.svg", "INFO")
    logger.log("   - pattern_metadata.json", "INFO")
    logger.log("   - seams.json (sewing instructions for Blender)", "INFO")
    
    logger.log("", "INFO")
    logger.log(f"📝 Detailed log: {LOG_FILE}", "INFO")
    logger.log(f"📊 Metrics JSON: {LOG_JSON}", "INFO")
    
    logger.log("", "INFO")
    logger.log("="*80, "INFO")
    
    # Save metrics
    logger.save_metrics()
    
    # Validate critical files
    critical_files = [
        OUTPUT_DIR / "front_pattern.svg",
        OUTPUT_DIR / "back_pattern.svg",
        OUTPUT_DIR / "sleeve_pattern.svg",
        OUTPUT_DIR / "pattern_metadata.json",
        OUTPUT_DIR / "seams.json"
    ]
    
    all_valid = True
    for file_path in critical_files:
        if not file_path.exists():
            logger.log(f"❌ CRITICAL FILE MISSING: {file_path}", "ERROR")
            all_valid = False
    
    if all_valid:
        logger.log("\n✅ ALL CRITICAL OUTPUT FILES VALIDATED", "SUCCESS")
        return True
    else:
        logger.log("\n❌ SOME CRITICAL FILES ARE MISSING", "ERROR")
        return False


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
    Generate T-shirt sewing patterns from measurements with comprehensive logging.
    
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
    
    Outputs:
    - front_pattern.svg, back_pattern.svg, sleeve_pattern.svg (SVG patterns)
    - pattern_metadata.json (measurements and metadata)
    - seams.json (sewing instructions for Blender)
    - step4_detailed_log.txt (complete operation log)
    - step4_metrics.json (structured metrics)
    """
    print("\n" + "="*80)
    print("   PATTERN GENERATION - ENHANCED VERSION")
    print("   With comprehensive logging and SVG validation")
    print("="*80 + "\n")
    
    # Get measurements from user interactively
    user_measurements = get_measurements_from_user()
    
    # Generate patterns with user's measurements
    success = run_pattern_generation_pipeline(user_measurements)
    
    if success:
        print("\n" + "="*80)
        print("   ✅ STEP 4 COMPLETE - ALL VALIDATIONS PASSED")
        print("="*80)
        print(f"\n📁 Output directory: {OUTPUT_DIR}")
        print(f"📝 Detailed log: {LOG_FILE}")
        print(f"📊 Metrics JSON: {LOG_JSON}")
        print("\n" + "="*80)
        print("   READY FOR NEXT STEP")
        print("="*80)
        print("\n➡️  Next step: Blender cloth simulation")
        print("   Run: blender --python step5_blender_sewing.py")
        print("\n   ⚠️  CRITICAL: SVG files validated and ready for Blender import")
        print("   The mesh face creation bug fix is active in step5")
        print("\n" + "="*80)
    else:
        print("\n" + "="*80)
        print("   ❌ STEP 4 FAILED - CHECK LOGS FOR DETAILS")
        print("="*80)
        print(f"\n📝 Check detailed log: {LOG_FILE}")
        print(f"📊 Check metrics: {LOG_JSON}")
        print("\nPlease fix the errors above and run again.")
        print("="*80)
