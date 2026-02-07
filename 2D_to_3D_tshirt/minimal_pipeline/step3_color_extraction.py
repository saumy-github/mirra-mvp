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
import time
from datetime import datetime

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

# Logging configuration
LOG_FILE = OUTPUT_DIR / "step3_detailed_log.txt"
LOG_JSON = OUTPUT_DIR / "step3_metrics.json"
DEBUG_DIR = OUTPUT_DIR / "debug_visualizations"

# Number of color clusters to find
N_CLUSTERS = 3  # Find top 3 colors (dominant + variations)


# ============================================================
# LOGGING SYSTEM
# ============================================================

class ColorExtractionLogger:
    """Logger for comprehensive color extraction tracking"""
    
    def __init__(self):
        self.log_entries = []
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "pipeline": "step3_color_extraction",
            "version": "enhanced_v1.0",
            "operations": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] [{level:7}] {message}"
        self.log_entries.append(entry)
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback for Windows console that doesn't support emojis
            print(message.encode('ascii', 'replace').decode('ascii'))
    
    def log_color_cluster(self, rank: int, rgb: tuple, hex_code: str, name: str, percentage: float):
        """Log a color cluster with all details"""
        self.log(f"  Cluster #{rank}:", "INFO")
        self.log(f"    RGB: {rgb}", "INFO")
        self.log(f"    HEX: {hex_code}", "INFO")
        self.log(f"    Name: {name}", "INFO")
        self.log(f"    Coverage: {percentage:.2f}% of fabric pixels", "INFO")
    
    def log_statistics(self, stats: dict):
        """Log color distribution statistics"""
        self.log(f"  Pixel count: {stats['num_pixels']:,}", "INFO")
        self.log(f"  Mean RGB: {stats['mean_rgb']}", "INFO")
        self.log(f"  Std RGB: [{stats['std_rgb'][0]:.2f}, {stats['std_rgb'][1]:.2f}, {stats['std_rgb'][2]:.2f}]", "INFO")
        self.log(f"  Min RGB: {stats['min_rgb']}", "INFO")
        self.log(f"  Max RGB: {stats['max_rgb']}", "INFO")
    
    def save_debug_image(self, image: np.ndarray, name: str):
        """Save a debug visualization image"""
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_DIR / f"{name}.png"
        cv2.imwrite(str(path), image)
        self.log(f"  Debug image saved: {path.name}", "SUCCESS")
    
    def save_metrics(self):
        """Save all metrics and logs to files"""
        # Save detailed log
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clean log entries of invalid Unicode surrogates
        cleaned_entries = []
        for entry in self.log_entries:
            try:
                # Try to encode/decode to find invalid characters
                entry.encode('utf-8')
                cleaned_entries.append(entry)
            except UnicodeEncodeError:
                # Remove surrogates by encoding with 'replace' error handler
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

logger = ColorExtractionLogger()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    logger.log(f"Output directory ready: {OUTPUT_DIR}", "SUCCESS")
    logger.log(f"Debug directory ready: {DEBUG_DIR}", "SUCCESS")


