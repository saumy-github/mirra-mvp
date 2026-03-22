"""
Dynamic 2D Pattern Generator for CLO3D
Generates measurement-driven T-shirt pattern pieces
Reads avatar measurements and calculates proper fit with ease
All measurements in centimeters (cm)
"""

import os
import math
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    print("Warning: ezdxf not installed. DXF export will be disabled.")

# Database integration (optional — requires pymongo)
import sys as _sys
_HERE = Path(__file__).parent
_ROOT = _HERE.parent
if str(_HERE) not in _sys.path:
    _sys.path.insert(0, str(_HERE))
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
try:
    from mirra_measurements.db import get_sizes_collection, get_avatar_collection, close_connection
    from mirra_measurements.size_model import create_size_doc, validate_size_doc
    HAS_DB = True
except (ImportError, AttributeError, FileNotFoundError):
    HAS_DB = False
    print("Warning: pymongo/dotenv not installed. Database operations will be disabled.")


@dataclass
class AvatarMeasurements:
    """Body measurements from STAR avatar (centimeters)"""
    height_cm: float
    chest_circumference_cm: float
    waist_circumference_cm: float
    hip_circumference_cm: float
    shoulder_width_cm: float
    gender: str
    user_id: str = "unknown"
    
    @classmethod
    def from_json(cls, json_path: str) -> 'AvatarMeasurements':
        """Load measurements from avatar JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        measurements = data.get('measurements', {})
        return cls(
            height_cm=measurements.get('height_cm', 175.0),
            chest_circumference_cm=measurements.get('chest_circumference_cm', 100.0),
            waist_circumference_cm=measurements.get('waist_circumference_cm', 85.0),
            hip_circumference_cm=measurements.get('hip_circumference_cm', 98.0),
            shoulder_width_cm=measurements.get('shoulder_width_cm', 45.0),
            gender=measurements.get('gender', 'male'),
            user_id=measurements.get('user_id', 'unknown')
        )

    @classmethod
    def from_db(cls, user_id: str) -> 'AvatarMeasurements':
        """
        Load avatar body measurements from the 'measurements' collection in MongoDB.

        Args:
            user_id: The user_id as stored by the avatar pipeline (e.g. 'u_001')
        """
        if not HAS_DB:
            raise RuntimeError(
                "pymongo is not installed. Cannot load from database.\n"
                "Install it with: pip install pymongo python-dotenv"
            )
        collection = get_avatar_collection()
        doc = collection.find_one({"user_id": user_id})
        if doc is None:
            raise ValueError(
                f"No avatar measurements found for user_id='{user_id}' "
                f"in the '{collection.name}' collection."
            )
        return cls(
            height_cm=doc.get('height_cm', 175.0),
            chest_circumference_cm=doc.get('chest_circumference_cm', 100.0),
            waist_circumference_cm=doc.get('waist_circumference_cm', 85.0),
            hip_circumference_cm=doc.get('hip_circumference_cm', 98.0),
            shoulder_width_cm=doc.get('shoulder_width_cm', 45.0),
            gender=doc.get('gender', 'male'),
            user_id=doc.get('user_id', user_id)
        )


@dataclass
class GarmentMeasurements:
    """Calculated garment pattern measurements in centimeters"""
    # Body measurements
    body_height: float
    body_chest: float
    body_shoulder: float
    
    # Calculated garment dimensions (with ease)
    half_chest_width: float       # Half chest circumference + ease
    garment_length: float         # Total garment length
    shoulder_width: float         # Shoulder to shoulder
    neck_width: float            # Neck opening width
    neck_depth_front: float      # Front neck drop
    neck_depth_back: float       # Back neck drop
    sleeve_length: float         # Sleeve length from shoulder
    bicep_width: float           # Bicep circumference
    armhole_depth: float         # Armhole depth
    seam_allowance: float = 1.0  # Seam allowance for all edges
    
    # Fit details
    ease_cm: float = 0           # Wearing ease applied
    fit_type: str = "regular"    # regular, slim, relaxed
    
    @classmethod
    def from_avatar(cls, avatar: AvatarMeasurements, fit_type: str = "regular") -> 'GarmentMeasurements':
        """
        Calculate garment measurements from avatar body measurements.
        
        Applies industry-standard pattern making formulas and ease.
        
        Args:
            avatar: Body measurements from avatar
            fit_type: "slim", "regular", or "relaxed"
        """
        # Determine ease based on fit type
        ease_map = {
            "slim": 4.0,      # 4cm ease (snug fit)
            "regular": 8.0,   # 8cm ease (comfortable)
            "relaxed": 12.0   # 12cm ease (loose)
        }
        ease_cm = ease_map.get(fit_type, 8.0)
        
        # Calculate garment dimensions
        # Chest width = (body chest + ease) / 2
        half_chest_width = (avatar.chest_circumference_cm + ease_cm) / 2
        
        # Garment length = proportion of height (standard t-shirt)
        # Male: 0.40 of height, Female: 0.38 of height
        length_ratio = 0.40 if avatar.gender == 'male' else 0.38
        garment_length = avatar.height_cm * length_ratio
        
        # Shoulder width = body shoulder width
        shoulder_width = avatar.shoulder_width_cm
        
        # Neck width = proportion of shoulder width
        neck_width = shoulder_width * 0.40
        
        # Neck depths (industry standard)
        neck_depth_front = 9.0 if avatar.gender == 'male' else 10.0
        neck_depth_back = 3.0 if avatar.gender == 'male' else 4.0
        
        # Sleeve length = proportion of height
        sleeve_length = avatar.height_cm * 0.12  # ~12% of height
        
        # Bicep width = proportion of chest
        bicep_width = avatar.chest_circumference_cm * 0.38
        
        # Armhole depth = proportion of height
        armhole_depth = avatar.height_cm * 0.12
        
        return cls(
            body_height=avatar.height_cm,
            body_chest=avatar.chest_circumference_cm,
            body_shoulder=avatar.shoulder_width_cm,
            half_chest_width=half_chest_width,
            garment_length=garment_length,
            shoulder_width=shoulder_width,
            neck_width=neck_width,
            neck_depth_front=neck_depth_front,
            neck_depth_back=neck_depth_back,
            sleeve_length=sleeve_length,
            bicep_width=bicep_width,
            armhole_depth=armhole_depth,
            ease_cm=ease_cm,
            fit_type=fit_type
        )

    @classmethod
    def from_sizes_db(cls, size_id: str) -> 'GarmentMeasurements':
        """
        Load pre-computed size measurements directly from the sizes
        collection (flat schema).  No avatar body measurements needed —
        the 10 size fields are used as-is.

        Args:
            size_id: The size_id stored in MongoDB (e.g. 's_001')
        """
        if not HAS_DB:
            raise RuntimeError(
                "pymongo is not installed. Cannot load from database.\n"
                "Install it with: pip install pymongo python-dotenv"
            )
        col = get_sizes_collection()
        doc = col.find_one({"size_id": size_id}, {"_id": 0})
        if doc is None:
            available = [d["size_id"] for d in col.find({}, {"size_id": 1, "_id": 0}).sort("size_id", 1)]
            raise ValueError(
                f"size_id='{size_id}' not found in sizes collection.\n"
                f"Available IDs: {', '.join(available) if available else 'none — run seed first'}"
            )
        return cls(
            # body fields — not stored in sizes collection, use display defaults
            body_height=175.0,
            body_chest=0.0,
            body_shoulder=doc["shoulder_width_cm"],
            # size fields (flat schema — already includes ease)
            half_chest_width=doc["half_chest_width_cm"],
            garment_length=doc["garment_length_cm"],
            shoulder_width=doc["shoulder_width_cm"],
            neck_width=doc["neck_width_cm"],
            neck_depth_front=doc["neck_depth_front_cm"],
            neck_depth_back=doc["neck_depth_back_cm"],
            sleeve_length=doc["sleeve_length_cm"],
            bicep_width=doc["bicep_width_cm"],
            armhole_depth=doc["armhole_depth_cm"],
            seam_allowance=doc["seam_allowance_cm"],
            fit_type=doc.get("fit_type", "regular"),
            ease_cm=0.0,          # ease already baked into stored values
        )

    # Legacy alias kept while older overlap commands still exist.
    from_garments_db = from_sizes_db


class DynamicPatternGenerator:
    """
    Generates measurement-driven T-shirt patterns for CLO3D.
    Automatically calculates proper fit from avatar measurements.
    """
    
    def __init__(self, measurements: GarmentMeasurements):
        self.m = measurements
        self.patterns = {}
        self.curve_smoothness = 6  # Number of points for curves (higher = smoother)
        
        # Track seam lengths for validation
        self.front_armhole_length = 0.0
        self.back_armhole_length = 0.0
        self.sleeve_cap_length = 0.0
        
    def generate_all(self, output_dir: str = "output"):
        """Generate all pattern pieces and export them."""
        base_output = Path(output_dir)
        base_output.mkdir(parents=True, exist_ok=True)

        # Auto-number runs so each pipeline execution creates a new sub-folder
        existing_runs = sorted(
            [d for d in base_output.iterdir() if d.is_dir() and d.name.startswith("run_")],
            key=lambda d: int(d.name.split("_")[1]) if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit() else 0
        )
        next_num = (int(existing_runs[-1].name.split("_")[1]) + 1) if existing_runs else 1
        output_path = base_output / f"run_{next_num:03d}"
        output_path.mkdir(parents=True, exist_ok=True)

        print("\n" + "="*60)
        print("GENERATING MEASUREMENT-DRIVEN PATTERNS")
        print("="*60)
        print(f"Body Measurements:")
        print(f"  Height: {self.m.body_height:.1f} cm")
        print(f"  Chest: {self.m.body_chest:.1f} cm")
        print(f"  Shoulder: {self.m.body_shoulder:.1f} cm")
        print(f"\nGarment Dimensions:")
        print(f"  Fit Type: {self.m.fit_type.upper()}")
        print(f"  Ease: +{self.m.ease_cm:.1f} cm")
        print(f"  Chest Width (half): {self.m.half_chest_width:.1f} cm")
        print(f"  Garment Length: {self.m.garment_length:.1f} cm")
        print(f"  Sleeve Length: {self.m.sleeve_length:.1f} cm")
        print()
        
        # Generate each pattern
        self.patterns['front_panel'] = self.generate_front_panel()
        self.patterns['back_panel'] = self.generate_back_panel()
        
        # Calculate total armhole circumference from body panels
        # For a symmetric pattern: total includes left + right armholes
        # Each sleeve needs to fit into ONE armhole (half the total)
        total_armhole = self.front_armhole_length + self.back_armhole_length
        armhole_per_sleeve = total_armhole / 2  # Each sleeve fits one armhole
        
        print(f"\n💡 Armhole sizing:")
        print(f"  Total armhole (both sides): {total_armhole:.2f} cm")
        print(f"  Per sleeve: {armhole_per_sleeve:.2f} cm")
        
        # Generate sleeves with matched cap circumference
        self.patterns['sleeve_left'] = self.generate_sleeve(target_armhole_length=armhole_per_sleeve)
        self.patterns['sleeve_right'] = self.generate_sleeve(target_armhole_length=armhole_per_sleeve)  # Will mirror in export
        
        # Export to DXF
        if HAS_EZDXF:
            dxf_dir = output_path / "patterns_dxf"
            dxf_dir.mkdir(exist_ok=True)
            self.export_dxf(dxf_dir)
        
        # Export to SVG for visual verification
        svg_dir = output_path / "patterns_svg"
        svg_dir.mkdir(exist_ok=True)
        self.export_svg(svg_dir)
        
        # Export metadata
        self.export_metadata(output_path)
        
        # Seam matching validation
        print("\n" + "="*60)
        print("SEAM MATCHING VALIDATION")
        print("="*60)
        
        # Calculate total armhole length (front + back = both sides)
        total_armhole = self.front_armhole_length + self.back_armhole_length
        armhole_per_sleeve = total_armhole / 2  # Each sleeve fits one armhole
        
        print(f"\nArmhole Circumference (per sleeve):")
        print(f"  Front panel contribution: {self.front_armhole_length/2:.2f} cm")
        print(f"  Back panel contribution:  {self.back_armhole_length/2:.2f} cm")
        print(f"  Total per sleeve:         {armhole_per_sleeve:.2f} cm")
        
        print(f"\nSleeve Cap Circumference:")
        print(f"  Sleeve cap:    {self.sleeve_cap_length:.2f} cm")
        
        # Calculate mismatch (compare per-sleeve values)
        mismatch = abs(armhole_per_sleeve - self.sleeve_cap_length)
        mismatch_percent = (mismatch / armhole_per_sleeve) * 100
        
        print(f"\nMismatch Analysis:")
        print(f"  Difference: {mismatch:.2f} cm ({mismatch_percent:.1f}%)")
        
        if mismatch <= 2.0:
            print(f"  ✅ GOOD - Within acceptable tolerance (±2cm)")
        elif mismatch <= 5.0:
            print(f"  ⚠️  WARNING - Seams may be difficult to match")
        else:
            print(f"  ❌ CRITICAL - Seams will not match, sewing impossible!")
        
        print(f"\n✅ Patterns generated successfully!")
        print(f"   Output: {output_path}")
        print(f"   Pattern pieces: {len(self.patterns)}")

        self.last_run_path = output_path
        return self.patterns
    
    
    def _generate_curve(self, start: Tuple[float, float], end: Tuple[float, float], 
                       control_offset: Tuple[float, float], num_points: int = 6) -> Tuple[List[Tuple[float, float]], float]:
        """
        Generate a smooth quadratic bezier curve.
        
        Args:
            start: Starting point (x, y)
            end: Ending point (x, y)
            control_offset: Offset for control point from midpoint
            num_points: Number of points to generate along curve
            
        Returns:
            Tuple of (points, arc_length):
                - points: List of (x, y) points forming the curve
                - arc_length: Total length of the curve in cm
        """
        # Calculate control point
        mid_x = (start[0] + end[0]) / 2 + control_offset[0]
        mid_y = (start[1] + end[1]) / 2 + control_offset[1]
        
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            # Quadratic Bezier formula: B(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
            x = (1-t)**2 * start[0] + 2*(1-t)*t * mid_x + t**2 * end[0]
            y = (1-t)**2 * start[1] + 2*(1-t)*t * mid_y + t**2 * end[1]
            points.append((x, y))
        
        # Calculate arc length by summing distances between consecutive points
        arc_length = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            arc_length += math.sqrt(dx**2 + dy**2)
        
        return points, arc_length
    
    def generate_front_panel(self) -> List[Tuple[float, float]]:
        """
        Generate front panel pattern with smooth curves.
        
        Returns list of (x, y) coordinates forming a closed polygon.
        """
        print("\n📐 GENERATING FRONT PANEL:")
        points = []
        
        # Calculate center and shoulder positions for symmetric pattern
        center_x = self.m.half_chest_width / 2
        left_shoulder_x = center_x - (self.m.shoulder_width / 2)
        right_shoulder_x = center_x + (self.m.shoulder_width / 2)
        
        print(f"  Pattern width: {self.m.half_chest_width:.2f} cm (full front)")
        print(f"  Center at x={center_x:.2f} cm")
        print(f"  Left shoulder at x={left_shoulder_x:.2f} cm, Right shoulder at x={right_shoulder_x:.2f} cm")
        
        # Bottom edge (hem) - left to right
        points.append((0, 0))
        points.append((self.m.half_chest_width, 0))
        print(f"  Bottom edge: 2 points, width: {self.m.half_chest_width:.2f} cm")
        
        # Right side seam - straight up to armhole
        armhole_start_y = self.m.garment_length - self.m.armhole_depth
        points.append((self.m.half_chest_width, armhole_start_y))
        side_seam_length = armhole_start_y
        print(f"  Right side seam: {side_seam_length:.2f} cm")
        
        # Right armhole curve
        armhole_end_y = self.m.garment_length - self.m.neck_depth_front
        right_armhole_width = self.m.half_chest_width - right_shoulder_x
        
        # Generate smooth right armhole curve (curves inward)
        right_armhole_curve, right_armhole_arc_length = self._generate_curve(
            start=(self.m.half_chest_width, armhole_start_y),
            end=(right_shoulder_x, armhole_end_y),
            control_offset=(-right_armhole_width * 0.3, 0),  # Curve inward
            num_points=self.curve_smoothness
        )
        points.extend(right_armhole_curve[1:])  # Skip first point (already added)
        print(f"  Right armhole curve: {right_armhole_arc_length:.2f} cm ({len(right_armhole_curve)} points)")
        
        # Right shoulder - straight across
        points.append((right_shoulder_x, self.m.garment_length))
        shoulder_length = self.m.shoulder_width / 2
        print(f"  Right shoulder line: {shoulder_length:.2f} cm")
        
        # Front neckline - smooth curve
        neck_half = self.m.neck_width / 2
        neckline_curve, neckline_arc_length = self._generate_curve(
            start=(right_shoulder_x, self.m.garment_length),
            end=(left_shoulder_x, self.m.garment_length),
            control_offset=(0, -self.m.neck_depth_front),  # Curve downward
            num_points=5
        )
        points.extend(neckline_curve[1:-1])  # Exclude endpoints
        print(f"  Neckline curve: {neckline_arc_length:.2f} cm")
        
        # Left shoulder
        points.append((left_shoulder_x, self.m.garment_length))
        print(f"  Left shoulder line: {shoulder_length:.2f} cm")
        
        # Left armhole curve (mirror of right)
        left_armhole_width = left_shoulder_x - 0
        left_armhole_curve, left_armhole_arc_length = self._generate_curve(
            start=(left_shoulder_x, armhole_end_y),
            end=(0, armhole_start_y),
            control_offset=(-left_armhole_width * 0.3, 0),  # Curve inward (toward center)
            num_points=self.curve_smoothness
        )
        points.extend(left_armhole_curve)
        print(f"  Left armhole curve: {left_armhole_arc_length:.2f} cm ({len(left_armhole_curve)} points)")
        
        # Store total armhole length for validation
        self.front_armhole_length = right_armhole_arc_length + left_armhole_arc_length
        
        print(f"  Total points: {len(points)}")
        print(f"  ✓ Front panel complete")
        
        return points
    
    def generate_back_panel(self) -> List[Tuple[float, float]]:
        """
        Generate back panel pattern with smooth curves.
        Similar to front but with shallower neckline.
        """
        print("\n📐 GENERATING BACK PANEL:")
        points = []
        
        # Calculate center and shoulder positions for symmetric pattern
        center_x = self.m.half_chest_width / 2
        left_shoulder_x = center_x - (self.m.shoulder_width / 2)
        right_shoulder_x = center_x + (self.m.shoulder_width / 2)
        
        # Bottom edge (hem)
        points.append((0, 0))
        points.append((self.m.half_chest_width, 0))
        print(f"  Bottom edge: 2 points, width: {self.m.half_chest_width:.2f} cm")
        
        # Right side seam
        armhole_start_y = self.m.garment_length - self.m.armhole_depth
        points.append((self.m.half_chest_width, armhole_start_y))
        side_seam_length = armhole_start_y
        print(f"  Right side seam: {side_seam_length:.2f} cm")
        
        # Right armhole curve
        armhole_end_y = self.m.garment_length - self.m.neck_depth_back
        right_armhole_width = self.m.half_chest_width - right_shoulder_x
        
        right_armhole_curve, right_armhole_arc_length = self._generate_curve(
            start=(self.m.half_chest_width, armhole_start_y),
            end=(right_shoulder_x, armhole_end_y),
            control_offset=(-right_armhole_width * 0.3, 0),
            num_points=self.curve_smoothness
        )
        points.extend(right_armhole_curve[1:])
        print(f"  Right armhole curve: {right_armhole_arc_length:.2f} cm ({len(right_armhole_curve)} points)")
        
        # Right shoulder
        points.append((right_shoulder_x, self.m.garment_length))
        shoulder_length = self.m.shoulder_width / 2
        print(f"  Right shoulder line: {shoulder_length:.2f} cm")
        
        # Back neckline - shallower curve
        neck_half = self.m.neck_width / 2
        neckline_curve, neckline_arc_length = self._generate_curve(
            start=(right_shoulder_x, self.m.garment_length),
            end=(left_shoulder_x, self.m.garment_length),
            control_offset=(0, -self.m.neck_depth_back),  # Shallower
            num_points=4
        )
        points.extend(neckline_curve[1:-1])
        neck_diff = self.m.neck_depth_front - self.m.neck_depth_back
        print(f"  Back neckline curve: {neckline_arc_length:.2f} cm ({neck_diff:.1f} cm shallower than front)")
        
        # Left shoulder
        points.append((left_shoulder_x, self.m.garment_length))
        print(f"  Left shoulder line: {shoulder_length:.2f} cm")
        
        # Left armhole curve
        left_armhole_width = left_shoulder_x - 0
        left_armhole_curve, left_armhole_arc_length = self._generate_curve(
            start=(left_shoulder_x, armhole_end_y),
            end=(0, armhole_start_y),
            control_offset=(-left_armhole_width * 0.3, 0),
            num_points=self.curve_smoothness
        )
        points.extend(left_armhole_curve)
        print(f"  Left armhole curve: {left_armhole_arc_length:.2f} cm ({len(left_armhole_curve)} points)")
        
        # Store total armhole length for validation
        self.back_armhole_length = right_armhole_arc_length + left_armhole_arc_length
        
        print(f"  Total points: {len(points)}")
        print(f"  ✓ Back panel complete")
        
        return points
    
    def generate_sleeve(self, target_armhole_length: float = None) -> List[Tuple[float, float]]:
        """
        Generate sleeve pattern with sleeve cap matched to armhole circumference.
        
        Args:
            target_armhole_length: Target armhole circumference to match (if None, uses default sizing)
        """
        print("\n📐 GENERATING SLEEVE:")
        
        # Sleeve dimensions
        sleeve_width = self.m.bicep_width / 2
        sleeve_length = self.m.sleeve_length
        
        # If target provided, iteratively adjust cap height to match
        if target_armhole_length is not None:
            print(f"  Target armhole: {target_armhole_length:.2f} cm")
            print(f"  Adjusting cap height to match...")
            
            # Iterative solver: binary search for correct cap_height
            # Allow 1-2cm ease (sleeve cap should be slightly larger than armhole)
            target_cap = target_armhole_length + 1.5  # 1.5cm ease
            tolerance = 2.0  # ±2cm is acceptable
            
            # Initial bounds
            min_height = self.m.armhole_depth * 0.2  # 20% minimum
            max_height = self.m.armhole_depth * 1.5  # 150% maximum
            cap_height = self.m.armhole_depth * 0.35  # Start at 35%
            
            iterations = 0
            max_iterations = 20
            
            while iterations < max_iterations:
                # Calculate sleeve cap length for current cap_height
                cap_start_y = sleeve_length - cap_height
                cap_top_x = sleeve_width / 2
                cap_top_y = sleeve_length + cap_height * 0.15
                
                # Calculate right cap
                right_cap_points, right_cap_length = self._generate_curve(
                    start=(sleeve_width, cap_start_y),
                    end=(cap_top_x, cap_top_y),
                    control_offset=(-sleeve_width * 0.15, cap_height * 0.3),
                    num_points=self.curve_smoothness
                )
                
                # Calculate left cap
                left_cap_points, left_cap_length = self._generate_curve(
                    start=(cap_top_x, cap_top_y),
                    end=(0, cap_start_y),
                    control_offset=(sleeve_width * 0.15, cap_height * 0.3),
                    num_points=self.curve_smoothness
                )
                
                current_cap = right_cap_length + left_cap_length
                difference = abs(current_cap - target_cap)
                
                if difference <= tolerance:
                    # Found acceptable match
                    print(f"  ✓ Converged after {iterations+1} iterations")
                    print(f"    Sleeve cap: {current_cap:.2f} cm")
                    print(f"    Target: {target_cap:.2f} cm")
                    print(f"    Difference: {difference:.2f} cm (within ±{tolerance:.1f}cm tolerance)")
                    break
                
                # Adjust cap_height using binary search
                if current_cap < target_cap:
                    # Need more length, increase height
                    min_height = cap_height
                else:
                    # Too much length, decrease height
                    max_height = cap_height
                
                cap_height = (min_height + max_height) / 2
                iterations += 1
            
            if iterations >= max_iterations:
                print(f"  ⚠️  Warning: Max iterations reached, using best approximation")
                print(f"    Sleeve cap: {current_cap:.2f} cm")
                print(f"    Target: {target_cap:.2f} cm")
                print(f"    Difference: {difference:.2f} cm")
        else:
            # Use default cap height (original behavior)
            cap_height = self.m.armhole_depth * 0.35
        
        print(f"  Sleeve width: {sleeve_width:.2f} cm (bicep {self.m.bicep_width:.1f} / 2)")
        print(f"  Sleeve length: {sleeve_length:.2f} cm")
        print(f"  Cap height: {cap_height:.2f} cm ({cap_height/self.m.armhole_depth*100:.1f}% of armhole depth)")
        
        points = []
        
        # Bottom edge (cuff)
        points.append((0, 0))
        points.append((sleeve_width, 0))
        print(f"  Cuff edge: 2 points, width: {sleeve_width:.2f} cm")
        
        # Right seam (underarm)
        cap_start_y = sleeve_length - cap_height
        points.append((sleeve_width, cap_start_y))
        underarm_seam_length = cap_start_y
        print(f"  Right underarm seam: {underarm_seam_length:.2f} cm")
        
        # Sleeve cap - smooth bell curve
        cap_top_x = sleeve_width / 2
        cap_top_y = sleeve_length + cap_height * 0.15  # Slight rise above sleeve length
        
        # Right side of cap
        right_cap, right_cap_arc_length = self._generate_curve(
            start=(sleeve_width, cap_start_y),
            end=(cap_top_x, cap_top_y),
            control_offset=(-sleeve_width * 0.15, cap_height * 0.3),
            num_points=self.curve_smoothness
        )
        points.extend(right_cap[1:])
        print(f"  Right cap curve: {right_cap_arc_length:.2f} cm ({len(right_cap)} points)")
        
        # Left side of cap (mirror)
        left_cap, left_cap_arc_length = self._generate_curve(
            start=(cap_top_x, cap_top_y),
            end=(0, cap_start_y),
            control_offset=(sleeve_width * 0.15, cap_height * 0.3),
            num_points=self.curve_smoothness
        )
        points.extend(left_cap[1:])
        print(f"  Left cap curve: {left_cap_arc_length:.2f} cm ({len(left_cap)} points)")
        
        sleeve_cap_circumference = right_cap_arc_length + left_cap_arc_length
        self.sleeve_cap_length = sleeve_cap_circumference  # Store for validation
        print(f"  Total cap circumference: {sleeve_cap_circumference:.2f} cm")
        
        print(f"  Total points: {len(points)}")
        print(f"  ✓ Sleeve complete")
        
        return points
    
    def export_dxf(self, output_dir: Path):
        """Export patterns as DXF files for CLO3D."""
        if not HAS_EZDXF:
            print("⚠️  ezdxf not available, skipping DXF export")
            return
        
        for name, points in self.patterns.items():
            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            # Add pattern outline as POLYLINE (not LWPOLYLINE - better CLO3D compatibility)
            # CLO3D prefers standard POLYLINE entities
            points_3d = [(x, y, 0) for x, y in points]
            
            # Create polyline with POLYLINE entity (not lightweight)
            polyline = msp.add_polyline3d(points_3d, dxfattribs={'layer': 'CutLine', 'color': 7})
            polyline.close(True)
            
            # Add notches as small lines (better than circles for CLO3D)
            if 'panel' in name:
                # Add notch at shoulder points
                shoulder_points = [p for p in points if p[1] > self.m.garment_length * 0.9]
                for px, py in shoulder_points[:2]:  # First 2 shoulder points
                    # Notch as small perpendicular line (5mm long)
                    msp.add_line((px - 0.25, py, 0), (px + 0.25, py, 0), dxfattribs={'layer': 'Notch', 'color': 1})
            elif 'sleeve' in name:
                # Add notch at sleeve cap top
                top_y = max(p[1] for p in points)
                top_points = [p for p in points if abs(p[1] - top_y) < 1.0]
                if top_points:
                    px, py = top_points[len(top_points)//2]
                    msp.add_line((px - 0.25, py, 0), (px + 0.25, py, 0), dxfattribs={'layer': 'Notch', 'color': 1})
            
            # Add text label
            center_x = sum(p[0] for p in points) / len(points)
            center_y = sum(p[1] for p in points) / len(points)
            msp.add_text(
                name.replace('_', ' ').title(),
                dxfattribs={
                    'layer': 'Text',
                    'height': 5.0,
                    'color': 3
                }
            ).set_placement((center_x, center_y, 0))
            
            # Add grain line (vertical line in center)
            grain_x = center_x
            grain_y_start = min(p[1] for p in points) + 5
            grain_y_end = max(p[1] for p in points) - 5
            msp.add_line(
                (grain_x, grain_y_start, 0),
                (grain_x, grain_y_end, 0),
                dxfattribs={'layer': 'GrainLine', 'color': 5}
            )
            
            # Save DXF file
            output_file = output_dir / f"{name}.dxf"
            doc.saveas(output_file)
            print(f"  ✓ {name}.dxf ({len(points)} points)")
    
    def export_svg(self, output_dir: Path):
        """Export patterns as SVG files for visual verification."""
        for name, points in self.patterns.items():
            # Calculate bounding box
            if not points:
                continue
            
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)
            
            MARGIN = 5  # 5cm margin on each side
            width = max_x - min_x + MARGIN * 2
            height = max_y - min_y + MARGIN * 2

            # SVG scale (1cm = 10px for readability)
            scale = 10.0

            # Offset so all coordinates are positive (translate origin to margin)
            ox = (-min_x + MARGIN) * scale
            oy = (-min_y + MARGIN) * scale

            svg_w = width * scale
            svg_h = height * scale

            # Start SVG - viewBox always starts at 0,0 for maximum viewer compatibility
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{svg_w}" 
     height="{svg_h}" 
     viewBox="0 0 {svg_w} {svg_h}">
    
    <!-- Background -->
    <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="white" stroke="none"/>
    
    <!-- Grid (1cm squares) -->
    <g id="grid" stroke="#e0e0e0" stroke-width="0.5">
'''

            # Add grid lines (translated into positive space)
            for x in range(int(min_x - MARGIN), int(max_x + MARGIN + 1)):
                lx = x * scale + ox
                svg_content += f'    <line x1="{lx}" y1="0" x2="{lx}" y2="{svg_h}"/>\n'
            for y in range(int(min_y - MARGIN), int(max_y + MARGIN + 1)):
                ly = y * scale + oy
                svg_content += f'    <line x1="0" y1="{ly}" x2="{svg_w}" y2="{ly}"/>\n'

            svg_content += '    </g>\n\n'

            # Add pattern outline (translated)
            path_data = "M " + " L ".join([f"{p[0]*scale+ox},{p[1]*scale+oy}" for p in points]) + " Z"
            svg_content += f'''    <!-- Pattern Outline -->
    <path d="{path_data}" 
          fill="#f0f8ff" 
          stroke="#000080" 
          stroke-width="2.0"/>
    
'''

            # Add grain line (translated)
            center_x = sum(p[0] for p in points) / len(points)
            center_y = sum(p[1] for p in points) / len(points)
            grain_y_start = min_y + 5
            grain_y_end = max_y - 5
            gcx = center_x * scale + ox
            gys = grain_y_start * scale + oy
            gye = grain_y_end * scale + oy
            svg_content += f'''    <!-- Grain Line -->
    <line x1="{gcx}" y1="{gys}" 
          x2="{gcx}" y2="{gye}" 
          stroke="#ff0000" stroke-width="1.5" stroke-dasharray="5,5"/>
    <polygon points="{gcx},{gye} {gcx - 0.5*scale},{gye + 1*scale} {gcx + 0.5*scale},{gye + 1*scale}" 
             fill="#ff0000"/>
    
'''

            # Add text label (translated)
            svg_content += f'''    <!-- Label -->
    <text x="{center_x*scale+ox}" y="{center_y*scale+oy}" 
          font-family="Arial" font-size="40" 
          text-anchor="middle" dominant-baseline="middle" 
          fill="#000080" font-weight="bold">
        {name.replace('_', ' ').title()}
    </text>
    
    <!-- Dimensions -->
    <text x="{center_x*scale+ox}" y="{(max_y + MARGIN - 1)*scale+oy}" 
          font-family="Arial" font-size="20" 
          text-anchor="middle" fill="#666">
        Width: {(max_x-min_x):.1f}cm &#xD7; Height: {(max_y-min_y):.1f}cm
    </text>
    
</svg>'''
            
            # Save SVG file
            output_file = output_dir / f"{name}.svg"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"  ✓ {name}.svg (for preview)")
    
    def export_metadata(self, output_dir: Path):
        """Export pattern metadata as JSON."""
        metadata = {
            'garment_type': 'tshirt',
            'version': '2.0',
            'generation_type': 'measurement-driven',
            'body_measurements': {
                'height_cm': self.m.body_height,
                'chest_circumference_cm': self.m.body_chest,
                'shoulder_width_cm': self.m.body_shoulder
            },
            'garment_measurements': {
                'half_chest_width': self.m.half_chest_width,
                'garment_length': self.m.garment_length,
                'shoulder_width': self.m.shoulder_width,
                'neck_width': self.m.neck_width,
                'sleeve_length': self.m.sleeve_length,
                'bicep_width': self.m.bicep_width,
                'armhole_depth': self.m.armhole_depth,
                'seam_allowance': self.m.seam_allowance
            },
            'fit_details': {
                'fit_type': self.m.fit_type,
                'ease_cm': self.m.ease_cm
            },
            'pattern_info': {
                'coordinates': 'seam_line',
                'seam_allowances_included': True,
                'seam_allowance_cm': self.m.seam_allowance,
                'notes': 'Patterns generated at seam line with seam allowances documented below'
            },
            'seam_allowance_specifications': {
                'front_panel': {
                    'bottom_edge': {'allowance_cm': 3.0, 'type': 'hem', 'notes': 'Double fold hem'},
                    'side_seams': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both left and right sides'},
                    'shoulder_seams': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both shoulders'},
                    'armholes': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both armhole curves'},
                    'neckline': {'allowance_cm': 0.5, 'type': 'binding', 'notes': 'Binding or ribbing applied'}
                },
                'back_panel': {
                    'bottom_edge': {'allowance_cm': 3.0, 'type': 'hem', 'notes': 'Double fold hem'},
                    'side_seams': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both left and right sides'},
                    'shoulder_seams': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both shoulders'},
                    'armholes': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Both armhole curves'},
                    'neckline': {'allowance_cm': 0.5, 'type': 'binding', 'notes': 'Binding or ribbing applied'}
                },
                'sleeves': {
                    'cuff_edge': {'allowance_cm': 2.0, 'type': 'hem', 'notes': 'Single or double fold'},
                    'underarm_seam': {'allowance_cm': 1.0, 'type': 'sewing', 'notes': 'Sleeve seam'},
                    'sleeve_cap': {'allowance_cm': 1.5, 'type': 'sewing', 'notes': 'Extra ease for setting into armhole'}
                }
            },
            'pattern_pieces': list(self.patterns.keys()),
            'seam_matching': {
                'armhole_length_cm': (self.front_armhole_length + self.back_armhole_length) / 2,
                'sleeve_cap_length_cm': self.sleeve_cap_length,
                'ease_cm': self.sleeve_cap_length - ((self.front_armhole_length + self.back_armhole_length) / 2),
                'status': 'matched' if abs(self.sleeve_cap_length - ((self.front_armhole_length + self.back_armhole_length) / 2)) <= 2.0 else 'mismatched'
            },
            'seam_connections': [
                {'type': 'shoulder', 'from': 'front_panel', 'to': 'back_panel', 'side': 'left'},
                {'type': 'shoulder', 'from': 'front_panel', 'to': 'back_panel', 'side': 'right'},
                {'type': 'side_seam', 'from': 'front_panel', 'to': 'back_panel', 'side': 'left'},
                {'type': 'side_seam', 'from': 'front_panel', 'to': 'back_panel', 'side': 'right'},
                {'type': 'armhole', 'from': 'sleeve_left', 'to': 'front_panel+back_panel', 'side': 'left'},
                {'type': 'armhole', 'from': 'sleeve_right', 'to': 'front_panel+back_panel', 'side': 'right'},
                {'type': 'sleeve_seam', 'from': 'sleeve_left', 'to': 'sleeve_left'},
                {'type': 'sleeve_seam', 'from': 'sleeve_right', 'to': 'sleeve_right'}
            ],
            'clo3d_import_notes': [
                'Patterns are at seam line (cutting line includes allowances documented above)',
                'When importing to CLO3D, use Segment Sewing tool to connect seams',
                'Apply seam allowances using Transform Pattern → Internal Line → Offset',
                'Or manually add allowances by offsetting edges outward before import',
                'Front and back shoulder lengths should match',
                'Armhole curves should match sleeve cap circumference (validated above)'
            ]
        }
        
        output_file = output_dir / "pattern_metadata.json"
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ pattern_metadata.json (with seam allowance specifications)")

    def save_to_db(self, size_id: str = None, garment_id: str = None) -> bool:
        """Upsert the size record into sizes using the flat schema."""
        if not HAS_DB:
            print("⚠️  Database not available — skipping DB save (pymongo not installed).")
            return False

        resolved_size_id = size_id or garment_id
        if not resolved_size_id or not str(resolved_size_id).startswith("s_"):
            print("⚠️  Skipping DB save because sizes collection expects size_id values like s_001.")
            return False

        doc = create_size_doc(
            size_id=resolved_size_id,
            fit_type=self.m.fit_type,
            half_chest_width_cm=self.m.half_chest_width,
            garment_length_cm=self.m.garment_length,
            shoulder_width_cm=self.m.shoulder_width,
            neck_width_cm=self.m.neck_width,
            neck_depth_front_cm=self.m.neck_depth_front,
            neck_depth_back_cm=self.m.neck_depth_back,
            sleeve_length_cm=self.m.sleeve_length,
            bicep_width_cm=self.m.bicep_width,
            armhole_depth_cm=self.m.armhole_depth,
            seam_allowance_cm=self.m.seam_allowance,
        )

        ok, err = validate_size_doc(doc)
        if not ok:
            print(f"⚠️  Size document validation failed: {err}")
            return False

        try:
            collection = get_sizes_collection()
            collection.update_one(
                {'size_id': resolved_size_id},
                {'$set': doc},
                upsert=True
            )
            print(f"  ✅ Saved to DB  →  sizes  (size_id={resolved_size_id}, fit={self.m.fit_type})")
            return True
        except Exception as exc:
            print(f"⚠️  DB write failed: {exc}")
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate measurement-driven 2D patterns for CLO3D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # DEFAULT — fetch from sizes DB (interactive prompt for ID):
  python generate_patterns_clo3d.py

  # DEFAULT — fetch size s_003 directly from sizes DB:
  python generate_patterns_clo3d.py --size-id s_003

  # Other modes:
  python generate_patterns_clo3d.py --avatar path/to/measurements.json
  python generate_patterns_clo3d.py --manual --height 178 --chest 100 --shoulder 45
  python generate_patterns_clo3d.py --db-user u_001
        """
    )

    # Size ID — the primary user-facing argument for the default DB mode
    parser.add_argument('--size-id', '--garment-id', dest='size_id', type=str, default=None,
                       help='Size ID from the sizes collection (e.g. s_003). '
                            'If omitted the script lists all sizes and prompts.')

    # Advanced / alternate input modes (all optional)
    parser.add_argument('--avatar', type=str, default=None,
                       help='Path to avatar measurements JSON file')
    parser.add_argument('--manual', action='store_true',
                       help='Use manual body measurements (specify with --height / --chest etc.)')
    parser.add_argument('--db-user', type=str, metavar='USER_ID', default=None,
                       help='Load avatar body-measurements from MongoDB by user_id')

    # Manual measurement overrides
    parser.add_argument('--height',   type=float, default=175.0, help='Body height (cm)')
    parser.add_argument('--chest',    type=float, default=100.0, help='Chest circumference (cm)')
    parser.add_argument('--waist',    type=float, default=85.0,  help='Waist circumference (cm)')
    parser.add_argument('--hip',      type=float, default=98.0,  help='Hip circumference (cm)')
    parser.add_argument('--shoulder', type=float, default=45.0,  help='Shoulder width (cm)')
    parser.add_argument('--gender',   type=str,   default='male', choices=['male', 'female'])

    # Fit (only used by avatar / manual modes)
    parser.add_argument('--fit', type=str, choices=['slim', 'regular', 'relaxed'],
                       default='regular', help='Fit type (default: regular)')

    # Output
    parser.add_argument('-o', '--output', help='Output directory',
                       default=str(Path(__file__).parent / 'output'))

    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("DYNAMIC PATTERN GENERATOR FOR CLO3D")
    print("="*60)
    
    # ── Route to the correct input mode ────────────────────────────────────
    # Default (no special flags) or --size-id → sizes DB mode
    use_sizes_db = not args.avatar and not args.manual and not args.db_user

    if args.avatar:
        print(f"\n📁 Loading measurements from: {args.avatar}")
        try:
            avatar = AvatarMeasurements.from_json(args.avatar)
            print(f"✓ Loaded avatar: {avatar.user_id}")
        except FileNotFoundError:
            print(f"❌ Error: File not found: {args.avatar}")
            return
        except Exception as e:
            print(f"❌ Error loading measurements: {e}")
            return
    elif args.db_user:
        print(f"\n🗄️  Loading measurements from DB  (user_id='{args.db_user}')")
        try:
            avatar = AvatarMeasurements.from_db(args.db_user)
            print(f"✓ Loaded avatar: {avatar.user_id}  ({avatar.gender})")
            print(f"  Height: {avatar.height_cm:.1f} cm  |  Chest: {avatar.chest_circumference_cm:.1f} cm  |  Shoulder: {avatar.shoulder_width_cm:.1f} cm")
        except (RuntimeError, ValueError) as e:
            print(f"❌ Error: {e}")
            return
        except Exception as e:
            print(f"❌ Unexpected DB error: {e}")
            return
    elif use_sizes_db:
        # ── Sizes-DB mode: load flat measurements directly from sizes ──
        print(f"\n🗄️  Loading from sizes collection …")

        if not HAS_DB:
            print("❌ DB not available. Install: pip install pymongo python-dotenv")
            return

        col = get_sizes_collection()

        # Resolve size_id — prompt interactively if not supplied via flag
        size_id = args.size_id
        if not size_id:
            all_sizes = list(col.find({}, {"_id": 0}).sort("size_id", 1))
            if not all_sizes:
                print("❌ The sizes collection is empty. Run seed first:")
                print("   python -m mirra_measurements.seed_sizes")
                return

            print(f"\n{'ID':<8} {'Fit Type':<12} {'Half Chest':>11} {'Length':>8} {'Shoulder':>10} {'Sleeve':>8}")
            print("─" * 62)
            for g in all_sizes:
                print(
                    f"  {g['size_id']:<6} "
                    f"{g['fit_type']:<12} "
                    f"{g['half_chest_width_cm']:>9.1f}cm "
                    f"{g['garment_length_cm']:>6.1f}cm "
                    f"{g['shoulder_width_cm']:>8.1f}cm "
                    f"{g['sleeve_length_cm']:>6.1f}cm"
                )
            print()
            size_id = input("Enter size_id to generate patterns for: ").strip()

        try:
            garment = GarmentMeasurements.from_sizes_db(size_id)
        except (RuntimeError, ValueError) as e:
            print(f"❌ Error: {e}")
            return

        print(f"✓ Loaded size_id={size_id}  fit={garment.fit_type}")
        print(f"  Half chest : {garment.half_chest_width:.1f} cm")
        print(f"  Length     : {garment.garment_length:.1f} cm")
        print(f"  Shoulder   : {garment.shoulder_width:.1f} cm")
        print(f"  Sleeve     : {garment.sleeve_length:.1f} cm")

        # Generate patterns directly (no from_avatar step needed)
        generator = DynamicPatternGenerator(garment)
        generator.generate_all(args.output)
        generator.save_to_db(size_id=size_id)

        run_path = generator.last_run_path
        print("\n" + "="*60)
        print("✅ PATTERN GENERATION COMPLETE")
        print("="*60)
        print(f"\n  Size ID      : {size_id}  ({garment.fit_type} fit)")
        print(f"  DXF files    : {run_path / 'patterns_dxf'}")
        print(f"  SVG previews : {run_path / 'patterns_svg'}")
        print(f"\nNext steps:")
        print(f"  1. Open CLO3D")
        print(f"  2. Import avatar  → Avatar › Import Avatar")
        print(f"  3. Import patterns → File › Import › DXF/AAMA (select all .dxf files)")
        print(f"  4. Sew seams and simulate!")
        print()
        return

    else:
        print(f"\n📐 Using manual measurements")
        avatar = AvatarMeasurements(
            height_cm=args.height,
            chest_circumference_cm=args.chest,
            waist_circumference_cm=args.waist,
            hip_circumference_cm=args.hip,
            shoulder_width_cm=args.shoulder,
            gender=args.gender,
            user_id="manual_input"
        )

    # Calculate garment measurements (avatar / manual / file modes)
    garment = GarmentMeasurements.from_avatar(avatar, fit_type=args.fit)
    
    # Generate patterns
    generator = DynamicPatternGenerator(garment)
    generator.generate_all(args.output)

    # Legacy avatar/manual modes intentionally do not write into sizes because
    # the canonical sizes collection is now a source-of-truth input collection.

    print("\n" + "="*60)
    print("✅ PATTERN GENERATION COMPLETE")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. Open CLO3D")
    print(f"2. Import avatar: CLO3D → Avatar → Import Avatar")
    print(f"3. Import patterns: CLO3D → File → Import → DXF/AAMA")
    print(f"4. Select all 4 DXF files from: {generator.last_run_path / 'patterns_dxf'}/")
    print(f"5. Use Segment Sewing tool to connect seams")
    print(f"6. Assign fabric properties and simulate!")
    print()


if __name__ == "__main__":
    main()
