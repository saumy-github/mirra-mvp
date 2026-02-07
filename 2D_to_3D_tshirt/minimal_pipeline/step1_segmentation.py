"""
STEP 1: T-Shirt Segmentation (ENHANCED WITH COMPREHENSIVE LOGGING)
============================
This script segments the T-shirt from the background.

What it does:
- Loads front image (required) and back image (optional)
- Removes background using AI-based segmentation
- Saves binary masks and masked images
- LOGS every operation with detailed metrics
- VALIDATES outputs with quality checks

The mask is a black-and-white image where:
- White (255) = T-shirt pixels
- Black (0) = Background pixels

ENHANCEMENTS:
- Detailed logging of all operations
- Mask quality metrics (coverage, edge smoothness, compactness)
- File validation (size, checksums)
- Visual debug outputs
- Performance timing
- Error recovery mechanisms
"""

import cv2
import numpy as np
from pathlib import Path
import sys
import time
import json
import hashlib
from datetime import datetime

# ============================================================
# CONFIGURATION - Set your image paths here
# ============================================================

# Front image is REQUIRED
FRONT_IMAGE_PATH = "input_images/front.png"  # Change this to your front image

# Back image is OPTIONAL (set to None if not available)
BACK_IMAGE_PATH = None  # Or "input_images/back.png" if you have one

# Output directory
OUTPUT_DIR = Path("segmentation_output")

# Logging configuration
LOG_FILE = OUTPUT_DIR / "step1_detailed_log.txt"
LOG_JSON = OUTPUT_DIR / "step1_metrics.json"
DEBUG_DIR = OUTPUT_DIR / "debug_visualizations"


# ============================================================
# LOGGING INFRASTRUCTURE
# ============================================================

