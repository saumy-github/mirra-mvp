"""
Step 4: Pattern Generation

Generates SVG pattern pieces for garment construction:
- Front bodice
- Back bodice
- Sleeve
- Neck band

All measurements in centimeters (cm).
"""

import numpy as np
import json
import os
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import math

import sys
sys.path.append('..')
from config.pipeline_config import PatternGenerationConfig, Measurements


@dataclass
class Point:
    """2D point for pattern construction"""
    x: float
    y: float
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point':
        return Point(self.x * scalar, self.y * scalar)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


@dataclass 
class BezierCurve:
    """Cubic Bezier curve defined by 4 control points"""
    p0: Point  # Start point
    p1: Point  # Control point 1
    p2: Point  # Control point 2
    p3: Point  # End point
    
    def to_svg_path(self) -> str:
        return f"C {self.p1.x:.2f},{self.p1.y:.2f} {self.p2.x:.2f},{self.p2.y:.2f} {self.p3.x:.2f},{self.p3.y:.2f}"
    
    def get_point(self, t: float) -> Point:
        """Get point on curve at parameter t (0-1)"""
        x = (1-t)**3 * self.p0.x + 3*(1-t)**2*t * self.p1.x + 3*(1-t)*t**2 * self.p2.x + t**3 * self.p3.x
        y = (1-t)**3 * self.p0.y + 3*(1-t)**2*t * self.p1.y + 3*(1-t)*t**2 * self.p2.y + t**3 * self.p3.y
        return Point(x, y)
    
    def approximate_length(self, segments: int = 100) -> float:
        """Approximate curve length by sampling"""
        length = 0.0
        prev = self.p0
        for i in range(1, segments + 1):
            t = i / segments
            curr = self.get_point(t)
            length += prev.distance_to(curr)
            prev = curr
        return length


@dataclass
class PatternPiece:
    """A single pattern piece with outline and notches"""
    name: str
    outline: List[Point]
    curves: List[BezierCurve] = field(default_factory=list)
    notches: List[Point] = field(default_factory=list)
    grain_line: Tuple[Point, Point] = None
    seam_allowance: float = 1.0  # cm
    
    def get_perimeter(self) -> float:
        """Calculate perimeter of the pattern piece"""
        perimeter = 0.0
        
        # Add straight line segments
        for i in range(len(self.outline) - 1):
            perimeter += self.outline[i].distance_to(self.outline[i+1])
        
        # Close the shape
        if self.outline:
            perimeter += self.outline[-1].distance_to(self.outline[0])
        
        # Add curve lengths
        for curve in self.curves:
            perimeter += curve.approximate_length()
        
        return perimeter


@dataclass
class PatternSet:
    """Complete set of pattern pieces"""
    pieces: Dict[str, PatternPiece]
    metadata: Dict
    measurements: Measurements


