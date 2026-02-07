"""
STEP 2: Design Extraction (ENHANCED WITH COMPREHENSIVE LOGGING)
=========================
This script extracts printed designs (logos, graphics, text) from the T-shirt.

How it works:
- The fabric has a relatively uniform color
- The print has different colors/textures from the fabric
- We detect these differences to isolate the print

Key insight:
- Plain fabric = smooth, consistent color
- Printed areas = edges, texture, color variation

ENHANCEMENTS:
- Detailed logging of all detection algorithms
- Quality metrics for design extraction
- Parameter tuning logs
- Visual debug outputs at each stage
- Performance profiling
- Adaptive threshold tuning
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import time
import json
from datetime import datetime

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

# Logging configuration
LOG_FILE = OUTPUT_DIR / "step2_detailed_log.txt"
LOG_JSON = OUTPUT_DIR / "step2_metrics.json"
DEBUG_DIR = OUTPUT_DIR / "debug_visualizations"


# ============================================================
# LOGGING INFRASTRUCTURE
# ============================================================

class DesignExtractionLogger:
    """Comprehensive logging for design extraction pipeline"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "pipeline_start": datetime.now().isoformat(),
            "steps": [],
            "detections": {},
            "errors": [],
            "warnings": []
        }
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(LOG_FILE, 'w') as f:
            f.write(f"{'='*80}\n")
            f.write(f"STEP 2: DESIGN EXTRACTION - DETAILED LOG\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
    
    def log(self, message, level="INFO", data=None):
        """Log message to both console and file"""
        timestamp = time.time() - self.start_time
        formatted = f"[{timestamp:7.3f}s] [{level:7s}] {message}"
        
        # Console output with Unicode error handling for Windows
        try:
            if level == "ERROR":
                print(f"❌ {formatted}")
                self.metrics["errors"].append({"time": timestamp, "message": message})
            elif level == "WARNING":
                print(f"⚠️  {formatted}")
                self.metrics["warnings"].append({"time": timestamp, "message": message})
            elif level == "SUCCESS":
                print(f"✅ {formatted}")
            else:
                print(f"📝 {formatted}")
        except UnicodeEncodeError:
            # Fallback for Windows console
            print(formatted)
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted + "\n")
            if data:
                f.write(f"    Data: {json.dumps(data, indent=4)}\n")
        
        self.metrics["steps"].append({
            "time": timestamp,
            "level": level,
            "message": message,
            "data": data
        })
    
    def log_detection_stats(self, method, mask, total_pixels):
        """Log statistics for a detection method"""
        detected_pixels = np.count_nonzero(mask)
        coverage = (detected_pixels / total_pixels * 100) if total_pixels > 0 else 0
        
        stats = {
            "detected_pixels": int(detected_pixels),
            "total_pixels": int(total_pixels),
            "coverage_percent": float(coverage)
        }
        
        self.log(f"  {method} detected: {detected_pixels} pixels ({coverage:.2f}%)", "INFO", stats)
        self.metrics["detections"][method] = stats
        
        return stats
    
    def save_debug_image(self, image, name):
        """Save debug image"""
        try:
            path = DEBUG_DIR / f"{name}.png"
            cv2.imwrite(str(path), image)
            self.log(f"  Debug image saved: {name}.png", "INFO")
        except Exception as e:
            self.log(f"  Failed to save debug image {name}: {e}", "WARNING")
    
    def save_metrics(self):
        """Save final metrics to JSON"""
        self.metrics["pipeline_end"] = datetime.now().isoformat()
        self.metrics["total_time_seconds"] = time.time() - self.start_time
        
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2)
        
        self.log(f"Metrics saved to: {LOG_JSON.name}", "SUCCESS")

logger = DesignExtractionLogger()


# ============================================================
# HELPER FUNCTIONS (ENHANCED)
# ============================================================

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    logger.log(f"Output directories ready: {OUTPUT_DIR}", "SUCCESS")