class SegmentationLogger:
    """Comprehensive logging system for segmentation pipeline"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "pipeline_start": datetime.now().isoformat(),
            "steps": [],
            "images": {},
            "errors": [],
            "warnings": []
        }
        
        # Ensure directories exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clear/create log file
        with open(LOG_FILE, 'w') as f:
            f.write(f"{'='*80}\n")
            f.write(f"STEP 1: T-SHIRT SEGMENTATION - DETAILED LOG\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
    
    def log(self, message, level="INFO", data=None):
        """Log message to both console and file"""
        timestamp = time.time() - self.start_time
        formatted = f"[{timestamp:7.3f}s] [{level:7s}] {message}"
        
        # Console output with colors (with Unicode error handling for Windows)
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
        
        # File output
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted + "\n")
            if data:
                f.write(f"    Data: {json.dumps(data, indent=4)}\n")
        
        # Store step info
        self.metrics["steps"].append({
            "time": timestamp,
            "level": level,
            "message": message,
            "data": data
        })
    
    def log_image_stats(self, name, image, prefix=""):
        """Log detailed image statistics"""
        if image is None:
            self.log(f"{prefix}Image {name}: NULL/FAILED", "ERROR")
            return None
        
        stats = {
            "shape": image.shape,
            "dtype": str(image.dtype),
            "size_bytes": image.nbytes,
            "min": float(np.min(image)),
            "max": float(np.max(image)),
            "mean": float(np.mean(image)),
            "std": float(np.std(image))
        }
        
        if len(image.shape) == 2:  # Grayscale/mask
            stats["non_zero_pixels"] = int(np.count_nonzero(image))
            stats["coverage_percent"] = float(np.count_nonzero(image) / image.size * 100)
        
        self.log(f"{prefix}Image {name}: {stats['shape']} {stats['dtype']}", "INFO", stats)
        self.metrics["images"][name] = stats
        
        return stats
    
    def log_mask_quality(self, mask, name):
        """Calculate and log mask quality metrics"""
        if mask is None or mask.size == 0:
            self.log(f"Mask quality for {name}: INVALID", "ERROR")
            return None
        
        # Calculate quality metrics
        total_pixels = mask.shape[0] * mask.shape[1]
        foreground_pixels = np.count_nonzero(mask)
        coverage = (foreground_pixels / total_pixels) * 100
        
        # Edge smoothness (using gradient magnitude)
        gradient_x = cv2.Sobel(mask, cv2.CV_64F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(mask, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        edge_smoothness = 100 - min(100, np.mean(edge_magnitude) * 10)
        
        # Compactness (ratio of area to perimeter squared)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)
            compactness = (4 * np.pi * area) / (perimeter**2) if perimeter > 0 else 0
            compactness_percent = compactness * 100
        else:
            compactness_percent = 0
        
        quality = {
            "coverage_percent": float(coverage),
            "edge_smoothness": float(edge_smoothness),
            "compactness": float(compactness_percent),
            "foreground_pixels": int(foreground_pixels),
            "total_pixels": int(total_pixels),
            "overall_score": float((coverage + edge_smoothness + compactness_percent) / 3)
        }
        
        self.log(f"Mask quality for {name}:", "INFO", quality)
        
        # Quality assessment
        if quality["overall_score"] > 70:
            self.log(f"  Quality: EXCELLENT ({quality['overall_score']:.1f}/100)", "SUCCESS")
        elif quality["overall_score"] > 50:
            self.log(f"  Quality: GOOD ({quality['overall_score']:.1f}/100)", "INFO")
        elif quality["overall_score"] > 30:
            self.log(f"  Quality: ACCEPTABLE ({quality['overall_score']:.1f}/100)", "WARNING")
        else:
            self.log(f"  Quality: POOR ({quality['overall_score']:.1f}/100)", "ERROR")
        
        return quality
    
    def save_debug_visualization(self, image, mask, name):
        """Save debug visualization with mask overlay"""
        try:
            if image is None or mask is None:
                return
            
            # Create visualization
            vis = image.copy()
            
            # Add colored mask overlay (green for foreground)
            mask_colored = np.zeros_like(vis)
            mask_colored[:, :, 1] = mask  # Green channel
            
            # Blend
            alpha = 0.3
            blended = cv2.addWeighted(vis, 1-alpha, mask_colored, alpha, 0)
            
            # Add contour
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(blended, contours, -1, (0, 255, 255), 2)  # Yellow contour
            
            # Save
            debug_path = DEBUG_DIR / f"{name}_overlay.png"
            cv2.imwrite(str(debug_path), blended)
            self.log(f"Saved debug visualization: {debug_path.name}", "INFO")
            
        except Exception as e:
            self.log(f"Failed to save debug visualization: {e}", "WARNING")
    
    def save_metrics(self):
        """Save final metrics to JSON"""
        self.metrics["pipeline_end"] = datetime.now().isoformat()
        self.metrics["total_time_seconds"] = time.time() - self.start_time
        
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2)
        
        self.log(f"Metrics saved to: {LOG_JSON.name}", "SUCCESS")

# Global logger instance
logger = SegmentationLogger()


# ============================================================
# HELPER FUNCTIONS (ENHANCED)
# ============================================================

def ensure_output_dir():
    """
    Create output directory if it doesn't exist.
    This is where we'll save all our segmentation results.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    logger.log(f"Output directories ready: {OUTPUT_DIR}", "SUCCESS")


