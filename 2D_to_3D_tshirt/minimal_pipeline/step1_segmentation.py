"""
STEP 1: T-Shirt Segmentation
============================
This script segments the T-shirt from the background.

What it does:
- Loads front image (required) and back image (optional)
- Removes background using AI-based segmentation
- Saves binary masks and masked images

The mask is a black-and-white image where:
- White (255) = T-shirt pixels
- Black (0) = Background pixels
"""

import cv2
import numpy as np
from pathlib import Path
import sys

# ============================================================
# CONFIGURATION - Set your image paths here
# ============================================================

# Front image is REQUIRED
FRONT_IMAGE_PATH = "input_images/front.png"  # Change this to your front image

# Back image is OPTIONAL (set to None if not available)
BACK_IMAGE_PATH = None  # Or "input_images/back.png" if you have one

# Output directory
OUTPUT_DIR = Path("segmentation_output")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def ensure_output_dir():
    """
    Create output directory if it doesn't exist.
    This is where we'll save all our segmentation results.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory ready: {OUTPUT_DIR}")


def load_image(image_path: str, name: str = "image") -> np.ndarray:
    """
    Load an image from disk.
    
    Args:
        image_path: Path to the image file
        name: Human-readable name for error messages
    
    Returns:
        Image as numpy array in BGR format (OpenCV default)
    
    Why BGR? OpenCV loads images in Blue-Green-Red order by default.
    We'll convert to RGB when needed for display or saving.
    """
    if image_path is None:
        return None
    
    path = Path(image_path)
    if not path.exists():
        print(f"⚠ {name} not found at: {path}")
        return None
    
    # cv2.imread loads the image as a numpy array
    # The image is in BGR format (Blue, Green, Red channels)
    image = cv2.imread(str(path))
    
    if image is None:
        print(f"✗ Failed to load {name}: {path}")
        return None
    
    height, width = image.shape[:2]
    print(f"✓ Loaded {name}: {path} ({width}x{height} pixels)")
    return image


def segment_garment_grabcut(image: np.ndarray) -> np.ndarray:
    """
    Segment the garment using GrabCut algorithm.
    
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
    height, width = image.shape[:2]
    
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
    Segment using rembg library (AI-based background removal).
    
    rembg uses a neural network (U2-Net) trained specifically for
    removing backgrounds. It's very accurate for clothing.
    
    Args:
        image: Input BGR image
    
    Returns:
        Binary mask where 255 = garment, 0 = background
    """
    try:
        from rembg import remove
        
        # Convert BGR to RGB (rembg expects RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Remove background - returns RGBA image
        # The alpha channel IS the mask we want
        result = remove(rgb_image)
        
        # Extract alpha channel as mask
        # Alpha = 255 means fully opaque (foreground)
        # Alpha = 0 means fully transparent (background)
        if result.shape[2] == 4:  # RGBA
            mask = result[:, :, 3]  # Alpha channel
        else:
            # Fallback: if no alpha, assume non-black is foreground
            gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
            mask = np.where(gray > 10, 255, 0).astype(np.uint8)
        
        return mask
        
    except ImportError:
        print("⚠ rembg not installed. Run: pip install rembg")
        print("  Falling back to GrabCut method...")
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
    Refine the segmentation mask.
    
    This cleans up rough edges and fills holes.
    
    Args:
        mask: Initial binary mask
    
    Returns:
        Refined binary mask
    """
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
    
    # Smooth the edges with Gaussian blur then threshold
    smoothed = cv2.GaussianBlur(filled, (5, 5), 0)
    _, refined = cv2.threshold(smoothed, 127, 255, cv2.THRESH_BINARY)
    
    return refined


def save_results(name: str, image: np.ndarray, mask: np.ndarray, masked: np.ndarray):
    """
    Save segmentation results to output directory.
    
    Args:
        name: Base name for files (e.g., "front", "back")
        image: Original image
        mask: Binary mask
        masked: Image with background removed
    """
    # Save original (for reference)
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_original.png"), image)
    print(f"  ✓ Saved {name}_original.png")
    
    # Save binary mask (useful for later steps)
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_mask.png"), mask)
    print(f"  ✓ Saved {name}_mask.png")
    
    # Save masked image (T-shirt only, transparent background)
    cv2.imwrite(str(OUTPUT_DIR / f"{name}_masked.png"), masked)
    print(f"  ✓ Saved {name}_masked.png")
    
    # Also save mask as numpy array for programmatic use
    np.save(str(OUTPUT_DIR / f"{name}_mask.npy"), mask)
    print(f"  ✓ Saved {name}_mask.npy")