class PatternGenerator:
    """
    Generates pattern pieces based on measurements.
    Uses parametric construction for accurate pattern drafting.
    """
    
    # Scale factor for SVG output (1cm = 10px for readable SVGs)
    SVG_SCALE = 10.0
    
    def __init__(self, config: Optional[PatternGenerationConfig] = None):
        self.config = config or PatternGenerationConfig()
        self.m = self.config.measurements
        
    def generate_all_pieces(self) -> PatternSet:
        """Generate all pattern pieces."""
        pieces = {
            'front_bodice': self.generate_front_bodice(),
            'back_bodice': self.generate_back_bodice(),
            'sleeve': self.generate_sleeve(),
            'neck_band': self.generate_neck_band(
                self._calculate_neckline_perimeter()
            )
        }
        
        metadata = self._generate_metadata(pieces)
        
        return PatternSet(
            pieces=pieces,
            metadata=metadata,
            measurements=self.m
        )
    
    def generate_front_bodice(self) -> PatternPiece:
        """
        Generate front bodice pattern piece.
        
        Construction points (from top-left, clockwise):
        - Center front neck
        - Shoulder point
        - Armhole curve
        - Side seam
        - Hem
        """
        points = []
        curves = []
        
        # Key measurements
        half_chest = self.m.half_chest_width / 2  # Quarter chest for front
        length = self.m.garment_length
        shoulder = self.m.shoulder_width / 2
        armhole = self.m.armhole_depth
        neck_w = self.m.neck_width / 2
        neck_d = self.m.neck_depth_front
        hem = self.m.hem_width / 2
        
        # Point 0: Center front at neck (origin)
        p0 = Point(0, 0)
        
        # Point 1: Neck curve end (at shoulder)
        p1 = Point(neck_w, 0)
        
        # Point 2: Shoulder point
        p2 = Point(shoulder, -1.5)  # Slight shoulder slope
        
        # Point 3: Armhole start (underarm)
        p3 = Point(half_chest, armhole)
        
        # Point 4: Side seam at hem
        p4 = Point(hem, length)
        
        # Point 5: Center front at hem
        p5 = Point(0, length)
        
        # Build outline
        points = [p0, p1, p2, p3, p4, p5]
        
        # Create neckline curve (bezier from p0 to p1)
        neck_curve = self._create_neckline_curve(p0, p1, neck_d, is_front=True)
        curves.append(neck_curve)
        
        # Create armhole curve (cubic bezier from p2 to p3)
        armhole_curve = self._create_armhole_curve(p2, p3)
        curves.append(armhole_curve)
        
        # Add notches for matching
        notches = [
            Point(shoulder / 2, -0.75),  # Shoulder notch
            Point(half_chest, armhole / 2),  # Armhole notch
        ]
        
        # Grain line (vertical, center of piece)
        grain_start = Point(neck_w / 2, armhole)
        grain_end = Point(neck_w / 2, length - 10)
        
        return PatternPiece(
            name="front_bodice",
            outline=points,
            curves=curves,
            notches=notches,
            grain_line=(grain_start, grain_end)
        )
    
    def generate_back_bodice(self) -> PatternPiece:
        """
        Generate back bodice pattern piece.
        Similar to front but with shallower neckline.
        """
        points = []
        curves = []
        
        # Key measurements
        half_chest = self.m.half_chest_width / 2
        length = self.m.garment_length
        shoulder = self.m.shoulder_width / 2
        armhole = self.m.armhole_depth
        neck_w = self.m.neck_width / 2
        neck_d = self.m.neck_depth_back
        hem = self.m.hem_width / 2
        
        # Point 0: Center back at neck
        p0 = Point(0, 0)
        
        # Point 1: Neck curve end
        p1 = Point(neck_w, 0)
        
        # Point 2: Shoulder point
        p2 = Point(shoulder, -1.5)
        
        # Point 3: Armhole start
        p3 = Point(half_chest, armhole)
        
        # Point 4: Side seam at hem
        p4 = Point(hem, length)
        
        # Point 5: Center back at hem
        p5 = Point(0, length)
        
        points = [p0, p1, p2, p3, p4, p5]
        
        # Create neckline curve
        neck_curve = self._create_neckline_curve(p0, p1, neck_d, is_front=False)
        curves.append(neck_curve)
        
        # Create armhole curve
        armhole_curve = self._create_armhole_curve(p2, p3)
        curves.append(armhole_curve)
        
        notches = [
            Point(shoulder / 2, -0.75),
            Point(half_chest, armhole / 2),
        ]
        
        grain_start = Point(neck_w / 2, armhole)
        grain_end = Point(neck_w / 2, length - 10)
        
        return PatternPiece(
            name="back_bodice",
            outline=points,
            curves=curves,
            notches=notches,
            grain_line=(grain_start, grain_end)
        )
    
    def generate_sleeve(self) -> PatternPiece:
        """
        Generate sleeve pattern piece with sleeve cap.
        """
        points = []
        curves = []
        
        # Key measurements
        sleeve_length = self.m.sleeve_length
        bicep = self.m.bicep_width / 2  # Half bicep for one side
        cap_height = self.m.armhole_depth + self.m.sleeve_cap_height_offset
        ease = 1 + (self.config.sleeve_cap_ease_percent / 100)
        
        # Sleeve head width with ease
        head_width = bicep * ease
        
        # Point 0: Top center of sleeve cap
        p0 = Point(0, 0)
        
        # Point 1: Right sleeve cap edge
        p1 = Point(head_width, cap_height)
        
        # Point 2: Right hem
        p2 = Point(head_width * 0.85, sleeve_length)  # Tapered
        
        # Point 3: Left hem
        p3 = Point(-head_width * 0.85, sleeve_length)
        
        # Point 4: Left sleeve cap edge
        p4 = Point(-head_width, cap_height)
        
        points = [p0, p1, p2, p3, p4]
        
        # Create sleeve cap curves
        right_cap = self._create_sleeve_cap_curve(p0, p1, is_right=True)
        left_cap = self._create_sleeve_cap_curve(p0, p4, is_right=False)
        curves.extend([right_cap, left_cap])
        
        # Notches for matching to armhole
        notches = [
            Point(0, 0),  # Top center - shoulder notch
            Point(head_width * 0.7, cap_height * 0.6),  # Front notch
            Point(-head_width * 0.7, cap_height * 0.6),  # Back notch
        ]
        
        # Grain line
        grain_start = Point(0, cap_height + 5)
        grain_end = Point(0, sleeve_length - 5)
        
        return PatternPiece(
            name="sleeve",
            outline=points,
            curves=curves,
            notches=notches,
            grain_line=(grain_start, grain_end)
        )
    
    def generate_neck_band(self, neckline_perimeter: float) -> PatternPiece:
        """
        Generate neck band/collar piece.
        
        Args:
            neckline_perimeter: Total neckline length (from front + back bodice)
        """
        # Apply reduction for stretch
        reduction = 1 - (self.config.neck_band_length_reduction_percent / 100)
        band_length = neckline_perimeter * reduction
        band_height = self.config.neck_band_height
        
        # Simple rectangular band
        p0 = Point(0, 0)
        p1 = Point(band_length, 0)
        p2 = Point(band_length, band_height)
        p3 = Point(0, band_height)
        
        points = [p0, p1, p2, p3]
        
        # Center notch for matching to center back
        notches = [
            Point(band_length / 2, 0),  # Center
            Point(band_length / 4, 0),  # Quarter marks
            Point(band_length * 3 / 4, 0),
        ]
        
        return PatternPiece(
            name="neck_band",
            outline=points,
            curves=[],
            notches=notches,
            grain_line=(Point(5, band_height/2), Point(band_length - 5, band_height/2))
        )
    
    def _create_neckline_curve(
        self, 
        start: Point, 
        end: Point, 
        depth: float,
        is_front: bool
    ) -> BezierCurve:
        """Create a bezier curve for the neckline."""
        if is_front:
            # Front neckline curves down more
            c1 = Point(start.x, start.y + depth * 0.5)
            c2 = Point(end.x - depth * 0.3, end.y + depth * 0.5)
        else:
            # Back neckline is shallower
            c1 = Point(start.x, start.y + depth * 0.3)
            c2 = Point(end.x - depth * 0.2, end.y + depth * 0.2)
        
        return BezierCurve(start, c1, c2, end)
    
    def _create_armhole_curve(
        self, 
        shoulder: Point, 
        underarm: Point
    ) -> BezierCurve:
        """Create a cubic bezier curve for the armhole."""
        # Control points for smooth armhole
        c1 = Point(
            shoulder.x + (underarm.x - shoulder.x) * 0.1,
            shoulder.y + (underarm.y - shoulder.y) * 0.4
        )
        c2 = Point(
            underarm.x,
            underarm.y - (underarm.y - shoulder.y) * 0.3
        )
        
        return BezierCurve(shoulder, c1, c2, underarm)
    
    def _create_sleeve_cap_curve(
        self, 
        top: Point, 
        edge: Point,
        is_right: bool
    ) -> BezierCurve:
        """Create sleeve cap curve."""
        cap_height = abs(edge.y - top.y)
        
        if is_right:
            c1 = Point(top.x + cap_height * 0.4, top.y + cap_height * 0.2)
            c2 = Point(edge.x - cap_height * 0.2, edge.y - cap_height * 0.3)
        else:
            c1 = Point(top.x - cap_height * 0.4, top.y + cap_height * 0.2)
            c2 = Point(edge.x + cap_height * 0.2, edge.y - cap_height * 0.3)
        
        return BezierCurve(top, c1, c2, edge)
    
    def _calculate_neckline_perimeter(self) -> float:
        """Calculate total neckline perimeter (front + back)."""
        # Approximate neckline as ellipse arcs
        neck_w = self.m.neck_width / 2
        
        # Front neckline (deeper)
        front_depth = self.m.neck_depth_front
        front_length = math.pi * math.sqrt((neck_w**2 + front_depth**2) / 2) / 2
        
        # Back neckline (shallower)
        back_depth = self.m.neck_depth_back
        back_length = math.pi * math.sqrt((neck_w**2 + back_depth**2) / 2) / 2
        
        # Total (both sides)
        return 2 * (front_length + back_length)
    
    def _generate_metadata(self, pieces: Dict[str, PatternPiece]) -> Dict:
        """Generate metadata for the pattern set."""
        return {
            "version": "2.0",
            "unit": "cm",
            "pieces": {
                name: {
                    "vertex_count": len(piece.outline),
                    "has_curves": len(piece.curves) > 0,
                    "notch_count": len(piece.notches),
                    "perimeter_cm": round(piece.get_perimeter(), 2)
                }
                for name, piece in pieces.items()
            },
            "measurements": {
                "half_chest_width": self.m.half_chest_width,
                "garment_length": self.m.garment_length,
                "shoulder_width": self.m.shoulder_width,
                "armhole_depth": self.m.armhole_depth,
                "sleeve_length": self.m.sleeve_length,
                "bicep_width": self.m.bicep_width,
                "neck_width": self.m.neck_width,
                "neck_depth_front": self.m.neck_depth_front,
                "neck_depth_back": self.m.neck_depth_back
            }
        }