def load_image_and_mask(
    image_path: Path, 
    mask_path: Path
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Load image and its corresponding mask with validation logging.
    
    Args:
        image_path: Path to the image file
        mask_path: Path to the mask file
    
    Returns:
        Tuple of (BGR image, grayscale mask) or (None, None)
    """
    logger.log(f"Loading image: {image_path.name}", "INFO")
    
    if not image_path.exists():
        logger.log(f"  Image file not found: {image_path}", "ERROR")
        return None, None
    
    # Load image (with alpha if present)
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        logger.log(f"  Failed to read image file: {image_path}", "ERROR")
        return None, None
    
    file_size = image_path.stat().st_size / 1024
    logger.log(f"  Image loaded: {img.shape}, {file_size:.1f} KB", "SUCCESS")
    
    # Extract BGR channels (ignore alpha if present)
    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = img[:, :, :3]
        logger.log(f"  Extracted BGR from BGRA image", "INFO")
    else:
        bgr = img
        logger.log(f"  Using BGR image directly", "INFO")
    
    # Load mask
    if mask_path.exists():
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        mask_pixels = np.count_nonzero(mask)
        logger.log(f"  Mask loaded: {mask.shape}, {mask_pixels:,} active pixels", "SUCCESS")
    else:
        # Fallback: use alpha channel as mask
        logger.log(f"  Mask file not found: {mask_path}", "WARNING")
        if len(img.shape) == 3 and img.shape[2] == 4:
            mask = img[:, :, 3]
            logger.log(f"  Using alpha channel as mask", "INFO")
        else:
            mask = np.ones(bgr.shape[:2], dtype=np.uint8) * 255
            logger.log(f"  Created full white mask (no masking)", "WARNING")
    
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
    Extract all pixels from fabric regions with logging.
    
    Args:
        image: BGR image
        fabric_mask: Binary mask (255 = fabric, 0 = not fabric)
    
    Returns:
        Array of shape (N, 3) containing RGB values of fabric pixels
    """
    start_time = time.time()
    logger.log("Extracting fabric pixels...", "INFO")
    
    # Convert BGR to RGB
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    logger.log(f"  Converted BGR to RGB", "INFO")
    
    # Get pixels where mask is non-zero
    fabric_pixels = rgb[fabric_mask > 0]
    
    elapsed = time.time() - start_time
    logger.log(f"  Extracted {len(fabric_pixels):,} fabric pixels in {elapsed:.3f}s", "SUCCESS")
    
    if len(fabric_pixels) == 0:
        logger.log("  WARNING: No fabric pixels found!", "WARNING")
    
    return fabric_pixels


def cluster_colors(
    pixels: np.ndarray, 
    n_clusters: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Cluster pixels to find dominant colors with detailed logging.
    
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
    start_time = time.time()
    logger.log(f"Clustering into {n_clusters} color groups...", "INFO")
    
    if len(pixels) == 0:
        logger.log("  No pixels to cluster!", "ERROR")
        return np.array([]), np.array([])
    
    # Limit sample size for performance (100k pixels is plenty)
    max_samples = 100000
    if len(pixels) > max_samples:
        indices = np.random.choice(len(pixels), max_samples, replace=False)
        pixels_sample = pixels[indices]
        logger.log(f"  Sampling {max_samples:,} pixels from {len(pixels):,} total (for performance)", "INFO")
    else:
        pixels_sample = pixels
        logger.log(f"  Using all {len(pixels):,} pixels for clustering", "INFO")
    
    # Run K-means clustering
    # n_init=10 means we run it 10 times and pick the best result
    logger.log(f"  Running K-means (n_init=10)...", "INFO")
    kmeans_start = time.time()
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = kmeans.fit_predict(pixels_sample)
    kmeans_time = time.time() - kmeans_start
    
    logger.log(f"  K-means completed in {kmeans_time:.3f}s", "SUCCESS")
    logger.log(f"  Inertia (sum of squared distances): {kmeans.inertia_:.2f}", "INFO")
    
    # Get cluster centers (these are our colors)
    centers = kmeans.cluster_centers_.astype(np.uint8)
    
    # Calculate percentage of pixels in each cluster
    unique, counts = np.unique(labels, return_counts=True)
    total = len(labels)
    percentages = (counts / total) * 100
    
    logger.log(f"  Cluster distribution:", "INFO")
    for i, pct in enumerate(percentages):
        logger.log(f"    Cluster {i}: {pct:.2f}%", "INFO")
    
    # Sort by percentage (most common first)
    sort_idx = np.argsort(percentages)[::-1]
    centers = centers[sort_idx]
    percentages = percentages[sort_idx]
    
    elapsed = time.time() - start_time
    logger.log(f"Color clustering complete in {elapsed:.3f}s", "SUCCESS")
    
    return centers, percentages


def analyze_color_distribution(pixels: np.ndarray) -> Dict:
    """
    Analyze the color distribution of fabric pixels with logging.
    
    This gives us statistics about the fabric color:
    - Mean: average color
    - Std: how much the color varies
    - This helps understand fabric consistency
    
    Args:
        pixels: Array of RGB values
    
    Returns:
        Dictionary with color statistics
    """
    logger.log("Analyzing color distribution...", "INFO")
    
    if len(pixels) == 0:
        logger.log("  No pixels to analyze!", "ERROR")
        return {}
    
    # Calculate mean RGB
    mean_rgb = np.mean(pixels, axis=0).astype(np.uint8)
    logger.log(f"  Mean RGB: {mean_rgb.tolist()}", "INFO")
    
    # Calculate standard deviation
    std_rgb = np.std(pixels, axis=0)
    logger.log(f"  Std RGB: [{std_rgb[0]:.2f}, {std_rgb[1]:.2f}, {std_rgb[2]:.2f}]", "INFO")
    
    # Calculate min/max
    min_rgb = np.min(pixels, axis=0)
    max_rgb = np.max(pixels, axis=0)
    logger.log(f"  Min RGB: {min_rgb.tolist()}", "INFO")
    logger.log(f"  Max RGB: {max_rgb.tolist()}", "INFO")
    
    # Calculate color variance (fabric uniformity metric)
    total_variance = np.sum(std_rgb)
    logger.log(f"  Total variance: {total_variance:.2f} (lower = more uniform)", "INFO")
    
    return {
        "mean_rgb": mean_rgb.tolist(),
        "std_rgb": std_rgb.tolist(),
        "min_rgb": min_rgb.tolist(),
        "max_rgb": max_rgb.tolist(),
        "num_pixels": len(pixels),
        "total_variance": round(total_variance, 2)
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
    Main fabric color extraction function with comprehensive logging.
    
    Args:
        image: BGR image
        fabric_mask: Binary mask of fabric-only areas
        name: Name for output files
    
    Returns:
        Dictionary with color information
    """
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"EXTRACTING FABRIC COLOR: {name.upper()}", "INFO")
    logger.log(f"{'='*60}", "INFO")
    
    extraction_start = time.time()
    
    # Step 1: Extract fabric pixels
    logger.log("", "INFO")
    logger.log("STEP 1: Extract Fabric Pixels", "INFO")
    logger.log("-" * 40, "INFO")
    fabric_pixels = extract_fabric_pixels(image, fabric_mask)
    
    if len(fabric_pixels) == 0:
        logger.log("No fabric pixels found!", "ERROR")
        return {}
    
    # Step 2: Cluster to find dominant colors
    logger.log("", "INFO")
    logger.log("STEP 2: K-Means Color Clustering", "INFO")
    logger.log("-" * 40, "INFO")
    centers, percentages = cluster_colors(fabric_pixels, N_CLUSTERS)
    
    # Step 3: Identify dominant color
    logger.log("", "INFO")
    logger.log("STEP 3: Identify Dominant Color", "INFO")
    logger.log("-" * 40, "INFO")
    dominant_rgb = tuple(centers[0].tolist())
    dominant_hex = rgb_to_hex(dominant_rgb)
    dominant_name = get_color_name(dominant_rgb)
    dominant_pct = percentages[0]
    
    logger.log(f"\nDOMINANT FABRIC COLOR:", "SUCCESS")
    logger.log(f"  RGB: {dominant_rgb}", "SUCCESS")
    logger.log(f"  HEX: {dominant_hex}", "SUCCESS")
    logger.log(f"  Name: {dominant_name}", "SUCCESS")
    logger.log(f"  Coverage: {dominant_pct:.2f}% of fabric", "SUCCESS")
    
    # Step 4: Analyze color distribution
    logger.log("", "INFO")
    logger.log("STEP 4: Analyze Color Distribution", "INFO")
    logger.log("-" * 40, "INFO")
    stats = analyze_color_distribution(fabric_pixels)
    
    # Step 5: Log all detected colors
    logger.log("", "INFO")
    logger.log("ALL DETECTED COLOR CLUSTERS:", "INFO")
    all_colors = []
    for i, (center, pct) in enumerate(zip(centers, percentages)):
        rgb = tuple(center.tolist())
        hex_code = rgb_to_hex(rgb)
        name = get_color_name(rgb)
        logger.log_color_cluster(i+1, rgb, hex_code, name, pct)
        all_colors.append({
            "rank": i + 1,
            "rgb": rgb,
            "hex": hex_code,
            "name": name,
            "percentage": round(pct, 2)
        })
    
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
    
    extraction_time = time.time() - extraction_start
    logger.log("", "INFO")
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"{name.upper()} COLOR EXTRACTION COMPLETE in {extraction_time:.3f}s", "SUCCESS")
    logger.log(f"{'='*60}", "INFO")
    
    return result


def save_color_results(name: str, color_info: Dict, centers: np.ndarray, percentages: np.ndarray):
    """
    Save color extraction results with validation.
    
    Args:
        name: Base name for files
        color_info: Dictionary with color information
        centers: Array of color centers (RGB)
        percentages: Percentage for each color
    """
    logger.log(f"Saving {name} color results...", "INFO")
    saved_files = []
    
    try:
        # Save JSON with all color information
        json_path = OUTPUT_DIR / f"{name}_fabric_color.json"
        with open(json_path, 'w') as f:
            json.dump(color_info, f, indent=2)
        size = json_path.stat().st_size
        saved_files.append(("json", json_path, size))
        logger.log(f"  ✓ {name}_fabric_color.json ({size} bytes)", "SUCCESS")
        
        # Save dominant color as simple text file (easy to read)
        txt_path = OUTPUT_DIR / f"{name}_dominant_color.txt"
        with open(txt_path, 'w') as f:
            f.write(f"RGB: {color_info['dominant']['rgb']}\n")
            f.write(f"HEX: {color_info['dominant']['hex']}\n")
            f.write(f"Name: {color_info['dominant']['name']}\n")
        size = txt_path.stat().st_size
        saved_files.append(("txt", txt_path, size))
        logger.log(f"  ✓ {name}_dominant_color.txt ({size} bytes)", "SUCCESS")
        
        # Create and save color swatch visualization
        colors = [tuple(c.tolist()) for c in centers]
        swatch = create_color_swatch(colors, percentages.tolist())
        swatch_path = OUTPUT_DIR / f"{name}_color_swatch.png"
        cv2.imwrite(str(swatch_path), swatch)
        size = swatch_path.stat().st_size
        saved_files.append(("swatch", swatch_path, size))
        logger.log(f"  ✓ {name}_color_swatch.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Create dominant color image
        dominant_img = create_dominant_color_image(color_info['dominant']['rgb'])
        dominant_path = OUTPUT_DIR / f"{name}_dominant_color.png"
        cv2.imwrite(str(dominant_path), dominant_img)
        size = dominant_path.stat().st_size
        saved_files.append(("dominant", dominant_path, size))
        logger.log(f"  ✓ {name}_dominant_color.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Validate all files
        all_valid = True
        for file_type, file_path, file_size in saved_files:
            if not file_path.exists():
                logger.log(f"  ERROR: {file_path.name} not created!", "ERROR")
                all_valid = False
            elif file_size == 0:
                logger.log(f"  ERROR: {file_path.name} is empty!", "ERROR")
                all_valid = False
        
        if all_valid:
            logger.log(f"All {name} color files validated successfully", "SUCCESS")
        
    except Exception as e:
        logger.log(f"Error saving {name} color results: {e}", "ERROR")


def run_color_extraction_pipeline():
    """
    Run the complete color extraction pipeline with comprehensive logging.
    """
    logger.log("\n" + "="*80, "INFO")
    logger.log("   STEP 3: FABRIC COLOR EXTRACTION PIPELINE (ENHANCED)", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    pipeline_start = time.time()
    
    ensure_output_dir()
    
    results = {"front": {"success": False}, "back": {"success": False}}
    
    # Process FRONT
    logger.log("\n" + "-"*80, "INFO")
    logger.log("PROCESSING FRONT FABRIC COLOR (REQUIRED)", "INFO")
    logger.log("-"*80 + "\n", "INFO")
    
    front_img, front_mask = load_image_and_mask(FRONT_IMAGE_PATH, FRONT_FABRIC_MASK_PATH)
    
    if front_img is None:
        logger.log("\n" + "="*80, "ERROR")
        logger.log("❌ CRITICAL ERROR: Could not load front image", "ERROR")
        logger.log(f"   Path: {FRONT_IMAGE_PATH}", "ERROR")
        logger.log("="*80 + "\n", "ERROR")
        logger.save_metrics()
        return False
    
    if front_mask is None:
        logger.log("\n" + "="*80, "ERROR")
        logger.log("❌ CRITICAL ERROR: Could not load front fabric mask", "ERROR")
        logger.log(f"   Path: {FRONT_FABRIC_MASK_PATH}", "ERROR")
        logger.log("   Make sure Step 2 (design extraction) has been run first.", "ERROR")
        logger.log("="*80 + "\n", "ERROR")
        logger.save_metrics()
        return False
    
    logger.log("", "INFO")
    
    # Extract fabric pixels and cluster
    fabric_pixels = extract_fabric_pixels(front_img, front_mask)
    if len(fabric_pixels) == 0:
        logger.log("No fabric pixels found in front image!", "ERROR")
        logger.save_metrics()
        return False
    
    centers, percentages = cluster_colors(fabric_pixels, N_CLUSTERS)
    
    logger.log("", "INFO")
    front_color_info = extract_fabric_color(front_img, front_mask, "front")
    if front_color_info:
        logger.log("", "INFO")
        save_color_results("front", front_color_info, centers, percentages)
        results["front"]["success"] = True
        results["front"]["color"] = front_color_info["dominant"]
    
    # Process BACK (if available)
    logger.log("\n" + "-"*80, "INFO")
    logger.log("PROCESSING BACK FABRIC COLOR (OPTIONAL)", "INFO")
    logger.log("-"*80 + "\n", "INFO")
    
    back_img, back_mask = load_image_and_mask(BACK_IMAGE_PATH, BACK_FABRIC_MASK_PATH)
    
    if back_img is not None and back_mask is not None:
        back_fabric_pixels = extract_fabric_pixels(back_img, back_mask)
        
        if len(back_fabric_pixels) > 0:
            back_centers, back_percentages = cluster_colors(back_fabric_pixels, N_CLUSTERS)
            
            logger.log("", "INFO")
            back_color_info = extract_fabric_color(back_img, back_mask, "back")
            if back_color_info:
                logger.log("", "INFO")
                save_color_results("back", back_color_info, back_centers, back_percentages)
                results["back"]["success"] = True
                results["back"]["color"] = back_color_info["dominant"]
        else:
            logger.log("No fabric pixels found in back image", "WARNING")
    else:
        logger.log("No back image available (optional)", "INFO")
    
    # Calculate total time
    total_time = time.time() - pipeline_start
    
    # Summary
    logger.log("\n" + "="*80, "INFO")
    logger.log("   FABRIC COLOR EXTRACTION SUMMARY", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    logger.log(f"Total pipeline time: {total_time:.3f}s", "SUCCESS")
    logger.log("", "INFO")
    
    if results["front"]["success"]:
        d = results["front"]["color"]
        logger.log("\u2705 FRONT FABRIC COLOR EXTRACTED", "SUCCESS")
        logger.log(f"   RGB: {d['rgb']}", "INFO")
        logger.log(f"   HEX: {d['hex']}", "INFO")
        logger.log(f"   Name: {d['name']}", "INFO")
        logger.log(f"   Coverage: {d['percentage']}%", "INFO")
        logger.log("", "INFO")
        logger.log(f"   Output files:", "INFO")
        logger.log(f"   - {OUTPUT_DIR}/front_fabric_color.json", "INFO")
        logger.log(f"   - {OUTPUT_DIR}/front_dominant_color.txt", "INFO")
        logger.log(f"   - {OUTPUT_DIR}/front_color_swatch.png", "INFO")
        logger.log(f"   - {OUTPUT_DIR}/front_dominant_color.png", "INFO")
    
    logger.log("", "INFO")
    
    if results["back"]["success"]:
        d = results["back"]["color"]
        logger.log("\u2705 BACK FABRIC COLOR EXTRACTED", "SUCCESS")
        logger.log(f"   RGB: {d['rgb']}", "INFO")
        logger.log(f"   HEX: {d['hex']}", "INFO")
        logger.log(f"   Name: {d['name']}", "INFO")
    else:
        logger.log("\u25cb BACK IMAGE: NOT PROVIDED", "INFO")
    
    logger.log("", "INFO")
    logger.log(f"\ud83d\udcca Detailed logs: {LOG_FILE}", "INFO")
    logger.log(f"\ud83d\udcc8 Metrics JSON: {LOG_JSON}", "INFO")
    logger.log("", "INFO")
    logger.log("="*80, "INFO")
    
    # Save metrics
    logger.save_metrics()
    
    # Validate critical files
    critical_files = [
        OUTPUT_DIR / "front_fabric_color.json",
        OUTPUT_DIR / "front_dominant_color.txt",
        OUTPUT_DIR / "front_color_swatch.png",
        OUTPUT_DIR / "front_dominant_color.png"
    ]
    
    all_valid = True
    for file_path in critical_files:
        if not file_path.exists():
            logger.log(f"\u274c CRITICAL FILE MISSING: {file_path}", "ERROR")
            all_valid = False
    
    if all_valid:
        logger.log("\n\u2705 ALL CRITICAL OUTPUT FILES VALIDATED", "SUCCESS")
        return True
    else:
        logger.log("\n\u274c SOME CRITICAL FILES ARE MISSING", "ERROR")
        return False


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run this script after Steps 1 and 2 with comprehensive logging.
    
    Requires:
    - segmentation_output/front_masked.png
    - design_output/front_fabric_mask.png
    
    Why we use fabric_mask (not garment_mask)?
    - fabric_mask = garment MINUS design
    - This gives us ONLY the plain fabric areas
    - No print colors contaminate our color extraction
    
    The result is the TRUE fabric color!
    
    Outputs to color_output/:
    - front_fabric_color.json (all color data)
    - front_dominant_color.txt (simple text format)
    - front_color_swatch.png (visual color distribution)
    - front_dominant_color.png (solid color preview)
    - step3_detailed_log.txt - Complete operation log
    - step3_metrics.json - Structured metrics
    
    Install with:
        pip install scikit-learn
    """
    print("\n" + "="*80)
    print("   FABRIC COLOR EXTRACTION - ENHANCED VERSION")
    print("   With K-means clustering and comprehensive logging")
    print("="*80 + "\n")
    
    success = run_color_extraction_pipeline()
    
    if success:
        try:
            print("\n" + "="*80)
            print("   ✅ STEP 3 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\n📁 Output directory: {OUTPUT_DIR}")
            print(f"📝 Detailed log: {LOG_FILE}")
            print(f"📊 Metrics JSON: {LOG_JSON}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\n➡️  Next step: Pattern generation from measurements")
            print("   Run: python step4_pattern_generation.py")
            print("\n" + "="*80)
        except UnicodeEncodeError:
            # Fallback for Windows console
            print("\n" + "="*80)
            print("   STEP 3 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\nOutput directory: {OUTPUT_DIR}")
            print(f"Detailed log: {LOG_FILE}")
            print(f"Metrics JSON: {LOG_JSON}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\nNext step: Pattern generation from measurements")
            print("   Run: python step4_pattern_generation.py")
            print("\n" + "="*80)
    else:
        try:
            print("\n" + "="*80)
            print("   ❌ STEP 3 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\n📝 Check detailed log: {LOG_FILE}")
            print(f"📊 Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
        except UnicodeEncodeError:
            # Fallback for Windows console
            print("\n" + "="*80)
            print("   STEP 3 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\nCheck detailed log: {LOG_FILE}")
            print(f"Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
