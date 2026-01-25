"""
STEP 3: Fabric Color Extraction
================================
This script extracts the true base color of the T-shirt fabric.

Key insight:
- We sample ONLY from fabric areas (excluding the print)
- This gives us the actual cloth color, not polluted by print colors

Why clustering?
- Even "solid" fabrics have slight color variations
- Lighting creates shadows and highlights
- K-means clustering finds the most representative color
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from sklearn.cluster import KMeans
import json

# ============================================================
# CONFIGURATION
# ============================================================

# Input directories from previous steps
SEGMENTATION_DIR = Path("segmentation_output")
DESIGN_DIR = Path("design_output")

# Input files
FRONT_IMAGE_PATH = SEGMENTATION_DIR / "front_masked.png"
FRONT_FABRIC_MASK_PATH = DESIGN_DIR / "front_fabric_mask.png"
BACK_IMAGE_PATH = SEGMENTATION_DIR / "back_masked.png"
BACK_FABRIC_MASK_PATH = DESIGN_DIR / "back_fabric_mask.png"

# Output directory
OUTPUT_DIR = Path("color_output")

# Number of color clusters to find
N_CLUSTERS = 3  # Find top 3 colors (dominant + variations)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory ready: {OUTPUT_DIR}")


def load_image_and_mask(
    image_path: Path, 
    mask_path: Path
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Load image and its corresponding mask.
    
    Args:
        image_path: Path to the image file
        mask_path: Path to the mask file
    
    Returns:
        Tuple of (BGR image, grayscale mask) or (None, None)
    """
    if not image_path.exists():
        return None, None
    
    # Load image (with alpha if present)
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None, None
    
    # Extract BGR channels (ignore alpha if present)
    if img.shape[2] == 4:
        bgr = img[:, :, :3]
    else:
        bgr = img
    
    # Load mask
    if mask_path.exists():
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    else:
        # Fallback: use alpha channel as mask
        if img.shape[2] == 4:
            mask = img[:, :, 3]
        else:
            mask = np.ones(bgr.shape[:2], dtype=np.uint8) * 255
    
    return bgr, mask


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to HEX color string.
    
    Args:
        rgb: Tuple of (R, G, B) values 0-255
    
    Returns:
        HEX string like "#FF5733"
    """
    return "#{:02X}{:02X}{:02X}".format(rgb[0], rgb[1], rgb[2])


def bgr_to_rgb(bgr: np.ndarray) -> np.ndarray:
    """
    Convert BGR to RGB (swap first and last channels).
    
    OpenCV uses BGR, but most tools expect RGB.
    """
    return bgr[:, :, ::-1] if len(bgr.shape) == 3 else bgr


def get_color_name(rgb: Tuple[int, int, int]) -> str:
    """
    Get approximate color name from RGB values.
    
    This is a simple heuristic - not a complete color naming system.
    
    Args:
        rgb: Tuple of (R, G, B) values
    
    Returns:
        Approximate color name
    """
    r, g, b = rgb
    
    # Convert to HSV for easier color naming
    # Normalize to 0-1 range
    r_norm, g_norm, b_norm = r/255, g/255, b/255
    max_c = max(r_norm, g_norm, b_norm)
    min_c = min(r_norm, g_norm, b_norm)
    diff = max_c - min_c
    
    # Calculate HSV
    # Value (brightness)
    v = max_c
    
    # Saturation
    s = 0 if max_c == 0 else diff / max_c
    
    # Hue
    if diff == 0:
        h = 0
    elif max_c == r_norm:
        h = 60 * ((g_norm - b_norm) / diff % 6)
    elif max_c == g_norm:
        h = 60 * ((b_norm - r_norm) / diff + 2)
    else:
        h = 60 * ((r_norm - g_norm) / diff + 4)
    
    # Name based on HSV
    if v < 0.15:
        return "Black"
    elif v > 0.9 and s < 0.1:
        return "White"
    elif s < 0.15:
        if v < 0.5:
            return "Dark Gray"
        else:
            return "Light Gray"
    else:
        # Chromatic colors
        if h < 15 or h >= 345:
            return "Red" if s > 0.5 else "Pink"
        elif h < 45:
            return "Orange" if s > 0.5 else "Peach"
        elif h < 70:
            return "Yellow"
        elif h < 150:
            return "Green"
        elif h < 190:
            return "Cyan"
        elif h < 260:
            return "Blue" if v > 0.3 else "Navy"
        elif h < 290:
            return "Purple"
        else:
            return "Magenta"


def extract_fabric_pixels(
    image: np.ndarray, 
    fabric_mask: np.ndarray
) -> np.ndarray:
    """
    Extract all pixels from fabric regions.
    
    Args:
        image: BGR image
        fabric_mask: Binary mask (255 = fabric, 0 = not fabric)
    
    Returns:
        Array of shape (N, 3) containing RGB values of fabric pixels
    """
    # Convert BGR to RGB
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Get pixels where mask is non-zero
    fabric_pixels = rgb[fabric_mask > 0]
    
    return fabric_pixels


def cluster_colors(
    pixels: np.ndarray, 
    n_clusters: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Cluster pixels to find dominant colors.
    
    K-means clustering groups similar colors together.
    The center of the largest cluster is the dominant color.
    
    Args:
        pixels: Array of shape (N, 3) with RGB values
        n_clusters: Number of clusters (colors) to find
    
    Returns:
        Tuple of (cluster_centers, cluster_percentages)
        - cluster_centers: RGB values of each cluster center
        - cluster_percentages: What % of pixels belong to each cluster
    """
    if len(pixels) == 0:
        return np.array([]), np.array([])
    
    # Limit sample size for performance (100k pixels is plenty)
    max_samples = 100000
    if len(pixels) > max_samples:
        indices = np.random.choice(len(pixels), max_samples, replace=False)
        pixels_sample = pixels[indices]
    else:
        pixels_sample = pixels
    
    # Run K-means clustering
    # n_init=10 means we run it 10 times and pick the best result
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = kmeans.fit_predict(pixels_sample)
    
    # Get cluster centers (these are our colors)
    centers = kmeans.cluster_centers_.astype(np.uint8)
    
    # Calculate percentage of pixels in each cluster
    unique, counts = np.unique(labels, return_counts=True)
    total = len(labels)
    percentages = (counts / total) * 100
    
    # Sort by percentage (most common first)
    sort_idx = np.argsort(percentages)[::-1]
    centers = centers[sort_idx]
    percentages = percentages[sort_idx]
    
    return centers, percentages