# ============================================================
# MAIN SEGMENTATION PIPELINE
# ============================================================

def segment_tshirt(image_path: str, name: str = "garment") -> tuple:
    """
    Main segmentation function for a single image.
    
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
    print(f"\n{'='*50}")
    print(f"Segmenting: {name}")
    print('='*50)
    
    # Load the image
    image = load_image(image_path, name)
    if image is None:
        return None, None, None
    
    # Try rembg first (best quality)
    print("\n→ Attempting AI-based segmentation (rembg)...")
    mask = segment_with_rembg(image)
    
    if mask is None:
        # Fallback to GrabCut
        print("\n→ Using GrabCut segmentation...")
        mask = segment_garment_grabcut(image)
    
    # Refine the mask
    print("→ Refining mask edges...")
    mask = refine_mask(mask)
    
    # Count foreground pixels
    fg_pixels = np.sum(mask > 0)
    total_pixels = mask.shape[0] * mask.shape[1]
    fg_percent = (fg_pixels / total_pixels) * 100
    print(f"✓ Segmentation complete: {fg_percent:.1f}% of image is garment")
    
    # Apply mask to create transparent image
    masked = apply_mask(image, mask)
    
    # Save results
    print("\n→ Saving results...")
    save_results(name, image, mask, masked)
    
    return image, mask, masked


def run_segmentation_pipeline():
    """
    Run the complete segmentation pipeline.
    
    This is the main entry point that:
    1. Creates output directory
    2. Segments front image (required)
    3. Segments back image (if provided)
    4. Creates a combined summary
    """
    print("\n" + "="*60)
    print("   STEP 1: T-SHIRT SEGMENTATION")
    print("="*60)
    
    # Ensure output directory exists
    ensure_output_dir()
    
    # Process FRONT image (required)
    print("\n" + "-"*40)
    print("Processing FRONT image (required)")
    print("-"*40)
    
    front_img, front_mask, front_masked = segment_tshirt(FRONT_IMAGE_PATH, "front")
    
    if front_img is None:
        print("\n✗ ERROR: Front image is required but could not be loaded!")
        print(f"  Please ensure the image exists at: {FRONT_IMAGE_PATH}")
        print("  Update FRONT_IMAGE_PATH in this script and run again.")
        return False
    
    # Process BACK image (optional)
    back_img, back_mask, back_masked = None, None, None
    
    if BACK_IMAGE_PATH:
        print("\n" + "-"*40)
        print("Processing BACK image (optional)")
        print("-"*40)
        back_img, back_mask, back_masked = segment_tshirt(BACK_IMAGE_PATH, "back")
        
        if back_img is None:
            print("⚠ Back image not available, continuing with front only.")
    else:
        print("\n→ No back image provided (this is optional)")
    
    # Summary
    print("\n" + "="*60)
    print("   SEGMENTATION SUMMARY")
    print("="*60)
    print(f"\n✓ Front image: PROCESSED")
    print(f"  - Mask: {OUTPUT_DIR}/front_mask.png")
    print(f"  - Masked: {OUTPUT_DIR}/front_masked.png")
    
    if back_mask is not None:
        print(f"\n✓ Back image: PROCESSED")
        print(f"  - Mask: {OUTPUT_DIR}/back_mask.png")
        print(f"  - Masked: {OUTPUT_DIR}/back_masked.png")
    else:
        print(f"\n○ Back image: NOT PROVIDED")
    
    print("\n" + "="*60)
    
    return True


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    """
    Run this script directly to perform segmentation.
    
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
    """
    success = run_segmentation_pipeline()
    
    if success:
        print("\n" + "="*60)
        print("   STEP 1 COMPLETE — GREEN SIGNAL REQUIRED ✅")
        print("="*60)
        print("\nNext step: Design extraction")
        print("Waiting for your GREEN SIGNAL to proceed...")
    else:
        print("\n✗ Segmentation failed. Please fix the errors above.")