def load_masked_image(path: Path) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Load a masked image and extract both the RGB and alpha channel.
    
    Args:
        path: Path to the masked image (BGRA format)
    
    Returns:
        Tuple of (BGR image, alpha mask) or (None, None) if not found
    """
    logger.log(f"Loading masked image: {path.name}", "INFO")
    
    if not path.exists():
        logger.log(f"  File not found: {path}", "ERROR")
        return None, None
    
    file_size = path.stat().st_size / (1024 * 1024)
    logger.log(f"  File size: {file_size:.2f} MB", "INFO")
    
    # Load with alpha channel (cv2.IMREAD_UNCHANGED keeps all channels)
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    
    if img is None:
        logger.log(f"  Failed to load image", "ERROR")
        return None, None
    
    logger.log(f"  Image shape: {img.shape}, dtype: {img.dtype}", "INFO")
    
    if len(img.shape) == 3 and img.shape[2] == 4:
        # Split into BGR and Alpha
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
        logger.log(f"  Extracted BGR and alpha channel", "SUCCESS")
        return bgr, alpha
    else:
        # No alpha channel, load mask separately
        bgr = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        mask_path = path.parent / path.name.replace("_masked", "_mask")
        
        if mask_path.exists():
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            logger.log(f"  Loaded separate mask from {mask_path.name}", "SUCCESS")
            return bgr, mask
        else:
            logger.log(f"  No alpha channel and mask file not found", "WARNING")
            # Create full mask
            h, w = bgr.shape[:2]
            mask = np.full((h, w), 255, dtype=np.uint8)
            return bgr, mask


# ============================================================
# DESIGN DETECTION METHODS
# ============================================================

def detect_edges(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Detect edges in the image with detailed logging.
    
    Edges indicate boundaries between:
    - Different colors in the print
    - Print and fabric
    
    Args:
        image: BGR image
        mask: Binary garment mask
    
    Returns:
        Edge map (white = edge pixels)
    """
    logger.log("Detecting edges (Canny algorithm)...", "INFO")
    start_time = time.time()
    
    # Convert to grayscale for edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    logger.log(f"  Converted to grayscale", "INFO")
    
    # Apply Gaussian blur to reduce noise
    blur_kernel = (5, 5)
    blur_sigma = 1.5
    blurred = cv2.GaussianBlur(gray, blur_kernel, blur_sigma)
    logger.log(f"  Applied Gaussian blur: kernel={blur_kernel}, sigma={blur_sigma}", "INFO")
    
    # Canny edge detection
    low_threshold = 50
    high_threshold = 150
    logger.log(f"  Canny thresholds: low={low_threshold}, high={high_threshold}", "INFO")
    
    edges = cv2.Canny(blurred, low_threshold, high_threshold)
    
    # Keep only edges within the garment
    edges = cv2.bitwise_and(edges, edges, mask=mask)
    
    elapsed = time.time() - start_time
    logger.log(f"  Edge detection complete in {elapsed:.3f}s", "SUCCESS")
    
    # Save debug image
    logger.save_debug_image(edges, "edges")
    
    return edges


