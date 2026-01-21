#!/usr/bin/env python3
from typing import Dict
import numpy as np


# Extract height as vertical range (max_y - min_y) in cm
def extract_height_from_mesh(vertices: np.ndarray, debug: bool = False) -> float:
    min_y = vertices[:, 1].min()
    max_y = vertices[:, 1].max()
    height_m = max_y - min_y
    height_cm = height_m * 100.0
    
    if debug:
        print(f"[DEBUG] Height: min_y={min_y:.4f}m, max_y={max_y:.4f}m, height={height_cm:.2f}cm")
    
    return height_cm


# Extract shoulder width using upper-torso y-band and x-range
def extract_shoulder_width_from_mesh(
    vertices: np.ndarray, 
    y_percentile: float = 0.85, 
    band_thickness: float = 0.02, 
    debug: bool = False
) -> float:
    min_y = vertices[:, 1].min()
    max_y = vertices[:, 1].max()
    y_range = max_y - min_y
    
    band_center_y = min_y + y_percentile * y_range
    band_half_thickness = band_thickness / 2.0
    
    mask = (
        (vertices[:, 1] >= band_center_y - band_half_thickness) & 
        (vertices[:, 1] <= band_center_y + band_half_thickness)
    )
    band_vertices = vertices[mask]
    
    if len(band_vertices) == 0:
        raise ValueError(
            f"Shoulder width: No vertices in y-band at percentile {y_percentile:.2f}. "
            f"Check mesh validity or adjust percentile/band_thickness."
        )
    
    min_x = band_vertices[:, 0].min()
    max_x = band_vertices[:, 0].max()
    shoulder_width_m = max_x - min_x
    shoulder_width_cm = shoulder_width_m * 100.0
    
    if debug:
        print(
            f"[DEBUG] Shoulder: band_center_y={band_center_y:.4f}m, "
            f"vertices_in_band={len(band_vertices)}, width={shoulder_width_cm:.2f}cm"
        )
    
    return shoulder_width_cm


# Extract circumference using thin y-band and ellipse approximation from width (x-range) and depth (z-range)
def extract_circumference_from_mesh(
    vertices: np.ndarray, 
    y_percentile: float, 
    band_thickness: float = 0.02, 
    debug: bool = False, 
    name: str = "circumference"
) -> float:
    min_y = vertices[:, 1].min()
    max_y = vertices[:, 1].max()
    y_range = max_y - min_y
    
    band_center_y = min_y + y_percentile * y_range
    band_half_thickness = band_thickness / 2.0
    
    mask = (
        (vertices[:, 1] >= band_center_y - band_half_thickness) & 
        (vertices[:, 1] <= band_center_y + band_half_thickness)
    )
    band_vertices = vertices[mask]
    
    if len(band_vertices) == 0:
        raise ValueError(
            f"{name} circumference: No vertices in y-band at percentile {y_percentile:.2f}. "
            f"Check mesh validity or adjust percentile/band_thickness."
        )
    
    width_m = band_vertices[:, 0].max() - band_vertices[:, 0].min()
    depth_m = band_vertices[:, 2].max() - band_vertices[:, 2].min()
    
    # Ramanujan ellipse approximation
    a = width_m / 2.0
    b = depth_m / 2.0
    h = ((a - b) ** 2) / ((a + b) ** 2)
    circumference_m = np.pi * (a + b) * (1 + (3 * h) / (10 + np.sqrt(4 - 3 * h)))
    circumference_cm = circumference_m * 100.0
    
    if debug:
        print(
            f"[DEBUG] {name}: band_center_y={band_center_y:.4f}m, "
            f"vertices_in_band={len(band_vertices)}, width={width_m*100:.2f}cm, "
            f"depth={depth_m*100:.2f}cm, circumference={circumference_cm:.2f}cm"
        )
    
    return circumference_cm


# Main entry point: extract all measurements from mesh vertices
def extract_measurements_from_mesh(vertices: np.ndarray, debug: bool = False) -> Dict[str, float]:
    measurements = {
        'height_cm': extract_height_from_mesh(vertices, debug=debug),
        'shoulder_width_cm': extract_shoulder_width_from_mesh(
            vertices, y_percentile=0.85, debug=debug
        ),
        'chest_circumference_cm': extract_circumference_from_mesh(
            vertices, y_percentile=0.75, debug=debug, name="Chest"
        ),
        'waist_circumference_cm': extract_circumference_from_mesh(
            vertices, y_percentile=0.55, debug=debug, name="Waist"
        ),
        'hip_circumference_cm': extract_circumference_from_mesh(
            vertices, y_percentile=0.45, debug=debug, name="Hip"
        ),
    }
    
    return measurements
