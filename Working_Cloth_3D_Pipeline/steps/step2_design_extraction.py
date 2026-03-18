"""
Step 2: Design/Print Extraction

Separates fabric regions from design/print regions using 
texture variance analysis and edge detection.
"""

import numpy as np
import cv2
from typing import Tuple, Optional
from dataclasses import dataclass
from scipy import ndimage

import sys
sys.path.append('..')
from config.pipeline_config import DesignExtractionConfig


@dataclass
class DesignExtractionResult:
    """Result from design extraction step"""
    fabric_mask: np.ndarray
    design_mask: np.ndarray
    original_image: np.ndarray
    garment_mask: np.ndarray
    has_design: bool
    design_coverage_percent: float


class DesignExtractor:
    """
    Extracts design/print regions from fabric using:
    - Texture variance analysis
    - Edge detection (Canny)
    - Color uniformity analysis
    """
    
    def __init__(self, config: Optional[DesignExtractionConfig] = None):
        self.config = config or DesignExtractionConfig()
    
    def extract(
        self, 
        image: np.ndarray, 
        garment_mask: np.ndarray
    ) -> DesignExtractionResult:
        """
        Extract design regions from the garment.
        
        Args:
            image: RGB image
            garment_mask: Binary mask from Step 1
            
        Returns:
            DesignExtractionResult with fabric and design masks
        """
        if image is None or garment_mask is None:
            return self._empty_result(image, garment_mask)
        
        # Ensure mask is binary
        mask_binary = (garment_mask > 127).astype(np.uint8) * 255
        
        # Apply mask to image
        masked_image = cv2.bitwise_and(image, image, mask=mask_binary)
        
        # Compute texture variance map
        variance_map = self._compute_texture_variance(masked_image)
        
        # Compute edge density map
        edge_map = self._compute_edge_density(masked_image)
        
        # Combine features
        combined_features = self._combine_features(variance_map, edge_map)
        
        # Threshold to get design regions
        design_mask = self._threshold_design_regions(
            combined_features, mask_binary
        )
        
        # Fabric mask is garment minus design
        fabric_mask = cv2.bitwise_and(
            mask_binary, 
            cv2.bitwise_not(design_mask)
        )
        
        # Calculate design coverage
        garment_pixels = np.sum(mask_binary > 0)
        design_pixels = np.sum(design_mask > 0)
        design_coverage = (design_pixels / garment_pixels * 100) if garment_pixels > 0 else 0
        
        return DesignExtractionResult(
            fabric_mask=fabric_mask,
            design_mask=design_mask,
            original_image=image,
            garment_mask=garment_mask,
            has_design=design_coverage > 1.0,  # More than 1% design
            design_coverage_percent=design_coverage
        )
    
    def _compute_texture_variance(
        self, 
        image: np.ndarray, 
        window_size: int = 15
    ) -> np.ndarray:
        """
        Compute local texture variance using sliding window.
        Higher variance indicates textured/patterned regions.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
        
        # Compute local mean
        kernel = np.ones((window_size, window_size), dtype=np.float32)
        kernel /= kernel.sum()
        
        local_mean = cv2.filter2D(gray, -1, kernel)
        
        # Compute local variance
        local_sq_mean = cv2.filter2D(gray ** 2, -1, kernel)
        local_variance = local_sq_mean - (local_mean ** 2)
        
        # Normalize
        local_variance = np.clip(local_variance, 0, None)
        if local_variance.max() > 0:
            local_variance = local_variance / local_variance.max()
        
        return local_variance
    
    def _compute_edge_density(
        self, 
        image: np.ndarray, 
        window_size: int = 21
    ) -> np.ndarray:
        """
        Compute local edge density using Canny edge detection.
        Higher density indicates detailed/patterned regions.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detect edges
        edges = cv2.Canny(
            blurred,
            self.config.canny_low_threshold,
            self.config.canny_high_threshold
        )
        
        # Compute local edge density
        kernel = np.ones((window_size, window_size), dtype=np.float32)
        edge_density = cv2.filter2D(
            edges.astype(np.float32), -1, kernel
        )
        
        # Normalize
        if edge_density.max() > 0:
            edge_density = edge_density / edge_density.max()
        
        return edge_density
    
    def _compute_color_variance(
        self, 
        image: np.ndarray, 
        window_size: int = 15
    ) -> np.ndarray:
        """
        Compute local color variance in LAB space.
        """
        # Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB).astype(np.float32)
        
        kernel = np.ones((window_size, window_size), dtype=np.float32)
        kernel /= kernel.sum()
        
        color_variance = np.zeros(image.shape[:2], dtype=np.float32)
        
        # Compute variance for each channel
        for i in range(3):
            channel = lab[:, :, i]
            local_mean = cv2.filter2D(channel, -1, kernel)
            local_sq_mean = cv2.filter2D(channel ** 2, -1, kernel)
            channel_var = local_sq_mean - (local_mean ** 2)
            color_variance += np.clip(channel_var, 0, None)
        
        # Normalize
        if color_variance.max() > 0:
            color_variance = color_variance / color_variance.max()
        
        return color_variance
    
    def _combine_features(
        self, 
        variance_map: np.ndarray, 
        edge_map: np.ndarray,
        variance_weight: float = 0.6,
        edge_weight: float = 0.4
    ) -> np.ndarray:
        """
        Combine texture variance and edge density features.
        """
        combined = (
            variance_weight * variance_map + 
            edge_weight * edge_map
        )
        
        # Normalize
        if combined.max() > 0:
            combined = combined / combined.max()
        
        return combined
    
    def _threshold_design_regions(
        self, 
        feature_map: np.ndarray, 
        garment_mask: np.ndarray
    ) -> np.ndarray:
        """
        Threshold feature map to extract design regions.
        """
        # Apply mask
        masked_features = feature_map.copy()
        masked_features[garment_mask == 0] = 0
        
        # Get valid pixel values within garment
        valid_values = masked_features[garment_mask > 0]
        
        if len(valid_values) == 0:
            return np.zeros_like(garment_mask)
        
        # Use adaptive threshold based on feature distribution
        threshold = np.percentile(valid_values, 70)
        threshold = max(threshold, self.config.texture_variance_threshold)
        
        # Create design mask
        design_mask = (masked_features > threshold).astype(np.uint8) * 255
        
        # Clean up with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        design_mask = cv2.morphologyEx(design_mask, cv2.MORPH_OPEN, kernel)
        design_mask = cv2.morphologyEx(design_mask, cv2.MORPH_CLOSE, kernel)
        
        # Ensure design is within garment mask
        design_mask = cv2.bitwise_and(design_mask, garment_mask)
        
        return design_mask
    
    def _empty_result(
        self, 
        image: np.ndarray, 
        mask: np.ndarray
    ) -> DesignExtractionResult:
        """Create empty result for invalid inputs."""
        empty = np.zeros((1, 1), dtype=np.uint8)
        return DesignExtractionResult(
            fabric_mask=empty,
            design_mask=empty,
            original_image=image if image is not None else empty,
            garment_mask=mask if mask is not None else empty,
            has_design=False,
            design_coverage_percent=0.0
        )
    
    def visualize_extraction(
        self, 
        result: DesignExtractionResult
    ) -> np.ndarray:
        """
        Create visualization of the extraction result.
        
        Returns:
            RGB image with fabric (green) and design (red) overlay
        """
        vis = result.original_image.copy()
        
        # Create colored overlays
        fabric_overlay = np.zeros_like(vis)
        fabric_overlay[:, :, 1] = result.fabric_mask  # Green for fabric
        
        design_overlay = np.zeros_like(vis)
        design_overlay[:, :, 0] = result.design_mask  # Red for design
        
        # Blend overlays
        alpha = 0.3
        vis = cv2.addWeighted(vis, 1 - alpha, fabric_overlay, alpha, 0)
        vis = cv2.addWeighted(vis, 1, design_overlay, alpha, 0)
        
        return vis