class SVGExporter:
    """Exports pattern pieces to SVG format."""
    
    # Scale: 1cm = 10 SVG units for readability
    SCALE = 10.0
    
    # SVG styling
    STROKE_COLOR = "#000000"
    STROKE_WIDTH = 0.5
    NOTCH_COLOR = "#FF0000"
    GRAIN_COLOR = "#0000FF"
    
    def __init__(self, output_directory: str = "pattern_output"):
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_piece(self, piece: PatternPiece) -> str:
        """
        Export a single pattern piece to SVG.
        
        Returns:
            Path to the saved SVG file
        """
        # Calculate bounding box
        all_x = [p.x for p in piece.outline]
        all_y = [p.y for p in piece.outline]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Add margin
        margin = 20
        width = (max_x - min_x) * self.SCALE + 2 * margin
        height = (max_y - min_y) * self.SCALE + 2 * margin
        
        # Offset for centering
        offset_x = -min_x * self.SCALE + margin
        offset_y = -min_y * self.SCALE + margin
        
        # Build SVG content
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" ',
            f'width="{width:.0f}" height="{height:.0f}" ',
            f'viewBox="0 0 {width:.0f} {height:.0f}">',
            f'  <title>{piece.name}</title>',
            f'  <desc>Pattern piece: {piece.name}</desc>',
            f'  <g transform="translate({offset_x:.2f}, {offset_y:.2f})">',
        ]
        
        # Draw main outline - using fill for proper mesh conversion
        path_d = self._build_path(piece)
        svg_parts.append(
            f'    <path d="{path_d}" '
            f'fill="#CCCCCC" stroke="{self.STROKE_COLOR}" '
            f'stroke-width="{self.STROKE_WIDTH}"/>'
        )
        
        # Draw notches
        for notch in piece.notches:
            nx = notch.x * self.SCALE
            ny = notch.y * self.SCALE
            svg_parts.append(
                f'    <circle cx="{nx:.2f}" cy="{ny:.2f}" r="3" '
                f'fill="{self.NOTCH_COLOR}"/>'
            )
        
        # Draw grain line
        if piece.grain_line:
            g1, g2 = piece.grain_line
            svg_parts.append(
                f'    <line x1="{g1.x * self.SCALE:.2f}" y1="{g1.y * self.SCALE:.2f}" '
                f'x2="{g2.x * self.SCALE:.2f}" y2="{g2.y * self.SCALE:.2f}" '
                f'stroke="{self.GRAIN_COLOR}" stroke-width="1" '
                f'stroke-dasharray="5,5"/>'
            )
            # Arrow head
            svg_parts.append(
                f'    <polygon points="'
                f'{g2.x * self.SCALE:.2f},{g2.y * self.SCALE - 5:.2f} '
                f'{g2.x * self.SCALE - 3:.2f},{g2.y * self.SCALE:.2f} '
                f'{g2.x * self.SCALE + 3:.2f},{g2.y * self.SCALE:.2f}" '
                f'fill="{self.GRAIN_COLOR}"/>'
            )
        
        # Add piece label
        center_x = (min_x + max_x) / 2 * self.SCALE
        center_y = (min_y + max_y) / 2 * self.SCALE
        svg_parts.append(
            f'    <text x="{center_x:.2f}" y="{center_y:.2f}" '
            f'text-anchor="middle" font-size="12" font-family="Arial">'
            f'{piece.name.replace("_", " ").title()}</text>'
        )
        
        svg_parts.extend([
            '  </g>',
            '</svg>'
        ])
        
        # Write file
        svg_content = '\n'.join(svg_parts)
        output_path = self.output_dir / f"{piece.name}.svg"
        
        with open(output_path, 'w') as f:
            f.write(svg_content)
        
        return str(output_path)
    
    def _build_path(self, piece: PatternPiece) -> str:
        """Build SVG path data for the piece outline."""
        if not piece.outline:
            return ""
        
        # Start at first point
        p0 = piece.outline[0]
        path = f"M {p0.x * self.SCALE:.2f},{p0.y * self.SCALE:.2f}"
        
        # Check if we have curves to substitute for line segments
        curve_starts = {(c.p0.x, c.p0.y): c for c in piece.curves}
        
        # Draw to each subsequent point
        for i in range(1, len(piece.outline)):
            prev = piece.outline[i-1]
            curr = piece.outline[i]
            
            # Check if there's a curve from prev to curr
            curve = curve_starts.get((prev.x, prev.y))
            if curve and abs(curve.p3.x - curr.x) < 0.1 and abs(curve.p3.y - curr.y) < 0.1:
                # Use curve
                path += f" C {curve.p1.x * self.SCALE:.2f},{curve.p1.y * self.SCALE:.2f} "
                path += f"{curve.p2.x * self.SCALE:.2f},{curve.p2.y * self.SCALE:.2f} "
                path += f"{curve.p3.x * self.SCALE:.2f},{curve.p3.y * self.SCALE:.2f}"
            else:
                # Use straight line
                path += f" L {curr.x * self.SCALE:.2f},{curr.y * self.SCALE:.2f}"
        
        # Close path
        path += " Z"
        
        return path
    
    def export_all(self, pattern_set: PatternSet) -> List[str]:
        """Export all pieces in the pattern set."""
        paths = []
        
        for name, piece in pattern_set.pieces.items():
            path = self.export_piece(piece)
            paths.append(path)
            print(f"Exported: {path}")
        
        # Export metadata
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(pattern_set.metadata, f, indent=2)
        paths.append(str(metadata_path))
        
        return paths


