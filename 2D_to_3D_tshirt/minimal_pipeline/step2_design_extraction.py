"""
STEP 2: Design Extraction
=========================
This script extracts printed designs (logos, graphics, text) from the T-shirt.

How it works:
- The fabric has a relatively uniform color
- The print has different colors/textures from the fabric
- We detect these differences to isolate the print

Key insight:
- Plain fabric = smooth, consistent color
- Printed areas = edges, texture, color variation
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

# ============================================================
# CONFIGURATION
# ============================================================

# Input from Step 1 (segmentation output)
INPUT_DIR = Path("segmentation_output")
FRONT_MASKED_PATH = INPUT_DIR / "front_masked.png"
FRONT_MASK_PATH = INPUT_DIR / "front_mask.png"
BACK_MASKED_PATH = INPUT_DIR / "back_masked.png"
BACK_MASK_PATH = INPUT_DIR / "back_mask.png"

# Output directory for this step
OUTPUT_DIR = Path("design_output")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory ready: {OUTPUT_DIR}")


def load_masked_image(path: Path) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Load a masked image and extract both the RGB and alpha channel.
    
    Args:
        path: Path to the masked image (BGRA format)
    
    Returns:
        Tuple of (BGR image, alpha mask) or (None, None) if not found
    """
    if not path.exists():
        return None, None
    
    # Load with alpha channel (cv2.IMREAD_UNCHANGED keeps all channels)
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    
    if img is None:
        return None, None
    
    if img.shape[2] == 4:
        # Split into BGR and Alpha
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
        return bgr, alpha
    else:
        # No alpha channel, load mask separately
        bgr = img
        mask_path = path.parent / path.name.replace("_masked", "_mask")
        if mask_path.exists():
            alpha = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        else:
            alpha = np.ones(bgr.shape[:2], dtype=np.uint8) * 255
        return bgr, alpha


