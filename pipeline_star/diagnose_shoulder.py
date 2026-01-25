#!/usr/bin/env python3
"""Diagnostic script to visualize shoulder width measurement on STAR mesh."""

import sys
import os
import numpy as np

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from pipeline_star.star_runner import generate_apose_mesh
from pipeline_star.mesh_measure import extract_shoulder_width_from_mesh


def diagnose_shoulder_measurement(user_id: str = "user_m_001"):
    """
    Diagnose shoulder width measurement issue.
    
    The current implementation uses max_x - min_x in a horizontal band at 85% height,
    which can include arms and other body parts, not just shoulder tips.
    """
    print("==" * 40)
    print("SHOULDER WIDTH MEASUREMENT DIAGNOSTIC")
    print("==" * 40)
    
    # Generate default mesh (average male, betas=zeros)
    print("\nGenerating default male mesh...")
    mesh_data = generate_apose_mesh(gender='male', betas=np.zeros(10), scale=1.0)
    vertices = mesh_data['vertices']
    
    print(f"Mesh vertices: {vertices.shape[0]:,}")
    print(f"Height range: {vertices[:, 1].min():.3f}m to {vertices[:, 1].max():.3f}m")
    
    # Current method
    print("\n" + "-" * 80)
    print("CURRENT METHOD: Max X-range in shoulder band")
    print("-" * 80)
    
    y_percentile = 0.85
    band_thickness = 0.02
    
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
    
    min_x = band_vertices[:, 0].min()
    max_x = band_vertices[:, 0].max()
    shoulder_width_cm = (max_x - min_x) * 100.0
    
    print(f"Y-band center: {band_center_y:.3f}m ({y_percentile*100:.0f}% of height)")
    print(f"Vertices in band: {len(band_vertices):,}")
    print(f"X-range: {min_x:.3f}m to {max_x:.3f}m")
    print(f"Calculated shoulder width: {shoulder_width_cm:.2f} cm")
    
    # Show why this is wrong
    print("\n" + "-" * 80)
    print("PROBLEM ANALYSIS")
    print("-" * 80)
    print("Issue: max_x - min_x measures the WIDEST point in the horizontal band,")
    print("       which includes arms, not just shoulder tips.")
    print()
    print("In A-pose with arms down ~45°:")
    print("  - Arms extend outward from body")
    print("  - At 85% height (shoulder area), arms are part of the measurement")
    print("  - This makes the 'shoulder width' much larger than anatomical shoulder width")
    print()
    print("For user_m_001:")
    print(f"  - Target shoulder width: 45.0 cm (from MongoDB)")
    print(f"  - Predicted by current method: ~72.8 cm (61.7% error)")
    print(f"  - The extra width comes from including the arms in the X-range")
    
    # Possible solutions
    print("\n" + "-" * 80)
    print("POSSIBLE SOLUTIONS")
    print("-" * 80)
    print()
    print("Option 1: Use STAR vertex indices for anatomical landmarks")
    print("  - STAR model has predefined vertex indices for left/right shoulder")
    print("  - Calculate distance between these specific vertices")
    print("  - More accurate but requires knowledge of STAR topology")
    print()
    print("Option 2: Adjust y-percentile higher (e.g., 0.90 or 0.92)")
    print("  - Move band above where arms connect to torso")
    print("  - May work but is fragile and depends on pose")
    print()
    print("Option 3: Use narrower Z-range filtering")
    print("  - Only include vertices near the front/back of the body")
    print("  - Filter out vertices with large Z-values (arms)")
    print()
    print("Option 4: Accept as STAR limitation")
    print("  - Document that shoulder width cannot be accurately fitted with current method")
    print("  - Remove shoulder_width_cm from gated_fields")
    print("  - Keep as validate-only field like leg_length")
    
    print("\n" + "==" * 40)
    print("RECOMMENDATION")
    print("==" * 40)
    print()
    print("For MVP: Use Option 4 (accept as limitation)")
    print("  - Remove shoulder_width_cm from fitting targets")
    print("  - Document as known limitation in 001-flag.md")
    print("  - Focus on measurements that can be accurately fitted:")
    print("    • Height (works perfectly)")
    print("    • Chest/Waist/Hip circumferences (use ellipse approximation)")
    print()
    print("For future: Implement Option 1 (use STAR landmarks)")
    print("  - Research STAR vertex topology")
    print("  - Find shoulder joint vertex indices")
    print("  - Calculate direct distance between shoulder points")
    print()


if __name__ == "__main__":
    diagnose_shoulder_measurement()