def analyze_color_distribution(pixels: np.ndarray) -> Dict:
    """
    Analyze the color distribution of fabric pixels.
    
    This gives us statistics about the fabric color:
    - Mean: average color
    - Std: how much the color varies
    - This helps understand fabric consistency
    
    Args:
        pixels: Array of RGB values
    
    Returns:
        Dictionary with color statistics
    """
    if len(pixels) == 0:
        return {}
    
    # Calculate mean RGB
    mean_rgb = np.mean(pixels, axis=0).astype(np.uint8)
    
    # Calculate standard deviation
    std_rgb = np.std(pixels, axis=0)
    
    # Calculate min/max
    min_rgb = np.min(pixels, axis=0)
    max_rgb = np.max(pixels, axis=0)
    
    return {
        "mean_rgb": mean_rgb.tolist(),
        "std_rgb": std_rgb.tolist(),
        "min_rgb": min_rgb.tolist(),
        "max_rgb": max_rgb.tolist(),
        "num_pixels": len(pixels)
    }


def create_color_swatch(
    colors: List[Tuple[int, int, int]], 
    percentages: List[float],
    size: Tuple[int, int] = (400, 100)
) -> np.ndarray:
    """
    Create a visual color swatch image.
    
    Shows the extracted colors as horizontal bars,
    with width proportional to their percentage.
    
    Args:
        colors: List of RGB tuples
        percentages: Percentage for each color
        size: Output image size (width, height)
    
    Returns:
        BGR image of the color swatch
    """
    width, height = size
    swatch = np.zeros((height, width, 3), dtype=np.uint8)
    
    x = 0
    for color, pct in zip(colors, percentages):
        # Calculate width of this color bar
        bar_width = int(width * pct / 100)
        if bar_width < 1:
            bar_width = 1
        
        # Convert RGB to BGR for OpenCV
        bgr_color = (int(color[2]), int(color[1]), int(color[0]))
        
        # Draw the color bar
        swatch[:, x:x+bar_width] = bgr_color
        x += bar_width
    
    # Fill any remaining space with the last color
    if x < width and len(colors) > 0:
        last_color = colors[-1]
        bgr_last = (int(last_color[2]), int(last_color[1]), int(last_color[0]))
        swatch[:, x:] = bgr_last
    
    return swatch


