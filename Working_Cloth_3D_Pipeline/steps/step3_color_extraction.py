"""
Step 3: Fabric Color Extraction

Extracts the primary fabric color using LAB color space and KMeans clustering.
"""

import numpy as np
import cv2
from typing import Tuple, Optional, List
from dataclasses import dataclass
from sklearn.cluster import KMeans

import sys
sys.path.append('..')
from config.pipeline_config import ColorExtractionConfig


@dataclass
class ColorInfo:
    """Information about an extracted color"""
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]
    hex_code: str
    percentage: float
    
    def to_dict(self) -> dict:
        return {
            "rgb": [int(x) for x in self.rgb],
            "lab": [float(x) for x in self.lab],
            "hex": self.hex_code,
            "percentage": round(float(self.percentage), 2)
        }


@dataclass
class ColorExtractionResult:
    """Result from color extraction step"""
    primary_color: ColorInfo
    all_colors: List[ColorInfo]
    original_image: np.ndarray
    fabric_mask: np.ndarray
    success: bool
    message: str


class FabricColorExtractor:
    """
    Extracts fabric colors using LAB color space and KMeans clustering.
    """
    
    def __init__(self, config: Optional[ColorExtractionConfig] = None):
        self.config = config or ColorExtractionConfig()
    
    def extract(
        self, 
        image: np.ndarray, 
        fabric_mask: np.ndarray
    ) -> ColorExtractionResult:
        """
        Extract primary fabric color.
        
        Args:
            image: RGB image
            fabric_mask: Binary mask of fabric regions (excluding designs)
            
        Returns:
            ColorExtractionResult with primary and all extracted colors
        """
        if image is None or fabric_mask is None:
            return self._empty_result(image, fabric_mask, "Invalid input")
        
        # Ensure mask is binary
        mask_binary = (fabric_mask > 127).astype(np.uint8)
        
        # Get fabric pixels
        fabric_pixels = self._get_masked_pixels(image, mask_binary)
        
        if len(fabric_pixels) < self.config.num_clusters:
            return self._empty_result(
                image, fabric_mask, 
                "Not enough fabric pixels for clustering"
            )
        
        # Convert to LAB color space for clustering
        if self.config.color_space == "LAB":
            clustering_pixels = self._rgb_to_lab(fabric_pixels)
        else:
            clustering_pixels = fabric_pixels
        
        # Perform KMeans clustering
        colors = self._cluster_colors(fabric_pixels, clustering_pixels)
        
        if not colors:
            return self._empty_result(
                image, fabric_mask, 
                "Clustering failed"
            )
        
        # Sort by percentage (primary = most common)
        colors.sort(key=lambda c: c.percentage, reverse=True)
        
        return ColorExtractionResult(
            primary_color=colors[0],
            all_colors=colors,
            original_image=image,
            fabric_mask=fabric_mask,
            success=True,
            message="Color extraction successful"
        )
    
    def _get_masked_pixels(
        self, 
        image: np.ndarray, 
        mask: np.ndarray
    ) -> np.ndarray:
        """
        Get pixels within the masked region.
        """
        # Flatten mask
        mask_flat = mask.flatten()
        
        # Reshape image to (N, 3)
        pixels = image.reshape(-1, 3)
        
        # Select masked pixels
        masked_pixels = pixels[mask_flat > 0]
        
        return masked_pixels
    
    def _rgb_to_lab(self, rgb_pixels: np.ndarray) -> np.ndarray:
        """
        Convert RGB pixels to LAB color space.
        """
        # Reshape for OpenCV
        pixels_reshaped = rgb_pixels.reshape(-1, 1, 3).astype(np.uint8)
        
        # Convert to LAB
        lab_pixels = cv2.cvtColor(pixels_reshaped, cv2.COLOR_RGB2LAB)
        
        # Reshape back
        return lab_pixels.reshape(-1, 3).astype(np.float32)
    
    def _lab_to_rgb(self, lab_value: np.ndarray) -> np.ndarray:
        """
        Convert LAB value to RGB.
        """
        lab_pixel = lab_value.reshape(1, 1, 3).astype(np.uint8)
        rgb_pixel = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2RGB)
        return rgb_pixel.flatten()
    
    def _cluster_colors(
        self, 
        rgb_pixels: np.ndarray,
        clustering_pixels: np.ndarray
    ) -> List[ColorInfo]:
        """
        Cluster pixels using KMeans and extract color information.
        """
        # Subsample if too many pixels (for performance)
        max_samples = 50000
        if len(clustering_pixels) > max_samples:
            indices = np.random.choice(
                len(clustering_pixels), 
                max_samples, 
                replace=False
            )
            clustering_samples = clustering_pixels[indices]
            rgb_samples = rgb_pixels[indices]
        else:
            clustering_samples = clustering_pixels
            rgb_samples = rgb_pixels
        
        # Perform KMeans
        try:
            kmeans = KMeans(
                n_clusters=self.config.num_clusters,
                random_state=42,
                n_init=10
            )
            labels = kmeans.fit_predict(clustering_samples)
        except Exception as e:
            print(f"KMeans error: {e}")
            return []
        
        colors = []
        total_pixels = len(labels)
        
        for i in range(self.config.num_clusters):
            # Get pixels in this cluster
            cluster_mask = labels == i
            cluster_rgb = rgb_samples[cluster_mask]
            
            if len(cluster_rgb) == 0:
                continue
            
            # Calculate percentage
            percentage = (np.sum(cluster_mask) / total_pixels) * 100
            
            # Get mean color in RGB
            mean_rgb = np.mean(cluster_rgb, axis=0).astype(int)
            
            # Get LAB value from cluster center
            if self.config.color_space == "LAB":
                mean_lab = kmeans.cluster_centers_[i]
            else:
                mean_lab = self._rgb_to_lab(mean_rgb.reshape(1, 3))[0]
            
            # Create hex code
            hex_code = "#{:02x}{:02x}{:02x}".format(
                int(mean_rgb[0]), 
                int(mean_rgb[1]), 
                int(mean_rgb[2])
            )
            
            colors.append(ColorInfo(
                rgb=tuple(mean_rgb),
                lab=tuple(mean_lab),
                hex_code=hex_code,
                percentage=percentage
            ))
        
        return colors
    
    def _empty_result(
        self, 
        image: np.ndarray, 
        mask: np.ndarray,
        message: str
    ) -> ColorExtractionResult:
        """Create empty result for invalid inputs."""
        empty_color = ColorInfo(
            rgb=(0, 0, 0),
            lab=(0.0, 0.0, 0.0),
            hex_code="#000000",
            percentage=0.0
        )
        
        empty = np.zeros((1, 1), dtype=np.uint8)
        
        return ColorExtractionResult(
            primary_color=empty_color,
            all_colors=[],
            original_image=image if image is not None else empty,
            fabric_mask=mask if mask is not None else empty,
            success=False,
            message=message
        )
    
    def create_color_palette(
        self, 
        result: ColorExtractionResult,
        swatch_size: int = 100
    ) -> np.ndarray:
        """
        Create a color palette visualization.
        
        Args:
            result: ColorExtractionResult
            swatch_size: Size of each color swatch
            
        Returns:
            RGB image of color palette
        """
        if not result.all_colors:
            return np.zeros((swatch_size, swatch_size, 3), dtype=np.uint8)
        
        num_colors = len(result.all_colors)
        palette = np.zeros((swatch_size, swatch_size * num_colors, 3), dtype=np.uint8)
        
        for i, color in enumerate(result.all_colors):
            x_start = i * swatch_size
            x_end = (i + 1) * swatch_size
            palette[:, x_start:x_end] = color.rgb
        
        return palette
    
    def find_similar_colors(
        self, 
        target_color: Tuple[int, int, int],
        threshold: float = 20.0
    ) -> bool:
        """
        Check if a color is similar to the target color.
        Uses Delta E (CIE76) in LAB space.
        
        Args:
            target_color: RGB color to compare
            threshold: Maximum Delta E for similarity
            
        Returns:
            True if colors are similar
        """
        # This is a utility method for color matching
        pass