class DXFExporter:
    """
    Export pattern pieces to DXF format for CLO3D.
    
    DXF is the standard CAD format that CLO3D uses for pattern import.
    All measurements are in centimeters.
    """
    
    def __init__(self, output_directory: str = "patterns_dxf"):
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_piece(self, piece: PatternPiece) -> str:
        """Export a single pattern piece to DXF."""
        try:
            import ezdxf
        except ImportError:
            raise ImportError(
                "ezdxf is required for DXF export. Install with: pip install ezdxf"
            )
        
        # Create new DXF document
        doc = ezdxf.new('R2010')  # AutoCAD 2010 format (widely compatible)
        msp = doc.modelspace()
        
        # Create layer for pattern outline
        doc.layers.new(name='PATTERN_OUTLINE', dxfattribs={'color': 7})
        doc.layers.new(name='NOTCHES', dxfattribs={'color': 1})
        doc.layers.new(name='GRAIN_LINE', dxfattribs={'color': 3})
        
        # Draw pattern outline as LWPOLYLINE (closed)
        points = []
        curve_segments = {(c.p0.x, c.p0.y): c for c in piece.curves}
        
        for i in range(len(piece.outline)):
            curr = piece.outline[i]
            
            # Check if there's a curve starting from this point
            curve = curve_segments.get((curr.x, curr.y))
            
            if curve:
                # Approximate curve with line segments (CLO3D will handle smoothing)
                samples = 20
                for j in range(samples + 1):
                    t = j / samples
                    p = curve.get_point(t)
                    points.append((p.x, p.y))
            else:
                # Regular point
                points.append((curr.x, curr.y))
        
        # Create closed polyline
        msp.add_lwpolyline(
            points,
            close=True,
            dxfattribs={'layer': 'PATTERN_OUTLINE'}
        )
        
        # Add notches as small lines
        for notch in piece.notches:
            # Draw notch as perpendicular line (3cm long)
            msp.add_line(
                (notch.x - 1.5, notch.y),
                (notch.x + 1.5, notch.y),
                dxfattribs={'layer': 'NOTCHES'}
            )
        
        # Add grain line if present
        if piece.grain_line:
            start, end = piece.grain_line
            msp.add_line(
                (start.x, start.y),
                (end.x, end.y),
                dxfattribs={'layer': 'GRAIN_LINE'}
            )
            
            # Add arrow at grain line start
            msp.add_circle(
                (start.x, start.y),
                radius=1.0,
                dxfattribs={'layer': 'GRAIN_LINE'}
            )
        
        # Add text label with piece name
        bounds = self._calculate_bounds(piece.outline)
        center_x = (bounds['min_x'] + bounds['max_x']) / 2
        center_y = (bounds['min_y'] + bounds['max_y']) / 2
        
        msp.add_text(
            piece.name.replace('_', ' ').title(),
            dxfattribs={
                'insert': (center_x, center_y),
                'height': 5,
                'layer': 'PATTERN_OUTLINE'
            }
        )
        
        # Save DXF file
        output_path = self.output_dir / f"{piece.name}.dxf"
        doc.saveas(str(output_path))
        
        print(f"  Exported DXF: {output_path}")
        return str(output_path)
    
    def _calculate_bounds(self, points: List[Point]) -> Dict[str, float]:
        """Calculate bounding box of points."""
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return {
            'min_x': min(xs),
            'max_x': max(xs),
            'min_y': min(ys),
            'max_y': max(ys)
        }
    
    def export_all(self, pattern_set: PatternSet) -> List[str]:
        """Export all pieces in the pattern set to DXF."""
        paths = []
        
        print(f"\nExporting {len(pattern_set.pieces)} patterns to DXF...")
        
        for name, piece in pattern_set.pieces.items():
            path = self.export_piece(piece)
            paths.append(path)
        
        # Export metadata as JSON
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(pattern_set.metadata, f, indent=2)
        paths.append(str(metadata_path))
        
        print(f"\n✓ All DXF patterns exported to: {self.output_dir}")
        print(f"  Ready for import into CLO3D!")
        
        return paths