def create_dominant_color_image(
    color: Tuple[int, int, int],
    size: Tuple[int, int] = (200, 200)
) -> np.ndarray:
    """
    Create a solid color image showing the dominant fabric color.
    
    Args:
        color: RGB tuple
        size: Output image size
    
    Returns:
        BGR image
    """
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    # Convert RGB to BGR
    img[:, :] = (color[2], color[1], color[0])
    return img


# ============================================================
# MAIN COLOR EXTRACTION PIPELINE
# ============================================================

def extract_fabric_color(
    image: np.ndarray, 
    fabric_mask: np.ndarray,
    name: str
) -> Dict:
    """
    Main fabric color extraction function.
    
    Args:
        image: BGR image
        fabric_mask: Binary mask of fabric-only areas
        name: Name for output files
    
    Returns:
        Dictionary with color information
    """
    print(f"\n{'='*50}")
    print(f"Extracting fabric color from: {name}")
    print('='*50)
    
    # Step 1: Extract fabric pixels
    print("\n→ Extracting fabric pixels...")
    fabric_pixels = extract_fabric_pixels(image, fabric_mask)
    print(f"  Found {len(fabric_pixels):,} fabric pixels")
    
    if len(fabric_pixels) == 0:
        print("✗ No fabric pixels found!")
        return {}
    
    # Step 2: Cluster to find dominant colors
    print(f"\n→ Clustering into {N_CLUSTERS} color groups...")
    centers, percentages = cluster_colors(fabric_pixels, N_CLUSTERS)
    
    # Step 3: Identify dominant color
    dominant_rgb = tuple(centers[0].tolist())
    dominant_hex = rgb_to_hex(dominant_rgb)
    dominant_name = get_color_name(dominant_rgb)
    dominant_pct = percentages[0]
    
    print(f"\n✓ DOMINANT FABRIC COLOR:")
    print(f"  RGB: {dominant_rgb}")
    print(f"  HEX: {dominant_hex}")
    print(f"  Name: {dominant_name}")
    print(f"  Coverage: {dominant_pct:.1f}% of fabric")
    
    # Step 4: Analyze color distribution
    print("\n→ Analyzing color distribution...")
    stats = analyze_color_distribution(fabric_pixels)
    print(f"  Mean RGB: {stats['mean_rgb']}")
    print(f"  Std Dev: [{stats['std_rgb'][0]:.1f}, {stats['std_rgb'][1]:.1f}, {stats['std_rgb'][2]:.1f}]")
    
    # Build result dictionary
    all_colors = []
    for i, (center, pct) in enumerate(zip(centers, percentages)):
        rgb = tuple(center.tolist())
        all_colors.append({
            "rank": i + 1,
            "rgb": rgb,
            "hex": rgb_to_hex(rgb),
            "name": get_color_name(rgb),
            "percentage": round(pct, 2)
        })
        print(f"\n  Color #{i+1}: {rgb_to_hex(rgb)} ({get_color_name(rgb)}) - {pct:.1f}%")
    
    result = {
        "dominant": {
            "rgb": dominant_rgb,
            "hex": dominant_hex,
            "name": dominant_name,
            "percentage": round(dominant_pct, 2)
        },
        "all_colors": all_colors,
        "statistics": stats
    }
    
    return result


def save_color_results(name: str, color_info: Dict, centers: np.ndarray, percentages: np.ndarray):
    """
    Save color extraction results.
    
    Args:
        name: Base name for files
        color_info: Dictionary with color information
        centers: Array of color centers (RGB)
        percentages: Percentage for each color
    """
    print(f"\n→ Saving {name} color results...")
    
    # Save JSON with all color information
    json_path = OUTPUT_DIR / f"{name}_fabric_color.json"
    with open(json_path, 'w') as f:
        json.dump(color_info, f, indent=2)
    print(f"  ✓ {name}_fabric_color.json")
    
    # Save dominant color as simple text file (easy to read)
    txt_path = OUTPUT_DIR / f"{name}_dominant_color.txt"
    with open(txt_path, 'w') as f:
        f.write(f"RGB: {color_info['dominant']['rgb']}\n")
        f.write(f"HEX: {color_info['dominant']['hex']}\n")
        f.write(f"Name: {color_info['dominant']['name']}\n")
    print(f"  ✓ {name}_dominant_color.txt")
    
    # Create and save color swatch visualization
    colors = [tuple(c.tolist()) for c in centers]
    swatch = create_color_swatch(colors, percentages.tolist())
    swatch_path = OUTPUT_DIR / f"{name}_color_swatch.png"
    cv2.imwrite(str(swatch_path), swatch)
    print(f"  ✓ {name}_color_swatch.png")
    
    # Create dominant color image
    dominant_img = create_dominant_color_image(color_info['dominant']['rgb'])
    dominant_path = OUTPUT_DIR / f"{name}_dominant_color.png"
    cv2.imwrite(str(dominant_path), dominant_img)
    print(f"  ✓ {name}_dominant_color.png")