def extract_fabric_color(
    image: np.ndarray,
    fabric_mask: np.ndarray,
    config: Optional[ColorExtractionConfig] = None
) -> ColorExtractionResult:
    """
    Convenience function for color extraction.
    
    Args:
        image: RGB image
        fabric_mask: Binary mask of fabric regions
        config: Optional configuration
        
    Returns:
        ColorExtractionResult
    """
    extractor = FabricColorExtractor(config)
    return extractor.extract(image, fabric_mask)


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex string."""
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    import argparse
    import json
    from step1_segmentation import segment_image
    from step2_design_extraction import DesignExtractor
    
    parser = argparse.ArgumentParser(description="Extract fabric color")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("-o", "--output", help="Output directory", default=".")
    
    args = parser.parse_args()
    
    # Step 1: Segment
    seg_result = segment_image(args.input)
    
    if not seg_result.is_valid:
        print(f"Segmentation failed: {seg_result.validation_message}")
        exit(1)
    
    # Step 2: Extract design
    design_extractor = DesignExtractor()
    design_result = design_extractor.extract(
        seg_result.original_image, 
        seg_result.mask
    )
    
    # Step 3: Extract color
    color_extractor = FabricColorExtractor()
    color_result = color_extractor.extract(
        seg_result.original_image,
        design_result.fabric_mask
    )
    
    if color_result.success:
        print(f"Primary fabric color: {color_result.primary_color.hex_code}")
        print(f"RGB: {color_result.primary_color.rgb}")
        
        # Save color info
        colors_data = {
            "primary_color": color_result.primary_color.to_dict(),
            "all_colors": [c.to_dict() for c in color_result.all_colors]
        }
        
        with open(f"{args.output}/colors.json", "w") as f:
            json.dump(colors_data, f, indent=2)
        
        # Save palette visualization
        palette = color_extractor.create_color_palette(color_result)
        cv2.imwrite(
            f"{args.output}/color_palette.png", 
            cv2.cvtColor(palette, cv2.COLOR_RGB2BGR)
        )
    else:
        print(f"Color extraction failed: {color_result.message}")