def generate_patterns(
    config: Optional[PatternGenerationConfig] = None,
    output_directory: str = "pattern_output",
    export_dxf: bool = False
) -> PatternSet:
    """
    Convenience function to generate all pattern pieces.
    
    Args:
        config: Optional pattern configuration
        output_directory: Directory for SVG output
        export_dxf: If True, also export DXF files for CLO3D
        
    Returns:
        PatternSet with all pieces
    """
    generator = PatternGenerator(config)
    pattern_set = generator.generate_all_pieces()
    
    # Always export SVG
    svg_exporter = SVGExporter(output_directory)
    svg_exporter.export_all(pattern_set)
    
    # Optionally export DXF
    if export_dxf:
        dxf_dir = str(Path(output_directory) / "dxf")
        dxf_exporter = DXFExporter(dxf_dir)
        dxf_exporter.export_all(pattern_set)
    
    return pattern_set


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate garment patterns")
    parser.add_argument(
        "-o", "--output", 
        help="Output directory", 
        default="pattern_output"
    )
    parser.add_argument(
        "--dxf",
        action="store_true",
        help="Export patterns as DXF for CLO3D"
    )
    parser.add_argument(
        "--chest", 
        type=float, 
        help="Half chest width (cm)"
    )
    parser.add_argument(
        "--length", 
        type=float, 
        help="Garment length (cm)"
    )
    
    args = parser.parse_args()
    
    # Create config with custom measurements if provided
    config = PatternGenerationConfig()
    
    if args.chest:
        config.measurements.half_chest_width = args.chest
    if args.length:
        config.measurements.garment_length = args.length
    
    # Generate patterns
    pattern_set = generate_patterns(config, args.output, export_dxf=args.dxf)
    
    print(f"\nGenerated {len(pattern_set.pieces)} pattern pieces:")
    for name, piece in pattern_set.pieces.items():
        print(f"  - {name}: {len(piece.outline)} vertices, perimeter: {piece.get_perimeter():.1f} cm")