def extract_design(
    image: np.ndarray,
    garment_mask: np.ndarray,
    config: Optional[DesignExtractionConfig] = None
) -> DesignExtractionResult:
    """
    Convenience function for design extraction.
    
    Args:
        image: RGB image
        garment_mask: Binary mask from segmentation
        config: Optional configuration
        
    Returns:
        DesignExtractionResult
    """
    extractor = DesignExtractor(config)
    return extractor.extract(image, garment_mask)


if __name__ == "__main__":
    import argparse
    from step1_segmentation import segment_image
    
    parser = argparse.ArgumentParser(description="Extract design from garment")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("-o", "--output", help="Output directory", default=".")
    
    args = parser.parse_args()
    
    # First segment
    seg_result = segment_image(args.input)
    
    if not seg_result.is_valid:
        print(f"Segmentation failed: {seg_result.validation_message}")
        exit(1)
    
    # Extract design
    extractor = DesignExtractor()
    result = extractor.extract(seg_result.original_image, seg_result.mask)
    
    print(f"Has design: {result.has_design}")
    print(f"Design coverage: {result.design_coverage_percent:.1f}%")
    
    # Save results
    cv2.imwrite(f"{args.output}/fabric_mask.png", result.fabric_mask)
    cv2.imwrite(f"{args.output}/design_mask.png", result.design_mask)
    
    # Save visualization
    vis = extractor.visualize_extraction(result)
    cv2.imwrite(f"{args.output}/design_visualization.png", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