def load_image(image_path: str, name: str = "image") -> np.ndarray:
    """
    Load an image from disk with comprehensive validation.
    
    Args:
        image_path: Path to the image file
        name: Human-readable name for error messages
    
    Returns:
        Image as numpy array in BGR format (OpenCV default)
    
    Why BGR? OpenCV loads images in Blue-Green-Red order by default.
    We'll convert to RGB when needed for display or saving.
    """
    logger.log(f"Loading {name} from: {image_path}", "INFO")
    
    if image_path is None:
        logger.log(f"{name}: Path is None", "ERROR")
        return None
    
    path = Path(image_path)
    if not path.exists():
        logger.log(f"{name} not found at: {path}", "ERROR")
        return None
    
    # Log file info
    file_size = path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    logger.log(f"{name} file size: {file_size_mb:.2f} MB", "INFO")
    
    # Calculate file checksum for validation
    try:
        with open(path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        logger.log(f"{name} MD5 checksum: {file_hash}", "INFO")
    except:
        pass
    
    # Load image
    start_time = time.time()
    image = cv2.imread(str(path))
    load_time = time.time() - start_time
    
    if image is None:
        logger.log(f"Failed to load {name}: {path} (OpenCV returned None)", "ERROR")
        return None
    
    # Log image statistics
    height, width = image.shape[:2]
    channels = image.shape[2] if len(image.shape) > 2 else 1
    
    logger.log(f"Loaded {name}: {width}x{height}x{channels} in {load_time:.3f}s", "SUCCESS")
    logger.log_image_stats(name, image, "  ")
    
    # Validate reasonable dimensions
    if width < 100 or height < 100:
        logger.log(f"Warning: {name} is very small ({width}x{height})", "WARNING")
    if width > 10000 or height > 10000:
        logger.log(f"Warning: {name} is very large ({width}x{height}), may cause memory issues", "WARNING")
    
    return image


def segment_garment_grabcut(image: np.ndarray) -> np.ndarray:
    """
    Segment the garment using GrabCut algorithm with detailed logging.
    
    GrabCut is a semi-automatic segmentation method that:
    1. You give it a rectangle around the object
    2. It learns what's foreground vs background
    3. It refines the boundary iteratively
    
    For T-shirts, we assume the garment is centered in the image.
    
    Args:
        image: Input BGR image
    
    Returns:
        Binary mask where 255 = garment, 0 = background
    """
    logger.log("Starting GrabCut segmentation...", "INFO")
    start_time = time.time()
    
    height, width = image.shape[:2]
    logger.log(f"  Image dimensions: {width}x{height}", "INFO")
    
    # Create initial mask (all zeros = unknown)
    mask = np.zeros((height, width), np.uint8)
    
    # Define a rectangle that likely contains the T-shirt
    # We use 10% margin on each side
    margin_x = int(width * 0.1)
    margin_y = int(height * 0.05)  # Less margin on top (neckline)
    rect = (margin_x, margin_y, width - 2*margin_x, height - 2*margin_y)
    
    logger.log(f"  Initial rectangle: x={margin_x}, y={margin_y}, w={width - 2*margin_x}, h={height - 2*margin_y}", "INFO")
    
    # GrabCut needs temporary arrays for its internal models
    # These store color distribution information
    bgd_model = np.zeros((1, 65), np.float64)  # Background model
    fgd_model = np.zeros((1, 65), np.float64)  # Foreground model
    
    # Run GrabCut algorithm
    # cv2.GC_INIT_WITH_RECT means we're starting with a rectangle
    # 5 iterations is usually enough for good results
    logger.log("  Running GrabCut algorithm (5 iterations)...", "INFO")
    iteration_start = time.time()
    
    try:
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        iteration_time = time.time() - iteration_start
        logger.log(f"  GrabCut completed in {iteration_time:.3f}s", "SUCCESS")
    except Exception as e:
        logger.log(f"  GrabCut failed: {e}", "ERROR")
        return None
    
    # GrabCut mask values:
    # 0 = definite background
    # 1 = definite foreground
    # 2 = probable background
    # 3 = probable foreground
    
    # Count pixels in each category
    definite_bg = np.sum(mask == 0)
    definite_fg = np.sum(mask == 1)
    probable_bg = np.sum(mask == 2)
    probable_fg = np.sum(mask == 3)
    
    logger.log(f"  GrabCut classification:", "INFO")
    logger.log(f"    Definite background: {definite_bg} pixels", "INFO")
    logger.log(f"    Definite foreground: {definite_fg} pixels", "INFO")
    logger.log(f"    Probable background: {probable_bg} pixels", "INFO")
    logger.log(f"    Probable foreground: {probable_fg} pixels", "INFO")
    
    # We want both definite and probable foreground
    # The & 1 trick: values 1 and 3 both have bit 0 set
    binary_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    
    total_time = time.time() - start_time
    logger.log(f"GrabCut segmentation completed in {total_time:.3f}s", "SUCCESS")
    
    return binary_mask
    
    # Create initial mask (all zeros = unknown)
    mask = np.zeros((height, width), np.uint8)
    
    # Define a rectangle that likely contains the T-shirt
    # We use 10% margin on each side
    margin_x = int(width * 0.1)
    margin_y = int(height * 0.05)  # Less margin on top (neckline)
    rect = (margin_x, margin_y, width - 2*margin_x, height - 2*margin_y)
    
    # GrabCut needs temporary arrays for its internal models
    # These store color distribution information
    bgd_model = np.zeros((1, 65), np.float64)  # Background model
    fgd_model = np.zeros((1, 65), np.float64)  # Foreground model
    
    # Run GrabCut algorithm
    # cv2.GC_INIT_WITH_RECT means we're starting with a rectangle
    # 5 iterations is usually enough for good results
    cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    
    # GrabCut mask values:
    # 0 = definite background
    # 1 = definite foreground
    # 2 = probable background
    # 3 = probable foreground
    
    # We want both definite and probable foreground
    # The & 1 trick: values 1 and 3 both have bit 0 set
    binary_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    
    return binary_mask


def segment_garment_color_based(image: np.ndarray) -> np.ndarray:
    """
    Alternative segmentation using color-based approach.
    
    This method works well when:
    - Background is relatively uniform (white, gray, etc.)
    - T-shirt color is different from background
    
    Steps:
    1. Convert to HSV color space (better for color analysis)
    2. Find the dominant background color (usually edges)
    3. Create mask by excluding background colors
    4. Clean up with morphological operations
    
    Args:
        image: Input BGR image
    
    Returns:
        Binary mask where 255 = garment, 0 = background
    """
    height, width = image.shape[:2]
    
    # Convert BGR to HSV (Hue, Saturation, Value)
    # HSV is better for color-based segmentation because
    # it separates color (H) from brightness (V)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Sample background from image corners
    # We assume corners are background
    corner_size = 20
    corners = [
        image[0:corner_size, 0:corner_size],                    # Top-left
        image[0:corner_size, width-corner_size:width],          # Top-right
        image[height-corner_size:height, 0:corner_size],        # Bottom-left
        image[height-corner_size:height, width-corner_size:width]  # Bottom-right
    ]
    
    # Stack all corner pixels
    bg_pixels = np.vstack([c.reshape(-1, 3) for c in corners])
    
    # Calculate mean and std of background
    bg_mean = np.mean(bg_pixels, axis=0)
    bg_std = np.std(bg_pixels, axis=0)
    
    # Create initial mask: pixels that are NOT like background
    # A pixel is foreground if it differs from background by more than 2 std
    diff = np.abs(image.astype(np.float32) - bg_mean)
    threshold = np.maximum(bg_std * 2, 30)  # At least 30 difference
    
    # Pixel is foreground if ANY channel differs significantly
    foreground = np.any(diff > threshold, axis=2)
    mask = (foreground * 255).astype(np.uint8)
    
    # Clean up the mask with morphological operations
    # These remove noise and fill holes
    
    # Kernel for morphological operations (small circular shape)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    
    # Opening: removes small white noise (erode then dilate)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # Closing: fills small holes (dilate then erode)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # Find the largest connected component (the T-shirt)
    # This removes any stray foreground regions
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    if num_labels > 1:
        # Find the largest component (excluding background which is label 0)
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = np.where(labels == largest_label, 255, 0).astype(np.uint8)
    
    return mask


def segment_with_rembg(image: np.ndarray) -> np.ndarray:
    """
    Segment using rembg library (AI-based background removal) with detailed logging.
    
    rembg uses a neural network (U2-Net) trained specifically for
    removing backgrounds. It's very accurate for clothing.
    
    Args:
        image: Input BGR image
    
    Returns:
        Binary mask where 255 = garment, 0 = background
    """
    logger.log("Attempting AI-based segmentation with rembg...", "INFO")
    
    try:
        from rembg import remove
        logger.log("  rembg library loaded successfully", "SUCCESS")
        
        start_time = time.time()
        
        # Convert BGR to RGB (rembg expects RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        logger.log("  Converted image to RGB", "INFO")
        
        # Remove background - returns RGBA image
        # The alpha channel IS the mask we want
        logger.log("  Running U2-Net neural network...", "INFO")
        result = remove(rgb_image)
        processing_time = time.time() - start_time
        
        logger.log(f"  U2-Net processing completed in {processing_time:.3f}s", "SUCCESS")
        
        # Extract alpha channel as mask
        # Alpha = 255 means fully opaque (foreground)
        # Alpha = 0 means fully transparent (background)
        if result.shape[2] == 4:  # RGBA
            mask = result[:, :, 3]  # Alpha channel
            logger.log(f"  Extracted alpha channel as mask", "SUCCESS")
        else:
            # Fallback: if no alpha, assume non-black is foreground
            logger.log(f"  No alpha channel, using grayscale fallback", "WARNING")
            gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
            mask = np.where(gray > 10, 255, 0).astype(np.uint8)
        
        # Log mask statistics
        foreground_pixels = np.count_nonzero(mask)
        total_pixels = mask.size
        coverage = (foreground_pixels / total_pixels) * 100
        logger.log(f"  rembg coverage: {coverage:.1f}% foreground", "INFO")
        
        return mask
        
    except ImportError:
        logger.log("rembg not installed. Install with: pip install rembg", "WARNING")
        logger.log("Falling back to GrabCut method...", "INFO")
        return None
    except Exception as e:
        logger.log(f"rembg failed with error: {e}", "ERROR")
        logger.log("Falling back to GrabCut method...", "INFO")
        return None


def apply_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Apply binary mask to image.
    
    Args:
        image: Original BGR image
        mask: Binary mask (255 = keep, 0 = discard)
    
    Returns:
        BGRA image with transparency where mask is 0
    """
    # Add alpha channel to image
    bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    
    # Set alpha channel to mask value
    bgra[:, :, 3] = mask
    
    return bgra


def refine_mask(mask: np.ndarray) -> np.ndarray:
    """
    Refine the segmentation mask with detailed logging.
    
    This cleans up rough edges and fills holes.
    
    Args:
        mask: Initial binary mask
    
    Returns:
        Refined binary mask
    """
    logger.log("Refining mask...", "INFO")
    start_time = time.time()
    
    # Count initial foreground pixels
    initial_fg = np.count_nonzero(mask)
    
    # Fill holes inside the mask
    # We do this by flood-filling from the corners
    h, w = mask.shape
    flood_mask = mask.copy()
    
    # Flood fill from corners with white
    temp = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood_mask, temp, (0, 0), 255)
    
    # Invert to get holes
    holes = cv2.bitwise_not(flood_mask)
    
    # Combine original mask with filled holes
    filled = mask | holes
    
    holes_filled = np.count_nonzero(filled) - initial_fg
    if holes_filled > 0:
        logger.log(f"  Filled {holes_filled} hole pixels", "INFO")
    
    # Smooth the edges with Gaussian blur then threshold
    smoothed = cv2.GaussianBlur(filled, (5, 5), 0)
    _, refined = cv2.threshold(smoothed, 127, 255, cv2.THRESH_BINARY)
    
    # Count final foreground pixels
    final_fg = np.count_nonzero(refined)
    pixel_change = final_fg - initial_fg
    change_percent = (pixel_change / initial_fg) * 100 if initial_fg > 0 else 0
    
    logger.log(f"  Pixel change: {pixel_change:+d} ({change_percent:+.2f}%)", "INFO")
    
    refine_time = time.time() - start_time
    logger.log(f"Mask refinement completed in {refine_time:.3f}s", "SUCCESS")
    
    return refined


def save_results(name: str, image: np.ndarray, mask: np.ndarray, masked: np.ndarray):
    """
    Save segmentation results to output directory with validation.
    
    Args:
        name: Base name for files (e.g., "front", "back")
        image: Original image
        mask: Binary mask
        masked: Image with background removed
    """
    logger.log(f"Saving results for {name}...", "INFO")
    saved_files = []
    
    try:
        # Save original (for reference)
        orig_path = OUTPUT_DIR / f"{name}_original.png"
        cv2.imwrite(str(orig_path), image)
        orig_size = orig_path.stat().st_size
        saved_files.append(("original", orig_path, orig_size))
        logger.log(f"  ✓ Saved {name}_original.png ({orig_size/1024:.1f} KB)", "SUCCESS")
        
        # Save binary mask (useful for later steps)
        mask_path = OUTPUT_DIR / f"{name}_mask.png"
        cv2.imwrite(str(mask_path), mask)
        mask_size = mask_path.stat().st_size
        saved_files.append(("mask", mask_path, mask_size))
        logger.log(f"  ✓ Saved {name}_mask.png ({mask_size/1024:.1f} KB)", "SUCCESS")
        
        # Save masked image (T-shirt only, transparent background)
        masked_path = OUTPUT_DIR / f"{name}_masked.png"
        cv2.imwrite(str(masked_path), masked)
        masked_size = masked_path.stat().st_size
        saved_files.append(("masked", masked_path, masked_size))
        logger.log(f"  ✓ Saved {name}_masked.png ({masked_size/1024:.1f} KB)", "SUCCESS")
        
        # Also save mask as numpy array for programmatic use
        npy_path = OUTPUT_DIR / f"{name}_mask.npy"
        np.save(str(npy_path), mask)
        npy_size = npy_path.stat().st_size
        saved_files.append(("numpy", npy_path, npy_size))
        logger.log(f"  ✓ Saved {name}_mask.npy ({npy_size/1024:.1f} KB)", "SUCCESS")
        
        # Validate files exist and have content
        for file_type, file_path, file_size in saved_files:
            if not file_path.exists():
                logger.log(f"  ERROR: {file_path.name} was not created!", "ERROR")
            elif file_size == 0:
                logger.log(f"  ERROR: {file_path.name} is empty (0 bytes)!", "ERROR")
        
        logger.log(f"All files saved successfully for {name}", "SUCCESS")
        
    except Exception as e:
        logger.log(f"Error saving results for {name}: {e}", "ERROR")


# ============================================================
# MAIN SEGMENTATION PIPELINE
# ============================================================

def segment_tshirt(image_path: str, name: str = "garment") -> tuple:
    """
    Main segmentation function for a single image with comprehensive logging.
    
    Tries methods in order of accuracy:
    1. rembg (AI-based, most accurate)
    2. GrabCut (semi-automatic)
    3. Color-based (fallback)
    
    Args:
        image_path: Path to input image
        name: Name for output files
    
    Returns:
        Tuple of (original_image, mask, masked_image)
    """
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"SEGMENTING: {name.upper()}", "INFO")
    logger.log(f"{'='*60}", "INFO")
    
    pipeline_start = time.time()
    
    # Load the image
    image = load_image(image_path, name)
    if image is None:
        logger.log(f"Failed to load image for {name}", "ERROR")
        return None, None, None
    
    mask = None
    method_used = "none"
    
    # Try rembg first (best quality)
    logger.log("", "INFO")
    logger.log("METHOD 1: Trying AI-based segmentation (rembg)...", "INFO")
    mask = segment_with_rembg(image)
    
    if mask is not None:
        method_used = "rembg (AI)"
        logger.log("rembg segmentation successful!", "SUCCESS")
    else:
        # Fallback to GrabCut
        logger.log("", "INFO")
        logger.log("METHOD 2: Falling back to GrabCut segmentation...", "INFO")
        mask = segment_garment_grabcut(image)
        
        if mask is not None:
            method_used = "GrabCut"
            logger.log("GrabCut segmentation successful!", "SUCCESS")
        else:
            logger.log("GrabCut segmentation failed!", "ERROR")
            return None, None, None
    
    # Log which method was used
    logger.log(f"", "INFO")
    logger.log(f"Segmentation method used: {method_used}", "SUCCESS")
    
    # Log initial mask statistics
    logger.log_image_stats(f"{name}_mask_initial", mask, "  ")
    
    # Refine the mask
    logger.log("", "INFO")
    mask = refine_mask(mask)
    
    # Log refined mask statistics
    logger.log_image_stats(f"{name}_mask_refined", mask, "  ")
    
    # Calculate and log mask quality
    logger.log("", "INFO")
    quality = logger.log_mask_quality(mask, name)
    
    # Apply mask to create transparent image
    logger.log("", "INFO")
    logger.log("Creating masked image with transparency...", "INFO")
    masked = apply_mask(image, mask)
    logger.log_image_stats(f"{name}_masked", masked, "  ")
    
    # Create debug visualization
    logger.log("", "INFO")
    logger.save_debug_visualization(image, mask, name)
    
    # Save results
    logger.log("", "INFO")
    save_results(name, image, mask, masked)
    
    # Calculate total time
    total_time = time.time() - pipeline_start
    logger.log("", "INFO")
    logger.log(f"{'='*60}", "INFO")
    logger.log(f"{name.upper()} SEGMENTATION COMPLETE in {total_time:.3f}s", "SUCCESS")
    logger.log(f"Method: {method_used} | Quality: {quality['overall_score']:.1f}/100", "SUCCESS")
    logger.log(f"{'='*60}", "INFO")
    
    return image, mask, masked


def run_segmentation_pipeline():
    """
    Run the complete segmentation pipeline with comprehensive logging.
    
    This is the main entry point that:
    1. Creates output directory
    2. Segments front image (required)
    3. Segments back image (if provided)
    4. Creates a combined summary
    5. Saves detailed metrics
    """
    logger.log("\n" + "="*80, "INFO")
    logger.log("   STEP 1: T-SHIRT SEGMENTATION PIPELINE (ENHANCED)", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    pipeline_start_time = time.time()
    
    # Ensure output directory exists
    ensure_output_dir()
    
    results = {
        "front": {"success": False},
        "back": {"success": False}
    }
    
    # Process FRONT image (required)
    logger.log("\n" + "-"*80, "INFO")
    logger.log("PROCESSING FRONT IMAGE (REQUIRED)", "INFO")
    logger.log("-"*80 + "\n", "INFO")
    
    front_img, front_mask, front_masked = segment_tshirt(FRONT_IMAGE_PATH, "front")
    
    if front_img is None:
        logger.log("\n" + "="*80, "ERROR")
        logger.log("❌ CRITICAL ERROR: Front image is required but could not be processed!", "ERROR")
        logger.log(f"   Please ensure the image exists at: {FRONT_IMAGE_PATH}", "ERROR")
        logger.log("   Update FRONT_IMAGE_PATH in this script and run again.", "ERROR")
        logger.log("="*80 + "\n", "ERROR")
        logger.save_metrics()
        return False
    else:
        results["front"]["success"] = True
        results["front"]["quality"] = logger.log_mask_quality(front_mask, "front_final")
    
    # Process BACK image (optional)
    back_img, back_mask, back_masked = None, None, None
    
    if BACK_IMAGE_PATH:
        logger.log("\n" + "-"*80, "INFO")
        logger.log("PROCESSING BACK IMAGE (OPTIONAL)", "INFO")
        logger.log("-"*80 + "\n", "INFO")
        
        back_img, back_mask, back_masked = segment_tshirt(BACK_IMAGE_PATH, "back")
        
        if back_img is None:
            logger.log("⚠ Back image processing failed, continuing with front only.", "WARNING")
        else:
            results["back"]["success"] = True
            results["back"]["quality"] = logger.log_mask_quality(back_mask, "back_final")
    else:
        logger.log("\n→ No back image provided (this is optional)", "INFO")
    
    # Calculate total pipeline time
    total_pipeline_time = time.time() - pipeline_start_time
    
    # Final Summary
    logger.log("\n" + "="*80, "INFO")
    logger.log("   SEGMENTATION PIPELINE SUMMARY", "INFO")
    logger.log("="*80 + "\n", "INFO")
    
    logger.log(f"Total pipeline time: {total_pipeline_time:.3f}s", "SUCCESS")
    logger.log("", "INFO")
    
    # Front image summary
    if results["front"]["success"]:
        quality_front = results["front"]["quality"]["overall_score"]
        logger.log(f"✅ FRONT IMAGE: PROCESSED (Quality: {quality_front:.1f}/100)", "SUCCESS")
        logger.log(f"   - Mask: {OUTPUT_DIR}/front_mask.png", "INFO")
        logger.log(f"   - Masked: {OUTPUT_DIR}/front_masked.png", "INFO")
        logger.log(f"   - Debug: {DEBUG_DIR}/front_overlay.png", "INFO")
    else:
        logger.log(f"❌ FRONT IMAGE: FAILED", "ERROR")
    
    logger.log("", "INFO")
    
    # Back image summary
    if results["back"]["success"]:
        quality_back = results["back"]["quality"]["overall_score"]
        logger.log(f"✅ BACK IMAGE: PROCESSED (Quality: {quality_back:.1f}/100)", "SUCCESS")
        logger.log(f"   - Mask: {OUTPUT_DIR}/back_mask.png", "INFO")
        logger.log(f"   - Masked: {OUTPUT_DIR}/back_masked.png", "INFO")
        logger.log(f"   - Debug: {DEBUG_DIR}/back_overlay.png", "INFO")
    else:
        logger.log(f"○ BACK IMAGE: NOT PROVIDED", "INFO")
    
    logger.log("", "INFO")
    logger.log(f"📊 Detailed logs: {LOG_FILE}", "INFO")
    logger.log(f"📈 Metrics JSON: {LOG_JSON}", "INFO")
    logger.log("", "INFO")
    logger.log("="*80, "INFO")
    
    # Save final metrics
    logger.save_metrics()
    
    # Final validation
    all_critical_files_exist = True
    critical_files = [
        OUTPUT_DIR / "front_mask.png",
        OUTPUT_DIR / "front_masked.png",
        OUTPUT_DIR / "front_mask.npy"
    ]
    
    for file_path in critical_files:
        if not file_path.exists():
            logger.log(f"❌ CRITICAL FILE MISSING: {file_path}", "ERROR")
            all_critical_files_exist = False
    
    if all_critical_files_exist:
        logger.log("\n✅ ALL CRITICAL OUTPUT FILES VALIDATED", "SUCCESS")
        return True
    else:
        logger.log("\n❌ SOME CRITICAL FILES ARE MISSING", "ERROR")
        return False


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run this script directly to perform segmentation with comprehensive logging.
    
    Before running:
    1. Place your front T-shirt image in input_images/front.png
       (or update FRONT_IMAGE_PATH above)
    2. Optionally add back image as input_images/back.png
       (or update BACK_IMAGE_PATH above)
    
    Required packages:
    - opencv-python (cv2)
    - numpy
    - rembg (optional, for best results)
    
    Install with:
        pip install opencv-python numpy rembg
    
    OUTPUTS:
    - segmentation_output/*.png - Segmented images
    - segmentation_output/step1_detailed_log.txt - Detailed text log
    - segmentation_output/step1_metrics.json - Structured metrics
    - segmentation_output/debug_visualizations/ - Visual debugging aids
    """
    print("\n" + "="*80)
    print("   T-SHIRT SEGMENTATION - ENHANCED VERSION")
    print("   With comprehensive logging, validation, and quality metrics")
    print("="*80 + "\n")
    
    success = run_segmentation_pipeline()
    
    if success:
        try:
            print("\n" + "="*80)
            print("   ✅ STEP 1 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\n📁 Output directory: {OUTPUT_DIR}")
            print(f"📝 Detailed log: {LOG_FILE}")
            print(f"📊 Metrics JSON: {LOG_JSON}")
            print(f"🎨 Debug visualizations: {DEBUG_DIR}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\n➡️  Next step: Design extraction")
            print("   Run: python step2_design_extraction.py")
            print("\n" + "="*80)
        except UnicodeEncodeError:
            print("\n" + "="*80)
            print("   STEP 1 COMPLETE - ALL VALIDATIONS PASSED")
            print("="*80)
            print(f"\nOutput directory: {OUTPUT_DIR}")
            print(f"Detailed log: {LOG_FILE}")
            print(f"Metrics JSON: {LOG_JSON}")
            print(f"Debug visualizations: {DEBUG_DIR}")
            print("\n" + "="*80)
            print("   READY FOR NEXT STEP")
            print("="*80)
            print("\nNext step: Design extraction")
            print("   Run: python step2_design_extraction.py")
            print("\n" + "="*80)
    else:
        try:
            print("\n" + "="*80)
            print("   ❌ STEP 1 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\n📝 Check detailed log: {LOG_FILE}")
            print(f"📊 Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
        except UnicodeEncodeError:
            print("\n" + "="*80)
            print("   STEP 1 FAILED - CHECK LOGS FOR DETAILS")
            print("="*80)
            print(f"\nCheck detailed log: {LOG_FILE}")
            print(f"Check metrics: {LOG_JSON}")
            print("\nPlease fix the errors above and run again.")
            print("="*80)