def detect_edges(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Detect edges within the garment region.
    
    Edges indicate boundaries between:
    - Different colors in the print
    - Print and fabric
    
    Args:
        image: BGR image
        mask: Binary garment mask
    
    Returns:
        Edge map (white = edge pixels)
    """
    # Convert to grayscale for edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    # This prevents detecting texture as edges
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    
    # Canny edge detection
    # Low threshold = 50, High threshold = 150
    # Edges must have gradient above 150 to be "strong"
    # Edges with gradient 50-150 are kept if connected to strong edges
    edges = cv2.Canny(blurred, 50, 150)
    
    # Keep only edges within the garment
    edges = cv2.bitwise_and(edges, edges, mask=mask)
    
    return edges


def detect_texture_variation(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Detect areas with high texture/color variation.
    
    Prints typically have:
    - Sharp color transitions
    - Higher local variance than plain fabric
    
    We use Local Binary Pattern (LBP) concept simplified:
    Compare each pixel to its neighborhood variance.
    
    Args:
        image: BGR image
        mask: Binary garment mask
    
    Returns:
        Texture variance map (higher = more texture)
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    
    # Calculate local mean using box filter
    kernel_size = 15
    local_mean = cv2.blur(gray, (kernel_size, kernel_size))
    
    # Calculate local variance
    # Variance = E[X^2] - E[X]^2
    local_sq_mean = cv2.blur(gray ** 2, (kernel_size, kernel_size))
    local_variance = local_sq_mean - local_mean ** 2
    
    # Normalize to 0-255 range
    local_variance = np.clip(local_variance, 0, None)
    max_var = np.max(local_variance)
    if max_var > 0:
        texture_map = (local_variance / max_var * 255).astype(np.uint8)
    else:
        texture_map = np.zeros_like(gray, dtype=np.uint8)
    
    # Apply garment mask
    texture_map = cv2.bitwise_and(texture_map, texture_map, mask=mask)
    
    return texture_map


def detect_color_outliers(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Detect pixels that differ significantly from the dominant fabric color.
    
    Strategy:
    1. Sample colors from edges of garment (less likely to have print)
    2. Build a color model of the fabric
    3. Mark pixels that deviate from this model
    
    Args:
        image: BGR image
        mask: Binary garment mask
    
    Returns:
        Binary mask where 255 = likely print, 0 = likely fabric
    """
    # Convert to LAB color space (better for color distance)
    # L = Lightness, A = green-red, B = blue-yellow
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    
    # Create an eroded mask to sample from garment edges (inner border)
    # These areas are less likely to have prints
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
    eroded = cv2.erode(mask, kernel, iterations=2)
    
    # Sample border region (original mask minus heavily eroded)
    border_mask = cv2.subtract(mask, eroded)
    
    # Also sample from top region (neckline area - usually no print)
    h, w = mask.shape
    top_region = np.zeros_like(mask)
    top_region[0:int(h*0.15), :] = 255
    top_sample = cv2.bitwise_and(mask, top_region)
    
    # Combine sampling regions
    sample_mask = cv2.bitwise_or(border_mask, top_sample)
    
    # Get fabric color samples
    fabric_pixels = lab[sample_mask > 0]
    
    if len(fabric_pixels) < 100:
        # Not enough samples, use entire garment
        fabric_pixels = lab[mask > 0]
    
    if len(fabric_pixels) == 0:
        return np.zeros_like(mask)
    
    # Calculate fabric color statistics
    fabric_mean = np.mean(fabric_pixels, axis=0)
    fabric_std = np.std(fabric_pixels, axis=0)
    
    # Calculate distance of each pixel from fabric color
    # Use Mahalanobis-like distance (normalized by std)
    diff = np.abs(lab.astype(np.float32) - fabric_mean)
    
    # Normalize by standard deviation (avoid division by zero)
    std_safe = np.maximum(fabric_std, 1)
    normalized_diff = diff / std_safe
    
    # Sum across channels for total distance
    total_distance = np.sum(normalized_diff, axis=2)
    
    # Threshold: pixels more than 3 std deviations are outliers
    threshold = 3.0
    outlier_mask = (total_distance > threshold).astype(np.uint8) * 255
    
    # Apply garment mask
    outlier_mask = cv2.bitwise_and(outlier_mask, outlier_mask, mask=mask)
    
    return outlier_mask


def combine_detection_methods(
    edges: np.ndarray,
    texture: np.ndarray,
    color_outliers: np.ndarray,
    mask: np.ndarray
) -> np.ndarray:
    """
    Combine multiple detection methods to create final design mask.
    
    Each method catches different aspects of prints:
    - Edges: Sharp boundaries in the design
    - Texture: Gradient areas, halftones
    - Color outliers: Solid colored print areas
    
    Args:
        edges: Edge detection result
        texture: Texture variance map
        color_outliers: Color deviation mask
        mask: Garment mask
    
    Returns:
        Final design mask
    """
    # Normalize and threshold texture map
    _, texture_binary = cv2.threshold(texture, 30, 255, cv2.THRESH_BINARY)
    
    # Dilate edges to create regions around edge pixels
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Combine all three methods with OR
    combined = cv2.bitwise_or(edges_dilated, texture_binary)
    combined = cv2.bitwise_or(combined, color_outliers)
    
    # Clean up with morphological operations
    # Close small gaps
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)
    
    # Remove small noise regions
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open)
    
    # Keep only largest connected components
    combined = keep_large_components(combined, min_area_ratio=0.001)
    
    # Ensure result is within garment bounds
    combined = cv2.bitwise_and(combined, combined, mask=mask)
    
    return combined


def keep_large_components(mask: np.ndarray, min_area_ratio: float = 0.001) -> np.ndarray:
    """
    Remove small connected components from mask.
    
    Args:
        mask: Binary mask
        min_area_ratio: Minimum component area as ratio of total mask area
    
    Returns:
        Cleaned mask with only large components
    """
    total_area = np.sum(mask > 0)
    min_area = int(total_area * min_area_ratio)
    
    # Find connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    # Create output mask
    result = np.zeros_like(mask)
    
    # Keep components larger than threshold
    for i in range(1, num_labels):  # Skip background (0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            result[labels == i] = 255
    
    return result


def extract_design_image(image: np.ndarray, design_mask: np.ndarray) -> np.ndarray:
    """
    Extract the design as an RGBA image.
    
    Args:
        image: Original BGR image
        design_mask: Binary mask of design areas
    
    Returns:
        BGRA image with only design visible (transparent elsewhere)
    """
    # Create 4-channel image
    bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    
    # Set alpha to design mask
    bgra[:, :, 3] = design_mask
    
    return bgra