def detect_texture_variation(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Detect texture variation in the image with detailed logging.
    
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
    logger.log("Analyzing texture variation...", "INFO")
    start_time = time.time()
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    
    # Calculate local mean using box filter
    kernel_size = 15
    logger.log(f"  Local variance kernel size: {kernel_size}x{kernel_size}", "INFO")
    
    local_mean = cv2.blur(gray, (kernel_size, kernel_size))
    
    # Calculate local variance
    # Variance = E[X^2] - E[X]^2
    local_sq_mean = cv2.blur(gray ** 2, (kernel_size, kernel_size))
    local_variance = local_sq_mean - local_mean ** 2
    
    # Normalize to 0-255 range
    local_variance = np.clip(local_variance, 0, None)
    max_var = np.max(local_variance)
    mean_var = np.mean(local_variance[mask > 0]) if np.any(mask > 0) else 0
    
    logger.log(f"  Variance stats: max={max_var:.2f}, mean={mean_var:.2f}", "INFO")
    
    if max_var > 0:
        texture_map = (local_variance / max_var * 255).astype(np.uint8)
    else:
        texture_map = np.zeros_like(gray, dtype=np.uint8)
        logger.log(f"  No variance detected (uniform image)", "WARNING")
    
    # Apply garment mask
    texture_map = cv2.bitwise_and(texture_map, texture_map, mask=mask)
    
    elapsed = time.time() - start_time
    logger.log(f"  Texture analysis complete in {elapsed:.3f}s", "SUCCESS")
    
    # Save debug image
    logger.save_debug_image(texture_map, "texture_variance")
    
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
    logger.log("Detecting color outliers...", "INFO")
    start_time = time.time()
    
    # Convert to LAB color space (better for color distance)
    # L = Lightness, A = green-red, B = blue-yellow
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    logger.log(f"  Converted to LAB color space", "INFO")
    
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
    
    logger.log(f"  Sampled {len(fabric_pixels)} fabric pixels", "INFO")
    
    if len(fabric_pixels) < 100:
        # Not enough samples, use entire garment
        logger.log(f"  Insufficient samples, using entire garment", "WARNING")
        fabric_pixels = lab[mask > 0]
    
    if len(fabric_pixels) == 0:
        logger.log(f"  No fabric pixels found!", "ERROR")
        return np.zeros_like(mask)
    
    # Calculate fabric color statistics
    fabric_mean = np.mean(fabric_pixels, axis=0)
    fabric_std = np.std(fabric_pixels, axis=0)
    
    logger.log(f"  Fabric color (LAB): L={fabric_mean[0]:.1f}, A={fabric_mean[1]:.1f}, B={fabric_mean[2]:.1f}", "INFO")
    logger.log(f"  Fabric std dev: L={fabric_std[0]:.1f}, A={fabric_std[1]:.1f}, B={fabric_std[2]:.1f}", "INFO")
    
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
    logger.log(f"  Outlier threshold: {threshold} std deviations", "INFO")
    
    outlier_mask = (total_distance > threshold).astype(np.uint8) * 255
    
    # Apply garment mask
    outlier_mask = cv2.bitwise_and(outlier_mask, outlier_mask, mask=mask)
    
    outlier_pixels = np.count_nonzero(outlier_mask)
    total_pixels = np.count_nonzero(mask)
    outlier_percent = (outlier_pixels / total_pixels * 100) if total_pixels > 0 else 0
    
    elapsed = time.time() - start_time
    logger.log(f"  Color outlier detection complete in {elapsed:.3f}s", "SUCCESS")
    logger.log(f"  Outliers: {outlier_pixels}/{total_pixels} pixels ({outlier_percent:.2f}%)", "INFO")
    
    # Save debug image
    logger.save_debug_image(outlier_mask, "color_outliers")
    
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
    Main design extraction function with comprehensive logging.
    
    Args:
        image: BGR image of garment
        mask: Binary garment mask
        name: Name for output files
    
    Returns:
        Tuple of (design_mask, fabric_mask)
    """
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"EXTRACTING DESIGN: {name.upper()}", "INFO")
    logger.log(f"{'='*60}", "INFO")
    
    extraction_start = time.time()
    total_pixels = np.count_nonzero(mask)
    logger.log(f"Total garment pixels: {total_pixels}", "INFO")
    logger.log("", "INFO")
    
    # Step 1: Detect edges (boundaries in the print)
    logger.log("STEP 1: Edge Detection", "INFO")
    logger.log("-" * 40, "INFO")
    edges = detect_edges(image, mask)
    logger.log_detection_stats("edge_detection", edges, total_pixels)
    logger.log("", "INFO")
    
    # Step 2: Detect texture variation
    logger.log("STEP 2: Texture Variation Analysis", "INFO")
    logger.log("-" * 40, "INFO")
    texture = detect_texture_variation(image, mask)
    
    logger.log_detection_stats("texture_variation", texture, total_pixels)
    logger.log("", "INFO")
    
    # Step 3: Detect color outliers
    logger.log("STEP 3: Color Outlier Detection", "INFO")
    logger.log("-" * 40, "INFO")
    color_outliers = detect_color_outliers(image, mask)
    logger.log_detection_stats("color_outliers", color_outliers, total_pixels)
    logger.log("", "INFO")
    
    # Step 4: Combine methods
    logger.log("STEP 4: Combining Detection Methods", "INFO")
    logger.log("-" * 40, "INFO")
    design_mask = combine_detection_methods(edges, texture, color_outliers, mask)
    
    # Calculate coverage
    design_pixels = np.count_nonzero(design_mask)
    coverage = (design_pixels / total_pixels * 100) if total_pixels > 0 else 0
    logger.log(f"Final design coverage: {coverage:.1f}% ({design_pixels}/{total_pixels} pixels)", "SUCCESS")
    logger.log("", "INFO")
    
    # Create fabric-only mask
    fabric_mask = create_fabric_only_mask(mask, design_mask)
    fabric_pixels = np.count_nonzero(fabric_mask)
    fabric_coverage = (fabric_pixels / total_pixels * 100) if total_pixels > 0 else 0
    logger.log(f"Fabric-only coverage: {fabric_coverage:.1f}% ({fabric_pixels}/{total_pixels} pixels)", "INFO")
    
    # Get design bounding box
    bbox = get_design_bounding_box(design_mask)
    if bbox[2] > 0 and bbox[3] > 0:
        logger.log(f"Design bounding box: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}", "SUCCESS")
    else:
        logger.log("No distinct design detected (plain fabric or full coverage print)", "INFO")
    
    extraction_time = time.time() - extraction_start
    logger.log("", "INFO")
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"{name.upper()} EXTRACTION COMPLETE in {extraction_time:.3f}s", "SUCCESS")
    logger.log(f"{'='*60}", "INFO")
    
    return design_mask, fabric_mask


def save_design_results(
    name: str,
    image: np.ndarray,
    garment_mask: np.ndarray,
    design_mask: np.ndarray,
    fabric_mask: np.ndarray
):
    """
    Save all design extraction results with validation.
    
    Args:
        name: Base name for files
        image: Original BGR image
        garment_mask: Full garment mask
        design_mask: Design-only mask
        fabric_mask: Fabric-only mask
    """
    logger.log(f"Saving {name} results...", "INFO")
    saved_files = []
    
    try:
        # Save design mask
        design_mask_path = OUTPUT_DIR / f"{name}_design_mask.png"
        cv2.imwrite(str(design_mask_path), design_mask)
        size = design_mask_path.stat().st_size
        saved_files.append(("design_mask", design_mask_path, size))
        logger.log(f"  ✓ {name}_design_mask.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Save fabric mask
        fabric_mask_path = OUTPUT_DIR / f"{name}_fabric_mask.png"
        cv2.imwrite(str(fabric_mask_path), fabric_mask)
        size = fabric_mask_path.stat().st_size
        saved_files.append(("fabric_mask", fabric_mask_path, size))
        logger.log(f"  ✓ {name}_fabric_mask.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Save design as transparent image
        design_image = extract_design_image(image, design_mask)
        design_img_path = OUTPUT_DIR / f"{name}_design.png"
        cv2.imwrite(str(design_img_path), design_image)
        size = design_img_path.stat().st_size
        saved_files.append(("design_image", design_img_path, size))
        logger.log(f"  ✓ {name}_design.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Save numpy arrays for programmatic use
        npy1 = OUTPUT_DIR / f"{name}_design_mask.npy"
        npy2 = OUTPUT_DIR / f"{name}_fabric_mask.npy"
        np.save(str(npy1), design_mask)
        np.save(str(npy2), fabric_mask)
        logger.log(f"  ✓ NumPy arrays saved", "SUCCESS")
        
        # Create visualization overlay
        visualization = create_visualization(image, garment_mask, design_mask)
        vis_path = OUTPUT_DIR / f"{name}_visualization.png"
        cv2.imwrite(str(vis_path), visualization)
        size = vis_path.stat().st_size
        saved_files.append(("visualization", vis_path, size))
        logger.log(f"  ✓ {name}_visualization.png ({size/1024:.1f} KB)", "SUCCESS")
        
        # Validate all files exist and have content
        all_valid = True
        for file_type, file_path, file_size in saved_files:
            if not file_path.exists():
                logger.log(f"  ERROR: {file_path.name} not created!", "ERROR")
                all_valid = False
            elif file_size == 0:
                logger.log(f"  ERROR: {file_path.name} is empty!", "ERROR")
                all_valid = False
        
        if all_valid:
            logger.log(f"All {name} files validated successfully", "SUCCESS")
        
    except Exception as e:
        logger.log(f"Error saving {name} results: {e}", "ERROR")


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
    Run the complete design extraction pipeline with comprehensive logging.
    """
    logger.log("\n" + "="*80, "INFO")
    logger.log("   STEP 2: DESIGN EXTRACTION PIPELINE (ENHANCED)", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    pipeline_start = time.time()
    
    ensure_output_dir()
    
    results = {"front": {"success": False}, "back": {"success": False}}
    
    # Process FRONT image
    logger.log("\n" + "-"*80, "INFO")
    logger.log("PROCESSING FRONT IMAGE (REQUIRED)", "INFO")
    logger.log("-"*80 + "\n", "INFO")
    
    front_img, front_mask = load_masked_image(FRONT_MASKED_PATH)
    
    if front_img is None:
        logger.log("\n" + "="*80, "ERROR")
        logger.log("❌ CRITICAL ERROR: Could not load front image", "ERROR")
        logger.log(f"   Path: {FRONT_MASKED_PATH}", "ERROR")
        logger.log("   Make sure Step 1 (segmentation) has been run first.", "ERROR")
        logger.log("="*80 + "\n", "ERROR")
        logger.save_metrics()
        return False
    
    logger.log(f"Loaded front image: {front_img.shape[1]}x{front_img.shape[0]} pixels", "SUCCESS")
    logger.log("", "INFO")
    
    front_design_mask, front_fabric_mask = extract_design(front_img, front_mask, "front")
    logger.log("", "INFO")
    save_design_results("front", front_img, front_mask, front_design_mask, front_fabric_mask)
    results["front"]["success"] = True
    
    # Process BACK image (if available)
    logger.log("\n" + "-"*80, "INFO")
    logger.log("PROCESSING BACK IMAGE (OPTIONAL)", "INFO")
    logger.log("-"*80 + "\n", "INFO")
    
    back_img, back_mask = load_masked_image(BACK_MASKED_PATH)
    
    if back_img is not None:
        logger.log(f"Loaded back image: {back_img.shape[1]}x{back_img.shape[0]} pixels", "SUCCESS")
        logger.log("", "INFO")
        
        back_design_mask, back_fabric_mask = extract_design(back_img, back_mask, "back")
        logger.log("", "INFO")
        save_design_results("back", back_img, back_mask, back_design_mask, back_fabric_mask)
        results["back"]["success"] = True
    else:
        logger.log("No back image available (optional)", "INFO")
    
    # Calculate total time
    total_time = time.time() - pipeline_start
    
    # Summary
    logger.log("\n" + "="*80, "INFO")
    logger.log("   DESIGN EXTRACTION SUMMARY", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    logger.log(f"Total pipeline time: {total_time:.3f}s", "SUCCESS")
    logger.log("", "INFO")
    
    if results["front"]["success"]:
        logger.log("✅ FRONT DESIGN EXTRACTED", "SUCCESS")
        logger.log(f"   - Design mask: {OUTPUT_DIR}/front_design_mask.png", "INFO")
        logger.log(f"   - Design image: {OUTPUT_DIR}/front_design.png", "INFO")
        logger.log(f"   - Fabric mask: {OUTPUT_DIR}/front_fabric_mask.png", "INFO")
        logger.log(f"   - Visualization: {OUTPUT_DIR}/front_visualization.png", "INFO")
        logger.log(f"   - Debug images: {DEBUG_DIR}/", "INFO")
    
    logger.log("", "INFO")
    
    if results["back"]["success"]:
        logger.log("✅ BACK DESIGN EXTRACTED", "SUCCESS")
        logger.log(f"   - Design mask: {OUTPUT_DIR}/back_design_mask.png", "INFO")
        logger.log(f"   - Design image: {OUTPUT_DIR}/back_design.png", "INFO")
    else:
        logger.log("○ BACK IMAGE: NOT PROVIDED", "INFO")
    
    logger.log("", "INFO")
    logger.log(f"📊 Detailed logs: {LOG_FILE}", "INFO")
    logger.log(f"📈 Metrics JSON: {LOG_JSON}", "INFO")
    logger.log("", "INFO")
    logger.log("="*80, "INFO")
    
    # Save metrics
    logger.save_metrics()
    
    # Validate critical files
    critical_files = [
        OUTPUT_DIR / "front_design_mask.png",
        OUTPUT_DIR / "front_fabric_mask.png",
        OUTPUT_DIR / "front_design_mask.npy",
        OUTPUT_DIR / "front_fabric_mask.npy"
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
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Run this script after Step 1 (segmentation) with comprehensive logging.
    #
    # Expects these files in segmentation_output/:
    # - front_masked.png (required)
    # - front_mask.png (required)
    # - back_masked.png (optional)
    # - back_mask.png (optional)
    #
    # Outputs to design_output/:
    # - front_design_mask.png (binary mask of print)
    # - front_design.png (extracted print with transparency)
    # - front_fabric_mask.png (mask of plain fabric areas)
    # - front_visualization.png (color-coded overlay)
    # - step2_detailed_log.txt - Complete operation log
    # - step2_metrics.json - Structured metrics
    # - debug_visualizations/ - Debug images for each detection method
    
    print("\n" + "="*80)
    print("   DESIGN EXTRACTION - ENHANCED VERSION")
    print("   With comprehensive logging and quality metrics")
    print("="*80 + "\n")
    
    success = run_design_extraction_pipeline()
    
    if success:
        try:
            print("\n" + "="*80)
            print("   ✅ STEP 2 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\n📁 Output directory: {OUTPUT_DIR}")
            print(f"📝 Detailed log: {LOG_FILE}")
            print(f"📊 Metrics JSON: {LOG_JSON}")
            print(f"🎨 Debug visualizations: {DEBUG_DIR}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\n➡️  Next step: Fabric color extraction")
            print("   Run: python step3_color_extraction.py")
            print("\n" + "="*80)
        except UnicodeEncodeError:
            print("\n" + "="*80)
            print("   STEP 2 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\nOutput directory: {OUTPUT_DIR}")
            print(f"Detailed log: {LOG_FILE}")
            print(f"Metrics JSON: {LOG_JSON}")
            print(f"Debug visualizations: {DEBUG_DIR}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\nNext step: Fabric color extraction")
            print("   Run: python step3_color_extraction.py")
            print("\n" + "="*80)
    else:
        try:
            print("\n" + "="*80)
            print("   ❌ STEP 2 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\n📝 Check detailed log: {LOG_FILE}")
            print(f"📊 Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
        except UnicodeEncodeError:
            print("\n" + "="*80)
            print("   STEP 2 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\nCheck detailed log: {LOG_FILE}")
            print(f"Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
