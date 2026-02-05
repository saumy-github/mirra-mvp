"""
Step 1: Image Segmentation

Segments garment from background image, producing a binary mask.
Includes morphological cleanup and sanity checks.
"""

import numpy as np
import cv2
from typing import Tuple, Optional
from dataclasses import dataclass

import sys
sys.path.append('..')
from config.pipeline_config import SegmentationConfig


@dataclass
class SegmentationResult:
    """Result from segmentation step"""
    mask: np.ndarray
    original_image: np.ndarray
    area_percent: float
    is_valid: bool
    validation_message: str


class GarmentSegmentor:
    """
    Garment Segmentation using multiple methods:
    - GrabCut algorithm
    - Color-based thresholding
    - Deep learning (optional, if model available)
    """
    
    def __init__(self, config: Optional[SegmentationConfig] = None):
        self.config = config or SegmentationConfig()
        
    def segment(self, image: np.ndarray) -> SegmentationResult:
        """
        Main segmentation method.
        
        Args:
            image: RGB image as numpy array
            
        Returns:
            SegmentationResult with binary mask and metadata
        """
        if image is None or image.size == 0:
            return SegmentationResult(
                mask=np.array([]),
                original_image=image,
                area_percent=0.0,
                is_valid=False,
                validation_message="Invalid input image"
            )
        
        # Try GrabCut first
        mask = self._grabcut_segment(image)
        
        # Apply morphological cleanup if enabled
        if self.config.morphology_cleanup:
            mask = self._morphology_cleanup(mask)
        
        # Keep largest connected component if required
        if self.config.connected_component_required:
            mask = self._keep_largest_component(mask)
        
        # Validate result
        is_valid, area_percent, message = self._validate_mask(mask, image.shape)
        
        return SegmentationResult(
            mask=mask,
            original_image=image,
            area_percent=area_percent,
            is_valid=is_valid,
            validation_message=message
        )
    
    def _grabcut_segment(self, image: np.ndarray) -> np.ndarray:
        """
        Segment using GrabCut algorithm.
        """
        h, w = image.shape[:2]
        
        # Initialize mask
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Create rectangle for GrabCut (assume garment is roughly centered)
        margin_x = int(w * 0.05)
        margin_y = int(h * 0.02)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        # Create background and foreground models
        bgd_model = np.zeros((1, 65), dtype=np.float64)
        fgd_model = np.zeros((1, 65), dtype=np.float64)
        
        try:
            # Run GrabCut
            cv2.grabCut(
                image, mask, rect,
                bgd_model, fgd_model,
                iterCount=5,
                mode=cv2.GC_INIT_WITH_RECT
            )
            
            # Convert mask to binary (foreground = 1 or 3)
            binary_mask = np.where(
                (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
                255, 0
            ).astype(np.uint8)
            
        except cv2.error:
            # Fallback to simple thresholding
            binary_mask = self._threshold_segment(image)
        
        return binary_mask
    
    def _threshold_segment(self, image: np.ndarray) -> np.ndarray:
        """
        Fallback segmentation using color thresholding.
        Assumes white/light background.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Otsu's thresholding
        _, mask = cv2.threshold(
            blurred, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        
        return mask
    
    def _morphology_cleanup(self, mask: np.ndarray) -> np.ndarray:
        """
        Clean up mask using morphological operations.
        """
        # Define kernels
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
        # Remove small noise (opening)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=2)
        
        # Fill small holes (closing)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_medium, iterations=2)
        
        # Dilate slightly to smooth edges
        cleaned = cv2.dilate(cleaned, kernel_small, iterations=1)
        cleaned = cv2.erode(cleaned, kernel_small, iterations=1)
        
        return cleaned
    
    def _keep_largest_component(self, mask: np.ndarray) -> np.ndarray:
        """
        Keep only the largest connected component in the mask.
        """
        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        
        if num_labels <= 1:
            return mask
        
        # Find largest component (excluding background at index 0)
        largest_idx = 1
        largest_area = 0
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > largest_area:
                largest_area = area
                largest_idx = i
        
        # Create mask with only largest component
        result = np.zeros_like(mask)
        result[labels == largest_idx] = 255
        
        return result
    
    def _validate_mask(
        self, mask: np.ndarray, image_shape: Tuple[int, ...]
    ) -> Tuple[bool, float, str]:
        """
        Validate the segmentation mask against constraints.
        
        Returns:
            Tuple of (is_valid, area_percent, validation_message)
        """
        total_pixels = image_shape[0] * image_shape[1]
        mask_pixels = np.sum(mask > 0)
        area_percent = (mask_pixels / total_pixels) * 100
        
        if area_percent < self.config.min_area_percent:
            return (
                False,
                area_percent,
                f"Mask area ({area_percent:.1f}%) below minimum ({self.config.min_area_percent}%)"
            )
        
        if area_percent > self.config.max_area_percent:
            return (
                False,
                area_percent,
                f"Mask area ({area_percent:.1f}%) exceeds maximum ({self.config.max_area_percent}%)"
            )
        
        # Check if mask has at least one connected component
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(mask)
        if num_labels <= 1:
            return (False, area_percent, "No valid garment region found")
        
        return (True, area_percent, "Segmentation successful")
    
    def refine_with_edges(
        self, 
        image: np.ndarray, 
        initial_mask: np.ndarray
    ) -> np.ndarray:
        """
        Refine segmentation mask using edge detection.
        """
        # Detect edges in original image
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate edges slightly
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours from initial mask
        contours, _ = cv2.findContours(
            initial_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return initial_mask
        
        # Refine largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Create refined mask
        refined_mask = np.zeros_like(initial_mask)
        cv2.drawContours(refined_mask, [largest_contour], -1, 255, -1)
        
        return refined_mask


def segment_image(
    image_path: str, 
    config: Optional[SegmentationConfig] = None
) -> SegmentationResult:
    """
    Convenience function to segment an image from file path.
    
    Args:
        image_path: Path to the input image
        config: Optional segmentation configuration
        
    Returns:
        SegmentationResult with mask and metadata
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return SegmentationResult(
            mask=np.array([]),
            original_image=np.array([]),
            area_percent=0.0,
            is_valid=False,
            validation_message=f"Could not load image: {image_path}"
        )
    
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Segment
    segmentor = GarmentSegmentor(config)
    return segmentor.segment(image_rgb)


def save_mask(mask: np.ndarray, output_path: str) -> bool:
    """
    Save segmentation mask to file.
    """
    try:
        cv2.imwrite(output_path, mask)
        return True
    except Exception as e:
        print(f"Error saving mask: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Segment garment from image")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("-o", "--output", help="Output mask path", default="mask.png")
    
    args = parser.parse_args()
    
    result = segment_image(args.input)
    
    if result.is_valid:
        save_mask(result.mask, args.output)
        print(f"Segmentation successful. Area: {result.area_percent:.1f}%")
    else:
        print(f"Segmentation failed: {result.validation_message}")