def get_design_bounding_box(mask: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Get bounding box of design region.
    
    Returns:
        (x, y, width, height) of bounding box
    """
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return (0, 0, 0, 0)
    
    # Get bounding box of all contours combined
    all_points = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(all_points)
    
    return (x, y, w, h)


def create_fabric_only_mask(garment_mask: np.ndarray, design_mask: np.ndarray) -> np.ndarray:
    """
    Create mask of fabric-only areas (garment minus design).
    
    This is useful for Step 3 (color extraction) - we want to
    sample color from fabric, not from the print.
    
    Args:
        garment_mask: Full garment mask
        design_mask: Design/print mask
    
    Returns:
        Mask of fabric-only areas
    """
    fabric_mask = cv2.subtract(garment_mask, design_mask)
    return fabric_mask


# ============================================================
# MAIN EXTRACTION PIPELINE
# ============================================================

def extract_design(image: np.ndarray, mask: np.ndarray, name: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Main design extraction function.
    
    Args:
        image: BGR image of garment
        mask: Binary garment mask
        name: Name for output files
    
    Returns:
        Tuple of (design_mask, fabric_mask)
    """
    print(f"\n{'='*50}")
    print(f"Extracting design from: {name}")
    print('='*50)
    
    # Step 1: Detect edges (boundaries in the print)
    print("\n→ Detecting edges...")
    edges = detect_edges(image, mask)
    edge_pixels = np.sum(edges > 0)
    print(f"  Found {edge_pixels} edge pixels")
    
    # Step 2: Detect texture variation
    print("\n→ Analyzing texture variation...")
    texture = detect_texture_variation(image, mask)
    
    # Step 3: Detect color outliers
    print("\n→ Detecting color outliers...")
    color_outliers = detect_color_outliers(image, mask)
    outlier_pixels = np.sum(color_outliers > 0)
    print(f"  Found {outlier_pixels} color outlier pixels")
    
    # Step 4: Combine methods
    print("\n→ Combining detection methods...")
    design_mask = combine_detection_methods(edges, texture, color_outliers, mask)
    
    # Calculate coverage
    garment_pixels = np.sum(mask > 0)
    design_pixels = np.sum(design_mask > 0)
    coverage = (design_pixels / garment_pixels * 100) if garment_pixels > 0 else 0
    print(f"✓ Design covers {coverage:.1f}% of garment")
    
    # Create fabric-only mask
    fabric_mask = create_fabric_only_mask(mask, design_mask)
    
    # Get design bounding box
    bbox = get_design_bounding_box(design_mask)
    if bbox[2] > 0 and bbox[3] > 0:
        print(f"✓ Design bounding box: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
    else:
        print("○ No design detected (plain fabric)")
    
    return design_mask, fabric_mask


def save_design_results(
    name: str,
    image: np.ndarray,
    garment_mask: np.ndarray,
    design_mask: np.ndarray,
    fabric_mask: np.ndarray
):
    """
    Save all design extraction results.
    
    Args:
        name: Base name for files
        image: Original BGR image
        garment_mask: Full garment mask
        design_mask: Design-only mask
        fabric_mask: Fabric-only mask
    """
    print(f"\n→ Saving {name} results...")
    
    # Save design mask
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_design_mask.png"), design_mask)
    print(f"  ✓ {name}_design_mask.png")
    
    # Save fabric mask
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_fabric_mask.png"), fabric_mask)
    print(f"  ✓ {name}_fabric_mask.png")
    
    # Save design as transparent image
    design_image = extract_design_image(image, design_mask)
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_design.png"), design_image)
    print(f"  ✓ {name}_design.png (design only, transparent bg)")
    
    # Save numpy arrays for programmatic use
    np.save(str(OUTPUT_DIR / f"{name}_design_mask.npy"), design_mask)
    np.save(str(OUTPUT_DIR / f"{name}_fabric_mask.npy"), fabric_mask)
    print(f"  ✓ NumPy arrays saved")
    
    # Create visualization overlay
    visualization = create_visualization(image, garment_mask, design_mask)
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_visualization.png"), visualization)
    print(f"  ✓ {name}_visualization.png (overlay for inspection)")


def create_visualization(
    image: np.ndarray,
    garment_mask: np.ndarray,
    design_mask: np.ndarray
) -> np.ndarray:
    """
    Create a visualization showing detected design regions.
    
    Color coding:
    - Blue tint: Fabric area
    - Red tint: Design area
    
    Args:
        image: Original BGR image
        garment_mask: Full garment mask
        design_mask: Design mask
    
    Returns:
        Visualization image
    """
    # Create a copy
    vis = image.copy()
    
    # Create colored overlays
    fabric_mask = create_fabric_only_mask(garment_mask, design_mask)
    
    # Blue overlay for fabric
    blue_overlay = np.zeros_like(image)
    blue_overlay[:, :] = (255, 100, 0)  # Blue in BGR
    vis = np.where(fabric_mask[:, :, np.newaxis] > 0,
                   cv2.addWeighted(vis, 0.7, blue_overlay, 0.3, 0),
                   vis)
    
    # Red overlay for design
    red_overlay = np.zeros_like(image)
    red_overlay[:, :] = (0, 0, 255)  # Red in BGR
    vis = np.where(design_mask[:, :, np.newaxis] > 0,
                   cv2.addWeighted(vis, 0.7, red_overlay, 0.3, 0),
                   vis)
    
    return vis


def run_design_extraction_pipeline():
    """
    Run the complete design extraction pipeline.
    """
    print("\n" + "="*60)
    print("   STEP 2: DESIGN EXTRACTION")
    print("="*60)
    
    ensure_output_dir()
    
    # Process FRONT image
    print("\n" + "-"*40)
    print("Processing FRONT image")
    print("-"*40)
    
    front_img, front_mask = load_masked_image(FRONT_MASKED_PATH)
    
    if front_img is None:
        print(f"\n✗ ERROR: Could not load front image from: {FRONT_MASKED_PATH}")
        print("  Make sure Step 1 (segmentation) has been run first.")
        return False
    
    print(f"✓ Loaded front image: {front_img.shape[1]}x{front_img.shape[0]} pixels")
    
    front_design_mask, front_fabric_mask = extract_design(front_img, front_mask, "front")
    save_design_results("front", front_img, front_mask, front_design_mask, front_fabric_mask)
    
    # Process BACK image (if available)
    back_img, back_mask = load_masked_image(BACK_MASKED_PATH)
    
    if back_img is not None:
        print("\n" + "-"*40)
        print("Processing BACK image")
        print("-"*40)
        
        print(f"✓ Loaded back image: {back_img.shape[1]}x{back_img.shape[0]} pixels")
        
        back_design_mask, back_fabric_mask = extract_design(back_img, back_mask, "back")
        save_design_results("back", back_img, back_mask, back_design_mask, back_fabric_mask)
    else:
        print("\n→ No back image available (optional)")
    
    # Summary
    print("\n" + "="*60)
    print("   DESIGN EXTRACTION SUMMARY")
    print("="*60)
    print(f"\n✓ Front design extracted:")
    print(f"  - Design mask: {OUTPUT_DIR}/front_design_mask.png")
    print(f"  - Design image: {OUTPUT_DIR}/front_design.png")
    print(f"  - Fabric mask: {OUTPUT_DIR}/front_fabric_mask.png")
    print(f"  - Visualization: {OUTPUT_DIR}/front_visualization.png")
    
    if back_img is not None:
        print(f"\n✓ Back design extracted:")
        print(f"  - Design mask: {OUTPUT_DIR}/back_design_mask.png")
        print(f"  - Design image: {OUTPUT_DIR}/back_design.png")
    
    print("\n" + "="*60)
    
    return True


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run this script after Step 1 (segmentation).
    
    Expects these files in segmentation_output/:
    - front_masked.png (required)
    - front_mask.png (required)
    - back_masked.png (optional)
    - back_mask.png (optional)
    
    Outputs to design_output/:
    - front_design_mask.png (binary mask of print)
    - front_design.png (extracted print with transparency)
    - front_fabric_mask.png (mask of plain fabric areas)
    - front_visualization.png (color-coded overlay)
    """
    success = run_design_extraction_pipeline()
    
    if success:
        print("\n" + "="*60)
        print("   STEP 2 COMPLETE — GREEN SIGNAL REQUIRED ✅")
        print("="*60)
        print("\nNext step: Fabric color extraction")
        print("Waiting for your GREEN SIGNAL to proceed...")
    else:
        print("\n✗ Design extraction failed. Please fix the errors above.")