def run_color_extraction_pipeline():
    """
    Run the complete color extraction pipeline.
    """
    print("\n" + "="*60)
    print("   STEP 3: FABRIC COLOR EXTRACTION")
    print("="*60)
    
    ensure_output_dir()
    
    # Process FRONT
    print("\n" + "-"*40)
    print("Processing FRONT fabric")
    print("-"*40)
    
    front_img, front_mask = load_image_and_mask(FRONT_IMAGE_PATH, FRONT_FABRIC_MASK_PATH)
    
    if front_img is None:
        print(f"\n✗ ERROR: Could not load front image from: {FRONT_IMAGE_PATH}")
        return False
    
    if front_mask is None:
        print(f"\n✗ ERROR: Could not load fabric mask from: {FRONT_FABRIC_MASK_PATH}")
        print("  Make sure Step 2 (design extraction) has been run first.")
        return False
    
    print(f"✓ Loaded front image: {front_img.shape[1]}x{front_img.shape[0]} pixels")
    print(f"✓ Loaded fabric mask: {np.sum(front_mask > 0):,} fabric pixels")
    
    # Extract fabric pixels and cluster
    fabric_pixels = extract_fabric_pixels(front_img, front_mask)
    centers, percentages = cluster_colors(fabric_pixels, N_CLUSTERS)
    
    front_color_info = extract_fabric_color(front_img, front_mask, "front")
    if front_color_info:
        save_color_results("front", front_color_info, centers, percentages)
    
    # Process BACK (if available)
    back_img, back_mask = load_image_and_mask(BACK_IMAGE_PATH, BACK_FABRIC_MASK_PATH)
    
    if back_img is not None and back_mask is not None:
        print("\n" + "-"*40)
        print("Processing BACK fabric")
        print("-"*40)
        
        back_fabric_pixels = extract_fabric_pixels(back_img, back_mask)
        back_centers, back_percentages = cluster_colors(back_fabric_pixels, N_CLUSTERS)
        
        back_color_info = extract_fabric_color(back_img, back_mask, "back")
        if back_color_info:
            save_color_results("back", back_color_info, back_centers, back_percentages)
    else:
        print("\n→ No back image available (optional)")
    
    # Summary
    print("\n" + "="*60)
    print("   FABRIC COLOR SUMMARY")
    print("="*60)
    
    if front_color_info:
        d = front_color_info['dominant']
        print(f"\n🎨 FRONT FABRIC COLOR:")
        print(f"   ┌────────────────────────────┐")
        print(f"   │  RGB: {d['rgb']}".ljust(30) + "│")
        print(f"   │  HEX: {d['hex']}".ljust(30) + "│")
        print(f"   │  Name: {d['name']}".ljust(30) + "│")
        print(f"   └────────────────────────────┘")
    
    if back_img is not None and back_color_info:
        d = back_color_info['dominant']
        print(f"\n🎨 BACK FABRIC COLOR:")
        print(f"   ┌────────────────────────────┐")
        print(f"   │  RGB: {d['rgb']}".ljust(30) + "│")
        print(f"   │  HEX: {d['hex']}".ljust(30) + "│")
        print(f"   │  Name: {d['name']}".ljust(30) + "│")
        print(f"   └────────────────────────────┘")
    
    print(f"\nOutput files saved to: {OUTPUT_DIR}/")
    print("\n" + "="*60)
    
    return True


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run this script after Steps 1 and 2.
    
    Requires:
    - segmentation_output/front_masked.png
    - design_output/front_fabric_mask.png
    
    Why we use fabric_mask (not garment_mask)?
    - fabric_mask = garment MINUS design
    - This gives us ONLY the plain fabric areas
    - No print colors contaminate our color extraction
    
    The result is the TRUE fabric color!
    
    Install with:
        pip install scikit-learn
    """
    success = run_color_extraction_pipeline()
    
    if success:
        print("\n" + "="*60)
        print("   STEP 3 COMPLETE — GREEN SIGNAL REQUIRED ✅")
        print("="*60)
        print("\nNext step: Pattern generation from measurements")
        print("Waiting for your GREEN SIGNAL to proceed...")
    else:
        print("\n✗ Color extraction failed. Please fix the errors above.")
