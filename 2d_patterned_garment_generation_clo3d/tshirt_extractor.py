"""
T-Shirt Appearance Extraction for CLO3D
=========================================

Four-stage pipeline that extracts appearance data from T-shirt photos
and produces CLO3D-compatible texture assets.

Stages:
  1. Segmentation       — RMBG-1.4 (or SAM fallback) isolates the garment
  2. View Selection     — CLIP zero-shot classifies front / back / side / irrelevant
  3. Colour Extraction  — K-Means in LAB colour space → HEX + palette
  4. Design Extraction  — Edge detection + contour analysis → graphic diffuse map

Each run auto-creates a new numbered folder  ext001 / ext002 / …
inside  extraction_output/.
"""

import os
import sys
import json
import math
import time
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Optional, Any

import numpy as np
from PIL import Image
import cv2

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. Colour extraction will be limited.")

try:
    import torch
    from transformers import AutoModelForImageSegmentation
    HAS_RMBG = True
except ImportError:
    HAS_RMBG = False
    print("Warning: torch/transformers not installed. RMBG segmentation unavailable.")

# Ensure this folder is importable
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# ═══════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ColorInfo:
    """Information about a single extracted colour."""
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]
    hex_code: str
    percentage: float

    def to_dict(self) -> dict:
        return {
            "rgb": list(self.rgb),
            "lab": [round(v, 2) for v in self.lab],
            "hex": self.hex_code,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class SegmentationResult:
    """Result from Stage 1: Segmentation."""
    rgba_image: Optional[np.ndarray] = None  # H×W×4  RGBA
    mask: Optional[np.ndarray] = None        # H×W    uint8 (0/255)
    area_percent: float = 0.0
    is_valid: bool = False
    method: str = ""
    message: str = ""


@dataclass
class ViewLabel:
    """View classification for one image."""
    filename: str
    filepath: str
    label: str       # front_view | back_view | side_view | irrelevant
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ColourResult:
    """Result from Stage 3: Colour Extraction."""
    base_colour_hex: str = "#000000"
    palette: List[ColorInfo] = field(default_factory=list)
    success: bool = False
    message: str = ""


@dataclass
class DesignResult:
    """Result from Stage 4: Design Extraction."""
    graphic_image: Optional[np.ndarray] = None   # RGBA
    has_design: bool = False
    design_coverage_percent: float = 0.0
    message: str = ""


@dataclass
class ExtractionResult:
    """Full pipeline result."""
    run_dir: str = ""
    segmentation: Optional[SegmentationResult] = None
    views: List[ViewLabel] = field(default_factory=list)
    colour: Optional[ColourResult] = None
    design: Optional[DesignResult] = None
    base_garment_path: str = ""
    graphic_diffuse_path: str = ""
    colors_json_path: str = ""
    metadata_path: str = ""


# ═══════════════════════════════════════════════════════════════
#  STAGE 1 — SEGMENTATION
# ═══════════════════════════════════════════════════════════════

class GarmentSegmentor:
    """
    Isolates the T-shirt from background (and human body).

    Primary method : RMBG-1.4 (briaai/RMBG-1.4)
    Fallback       : GrabCut + morphological cleanup
    """

    def __init__(self):
        self._rmbg_model = None

    # ── RMBG-1.4 ─────────────────────────────────────────────
    def _load_rmbg(self):
        if self._rmbg_model is not None:
            return
        if not HAS_RMBG:
            raise RuntimeError("RMBG-1.4 requires torch + transformers")
        print("    Loading RMBG-1.4 model …")
        self._rmbg_model = AutoModelForImageSegmentation.from_pretrained(
            "briaai/RMBG-1.4", trust_remote_code=True
        )
        self._rmbg_model.eval()
        print("    ✓ RMBG-1.4 loaded")

    def segment_rmbg(self, image_path: str) -> SegmentationResult:
        """Segment using RMBG-1.4."""
        try:
            self._load_rmbg()
        except RuntimeError as e:
            return SegmentationResult(
                is_valid=False, method="rmbg-1.4",
                message=f"Model load failed: {e}",
            )

        from torchvision import transforms as T

        pil_img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = pil_img.size

        # Preprocess
        transform = T.Compose([
            T.Resize((1024, 1024)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        input_tensor = transform(pil_img).unsqueeze(0)

        with torch.no_grad():
            output = self._rmbg_model(input_tensor)

        # Post-process: unwrap → threshold
        # RMBG-1.4 returns a list of tensors AND already applies sigmoid internally.
        # Do NOT apply sigmoid again — just unwrap and convert to numpy.
        pred = output
        while isinstance(pred, (list, tuple)):
            pred = pred[0]
        pred = pred.squeeze()
        if pred.dim() == 3:
            pred = pred[0]
        # Values are already in [0, 1] — just move to CPU numpy
        pred = pred.cpu().float().numpy()

        # Resize mask back to original
        mask_resized = cv2.resize(pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel, iterations=2)
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Keep largest connected component
        mask_binary = self._keep_largest_component(mask_binary)

        # Compose RGBA
        orig_np = np.array(pil_img)
        rgba = np.dstack([orig_np, mask_binary])

        # Validate mask area
        area_pct = float(np.sum(mask_binary > 0) / mask_binary.size * 100)
        is_valid = 5.0 <= area_pct <= 95.0

        return SegmentationResult(
            rgba_image=rgba,
            mask=mask_binary,
            area_percent=area_pct,
            is_valid=is_valid,
            method="rmbg-1.4",
            message="OK" if is_valid else f"Area {area_pct:.1f}% outside 5-95% range",
        )

    # ── GrabCut fallback ─────────────────────────────────────
    def segment_grabcut(self, image_path: str) -> SegmentationResult:
        """Fallback segmentation using GrabCut."""
        img = cv2.imread(image_path)
        if img is None:
            return SegmentationResult(
                is_valid=False, method="grabcut",
                message=f"Cannot read image: {image_path}",
            )
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        mask = np.zeros((h, w), dtype=np.uint8)
        margin_x, margin_y = int(w * 0.05), int(h * 0.02)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        bgd = np.zeros((1, 65), dtype=np.float64)
        fgd = np.zeros((1, 65), dtype=np.float64)

        try:
            cv2.grabCut(img, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
            mask_binary = np.where(
                (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
            ).astype(np.uint8)
        except cv2.error:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, mask_binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel, iterations=2)
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask_binary = self._keep_largest_component(mask_binary)

        rgba = np.dstack([rgb, mask_binary])
        area_pct = float(np.sum(mask_binary > 0) / mask_binary.size * 100)
        is_valid = 5.0 <= area_pct <= 95.0

        return SegmentationResult(
            rgba_image=rgba,
            mask=mask_binary,
            area_percent=area_pct,
            is_valid=is_valid,
            method="grabcut",
            message="OK" if is_valid else f"Area {area_pct:.1f}% outside 5-95% range",
        )

    # ── Auto-select method ───────────────────────────────────
    def segment(self, image_path: str) -> SegmentationResult:
        """Try RMBG-1.4 first, fall back to GrabCut."""
        if HAS_RMBG:
            result = self.segment_rmbg(image_path)
            if result.is_valid:
                return result
            print(f"    ⚠️  RMBG result invalid ({result.message}), trying GrabCut …")

        return self.segment_grabcut(image_path)

    # ── Utilities ────────────────────────────────────────────
    @staticmethod
    def _keep_largest_component(mask: np.ndarray) -> np.ndarray:
        """Keep only the largest connected component."""
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if n_labels <= 1:
            return mask
        largest_idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        out = np.zeros_like(mask)
        out[labels == largest_idx] = 255
        return out


# ═══════════════════════════════════════════════════════════════
#  STAGE 2 — VIEW SELECTION  (uses GarmentRouter from garment_router.py)
# ═══════════════════════════════════════════════════════════════

def run_view_selection(input_dir: str) -> List[ViewLabel]:
    """
    Classify images in *input_dir* using CLIP zero-shot.
    Returns list of ViewLabel for each image.
    """
    try:
        from garment_router import GarmentRouter
    except ImportError:
        print("    ⚠️  garment_router.py not importable — skipping view selection")
        return []

    router = GarmentRouter()
    routing = router.route_images(input_dir)

    views = []
    for score in routing.all_scores:
        views.append(ViewLabel(
            filename=score.filename,
            filepath=score.filepath,
            label=f"{score.assigned_view}_view" if score.assigned_view != "irrelevant" else "irrelevant",
            confidence=score.confidence,
            scores={
                "front_view": score.front,
                "back_view": score.back,
                "side_view": score.side,
                "irrelevant": score.irrelevant,
            },
        ))
    return views


# ═══════════════════════════════════════════════════════════════
#  STAGE 3 — COLOUR EXTRACTION (K-Means in LAB)
# ═══════════════════════════════════════════════════════════════

class ColourExtractor:
    """
    Determines the dominant garment colour using K-Means clustering
    in the perceptually uniform LAB colour space.
    """

    def __init__(self, n_clusters: int = 5, max_samples: int = 50_000):
        self.n_clusters = n_clusters
        self.max_samples = max_samples

    def extract(self, rgba_image: np.ndarray) -> ColourResult:
        """
        Extract dominant colour and palette from an RGBA garment image.

        Picks the **mid-lightness** cluster as the base colour to avoid
        shadow/highlight bias on fabric photos.
        """
        if not HAS_SKLEARN:
            return ColourResult(success=False, message="scikit-learn not installed")

        if rgba_image is None or rgba_image.shape[2] < 4:
            return ColourResult(success=False, message="Invalid RGBA image")

        # Extract non-transparent pixels
        alpha = rgba_image[:, :, 3]
        mask = alpha > 10
        rgb_pixels = rgba_image[:, :, :3][mask]   # shape (N, 3)

        if len(rgb_pixels) < self.n_clusters:
            return ColourResult(success=False, message="Not enough opaque pixels")

        # Subsample for performance
        if len(rgb_pixels) > self.max_samples:
            idx = np.random.default_rng(42).choice(len(rgb_pixels), self.max_samples, replace=False)
            rgb_pixels = rgb_pixels[idx]

        # Convert to LAB
        pixels_for_cv = rgb_pixels.reshape(-1, 1, 3).astype(np.uint8)
        lab_pixels = cv2.cvtColor(pixels_for_cv, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)

        # K-Means clustering
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lab_pixels)

        # Build palette
        palette: List[ColorInfo] = []
        total = len(labels)
        for i in range(self.n_clusters):
            cluster_mask = labels == i
            pct = float(np.sum(cluster_mask) / total * 100)

            lab_center = kmeans.cluster_centers_[i]
            mean_rgb = np.mean(rgb_pixels[cluster_mask], axis=0).astype(int)
            hex_code = "#{:02x}{:02x}{:02x}".format(*mean_rgb)

            palette.append(ColorInfo(
                rgb=tuple(int(v) for v in mean_rgb),
                lab=tuple(float(v) for v in lab_center),
                hex_code=hex_code,
                percentage=pct,
            ))

        # Sort by L* (lightness) to pick mid-lightness cluster
        palette.sort(key=lambda c: c.lab[0])

        # Mid-lightness selection: pick the middle cluster
        mid_idx = len(palette) // 2
        base_colour = palette[mid_idx]

        # Re-sort by percentage for the output palette
        palette.sort(key=lambda c: c.percentage, reverse=True)

        return ColourResult(
            base_colour_hex=base_colour.hex_code,
            palette=palette,
            success=True,
            message="OK",
        )


# ═══════════════════════════════════════════════════════════════
#  STAGE 4 — DESIGN / GRAPHIC EXTRACTION
# ═══════════════════════════════════════════════════════════════

class DesignExtractor:
    """
    Extracts logos, prints, or graphics from the segmented garment
    using edge detection, contour analysis, and contrast filtering.
    """

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        min_area_ratio: float = 0.01,    # 1% of garment
        max_area_ratio: float = 0.80,    # 80% of garment
        contrast_threshold: float = 0.25,
    ):
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.contrast_threshold = contrast_threshold

    def extract(self, rgba_image: np.ndarray) -> DesignResult:
        """
        Detect and crop any graphic / print from the garment image.

        Pipeline:
          1. Mask out background
          2. Gaussian blur → Canny edge detection
          3. Morphological closing to join fragmented edges
          4. Contour filtering by area
          5. Contrast check (ensure graphic ≠ plain fabric)
          6. Bounding-box crop → transparent RGBA
        """
        if rgba_image is None or rgba_image.shape[2] < 4:
            return DesignResult(message="Invalid RGBA image")

        rgb = rgba_image[:, :, :3]
        alpha = rgba_image[:, :, 3]

        # Work only inside garment mask
        mask = (alpha > 10).astype(np.uint8) * 255
        garment_area = int(np.sum(mask > 0))
        if garment_area == 0:
            return DesignResult(message="Empty garment mask")

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray_masked = cv2.bitwise_and(gray, gray, mask=mask)

        # ── Edge detection ───────────────────────────────────
        blurred = cv2.GaussianBlur(gray_masked, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)

        # Morphological closing to connect fragmented edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # ── Contour analysis ─────────────────────────────────
        contours, _ = cv2.findContours(edges_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return DesignResult(message="No contours found — likely plain garment")

        # Filter contours by area
        min_area = garment_area * self.min_area_ratio
        max_area = garment_area * self.max_area_ratio

        valid_contours = [
            c for c in contours
            if min_area <= cv2.contourArea(c) <= max_area
        ]

        if not valid_contours:
            return DesignResult(message="No contours matched size criteria — likely plain garment")

        # Use the largest valid contour
        best_contour = max(valid_contours, key=cv2.contourArea)
        design_area = cv2.contourArea(best_contour)
        coverage = design_area / garment_area * 100

        # ── Contrast filtering ───────────────────────────────
        x, y, w, h = cv2.boundingRect(best_contour)

        # Ensure bounding box is within image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, rgba_image.shape[1] - x)
        h = min(h, rgba_image.shape[0] - y)

        roi_gray = gray_masked[y:y+h, x:x+w]
        roi_mask = mask[y:y+h, x:x+w]
        roi_pixels = roi_gray[roi_mask > 0]

        if len(roi_pixels) < 10:
            return DesignResult(message="ROI too small for contrast analysis")

        # Check local contrast (std / mean) — high contrast = graphic
        local_std = float(np.std(roi_pixels))
        local_mean = float(np.mean(roi_pixels)) if np.mean(roi_pixels) > 0 else 1
        contrast_ratio = local_std / local_mean

        if contrast_ratio < self.contrast_threshold:
            return DesignResult(
                message=f"Low contrast ({contrast_ratio:.3f}) — likely fabric texture, not a graphic"
            )

        # ── Crop graphic as transparent RGBA ────────────────
        # Create a contour mask for just the graphic region
        graphic_mask = np.zeros_like(mask)
        cv2.drawContours(graphic_mask, [best_contour], -1, 255, -1)

        # Crop to bounding box
        crop_rgba = rgba_image[y:y+h, x:x+w].copy()
        crop_gm = graphic_mask[y:y+h, x:x+w]

        # Apply graphic contour mask to alpha channel
        crop_rgba[:, :, 3] = np.minimum(crop_rgba[:, :, 3], crop_gm)

        return DesignResult(
            graphic_image=crop_rgba,
            has_design=True,
            design_coverage_percent=coverage,
            message=f"Graphic found ({coverage:.1f}% of garment, contrast={contrast_ratio:.3f})",
        )


# ═══════════════════════════════════════════════════════════════
#  AUTO-NUMBERED OUTPUT DIRECTORY
# ═══════════════════════════════════════════════════════════════

def get_next_run_dir(base_dir: str, prefix: str = "ext") -> Path:
    """
    Create the next auto-numbered run directory:
      ext001, ext002, ext003, …
    Always returns an absolute path so PIL / cv2 saves work regardless of CWD.
    """
    base = Path(base_dir).resolve()          # ← absolute path
    base.mkdir(parents=True, exist_ok=True)

    # Only count non-empty run dirs (skip dirs created by failed runs with no files)
    existing_nums = []
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            suffix = d.name[len(prefix):]
            if suffix.isdigit():
                # Count it only if it has at least one file inside
                has_files = any(d.iterdir())
                if has_files:
                    existing_nums.append(int(suffix))

    next_num = (max(existing_nums) + 1) if existing_nums else 1

    run_dir = base / f"{prefix}{next_num:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# ═══════════════════════════════════════════════════════════════
#  VALIDATION
# ═══════════════════════════════════════════════════════════════

def validate_hex(hex_code: str) -> bool:
    """Validate a hex colour code."""
    if not hex_code.startswith("#") or len(hex_code) != 7:
        return False
    try:
        int(hex_code[1:], 16)
        return True
    except ValueError:
        return False


def validate_transparent_bg(rgba: np.ndarray) -> bool:
    """Check that the image has a transparent background (alpha < 10 on edges)."""
    if rgba is None or rgba.shape[2] < 4:
        return False
    alpha = rgba[:, :, 3]
    edge_alpha = np.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
    return float(np.mean(edge_alpha)) < 50  # most edge pixels should be transparent


# ═══════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

class TShirtExtractor:
    """
    Full T-shirt appearance extraction pipeline.

    Usage:
        extractor = TShirtExtractor()
        result = extractor.run("input_images/", output_base="extraction_output")
    """

    def __init__(self):
        self.segmentor = GarmentSegmentor()
        self.colour_extractor = ColourExtractor()
        self.design_extractor = DesignExtractor()

    def run(
        self,
        input_folder: str,
        output_base: str = "extraction_output",
    ) -> ExtractionResult:
        """
        Run the full extraction pipeline.

        Args:
            input_folder: Directory containing 1–10 T-shirt images
            output_base:  Base directory for output folders

        Returns:
            ExtractionResult with paths to all generated files
        """
        t0 = time.time()
        input_path = Path(input_folder)

        # Collect images
        supported = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
        images = sorted([
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported
        ])

        if not images:
            raise FileNotFoundError(f"No images found in {input_folder}")
        if len(images) > 10:
            print(f"⚠️  {len(images)} images found — using first 10")
            images = images[:10]

        print("\n" + "=" * 60)
        print("T-SHIRT APPEARANCE EXTRACTION FOR CLO3D")
        print("=" * 60)
        print(f"  Input:  {input_path} ({len(images)} image{'s' if len(images) > 1 else ''})")

        # Create output directory
        run_dir = get_next_run_dir(output_base)
        print(f"  Output: {run_dir}")
        result = ExtractionResult(run_dir=str(run_dir))

        # ── STAGE 2: View Selection ──────────────────────────
        print(f"\n{'─'*60}")
        print("STAGE 2: View Selection (CLIP)")
        print(f"{'─'*60}")

        try:
            views = run_view_selection(str(input_path))
            result.views = views
        except Exception as e:
            print(f"  ⚠️  View selection failed: {e}")
            views = []

        # Select best front-view image for processing
        # If view selection worked, use best front; otherwise use first image
        target_image = str(images[0])

        if views:
            front_views = [v for v in views if v.label == "front_view"]
            if front_views:
                best_front = max(front_views, key=lambda v: v.confidence)
                target_image = best_front.filepath
                print(f"  ✓ Selected front view: {best_front.filename} ({best_front.confidence:.1%})")
            else:
                # Pick the image with the highest front score
                best = max(views, key=lambda v: v.scores.get("front_view", 0))
                target_image = best.filepath
                print(f"  ℹ️  No clear front view — using best candidate: {best.filename}")
        else:
            print(f"  ℹ️  View selection unavailable — using first image: {images[0].name}")

        # ── STAGE 1: Segmentation ────────────────────────────
        print(f"\n{'─'*60}")
        print("STAGE 1: Segmentation")
        print(f"{'─'*60}")
        print(f"  Processing: {Path(target_image).name}")

        seg = self.segmentor.segment(target_image)
        result.segmentation = seg

        if not seg.is_valid:
            print(f"  ❌ Segmentation failed: {seg.message}")
            # Save metadata with what we have
            self._save_metadata(result, run_dir, time.time() - t0)
            return result

        print(f"  ✓ Method: {seg.method}")
        print(f"  ✓ Garment area: {seg.area_percent:.1f}%")

        # Save base_garment.png
        garment_path = run_dir / "base_garment.png"
        Image.fromarray(seg.rgba_image).save(str(garment_path))
        result.base_garment_path = str(garment_path)
        print(f"  ✓ Saved: {garment_path.name}")

        # Validation: transparent background
        if validate_transparent_bg(seg.rgba_image):
            print("  ✓ Transparent background validated")
        else:
            print("  ⚠️  Background may not be fully transparent")

        # ── STAGE 3: Colour Extraction ───────────────────────
        print(f"\n{'─'*60}")
        print("STAGE 3: Colour Extraction (LAB K-Means)")
        print(f"{'─'*60}")

        colour = self.colour_extractor.extract(seg.rgba_image)
        result.colour = colour

        if colour.success:
            print(f"  ✓ Base colour: {colour.base_colour_hex}")
            if validate_hex(colour.base_colour_hex):
                print(f"  ✓ Valid HEX confirmed")
            else:
                print(f"  ⚠️  Invalid HEX format")

            print(f"  Palette ({len(colour.palette)} clusters):")
            for i, c in enumerate(colour.palette):
                print(f"    {i+1}. {c.hex_code}  RGB{c.rgb}  {c.percentage:.1f}%")

            # Save colors.json
            colors_data = {
                "base_colour_hex": colour.base_colour_hex,
                "palette": [c.to_dict() for c in colour.palette],
            }
            colors_path = run_dir / "colors.json"
            with open(colors_path, "w") as f:
                json.dump(colors_data, f, indent=2)
            result.colors_json_path = str(colors_path)
            print(f"  ✓ Saved: {colors_path.name}")
        else:
            print(f"  ❌ Colour extraction failed: {colour.message}")

        # ── STAGE 4: Design Extraction ───────────────────────
        print(f"\n{'─'*60}")
        print("STAGE 4: Design Extraction (Edge + Contour + Contrast)")
        print(f"{'─'*60}")

        design = self.design_extractor.extract(seg.rgba_image)
        result.design = design

        if design.has_design and design.graphic_image is not None:
            print(f"  ✓ {design.message}")

            # Save graphic_diffuse.png
            graphic_path = run_dir / "graphic_diffuse.png"
            Image.fromarray(design.graphic_image).save(str(graphic_path))
            result.graphic_diffuse_path = str(graphic_path)
            print(f"  ✓ Saved: {graphic_path.name}")

            if validate_transparent_bg(design.graphic_image):
                print("  ✓ Graphic has transparent background")
        else:
            print(f"  ℹ️  {design.message}")

            # Create an empty transparent graphic_diffuse.png
            h, w = seg.rgba_image.shape[:2]
            empty_rgba = np.zeros((h, w, 4), dtype=np.uint8)
            graphic_path = run_dir / "graphic_diffuse.png"
            Image.fromarray(empty_rgba).save(str(graphic_path))
            result.graphic_diffuse_path = str(graphic_path)
            print(f"  ✓ Saved empty: {graphic_path.name}")

        # ── Save extraction metadata ─────────────────────────
        elapsed = time.time() - t0
        self._save_metadata(result, run_dir, elapsed)

        # ── Summary ──────────────────────────────────────────
        print(f"\n{'='*60}")
        print("✅ EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"  Run directory : {run_dir}")
        print(f"  base_garment.png        : {'✓' if result.base_garment_path else '✗'}")
        print(f"  graphic_diffuse.png     : {'✓' if result.graphic_diffuse_path else '✗'}")
        print(f"  colors.json             : {'✓' if result.colors_json_path else '✗'}")
        print(f"  extraction_metadata.json: ✓")
        print(f"  Time elapsed  : {elapsed:.1f}s")

        print(f"\n  CLO3D Integration:")
        print(f"    • Apply base colour ({colour.base_colour_hex if colour and colour.success else 'N/A'}) → Fabric Colour")
        print(f"    • Apply graphic_diffuse.png → Diffuse Texture Map")
        print()

        return result

    def _save_metadata(self, result: ExtractionResult, run_dir: Path, elapsed: float):
        """Save extraction_metadata.json."""
        meta: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "pipeline_version": "1.1",
            "segmentation": None,
            "views": [asdict(v) for v in result.views],
            "colour": None,
            "design": None,
            "clo3d_integration": {
                "base_colour_hex": None,
                "diffuse_map": "graphic_diffuse.png" if result.graphic_diffuse_path else None,
            }
        }

        if result.segmentation:
            meta["segmentation"] = {
                "valid": result.segmentation.is_valid,
                "method": result.segmentation.method,
                "area_percent": round(result.segmentation.area_percent, 2),
                "message": result.segmentation.message,
            }

        if result.colour:
            meta["colour"] = {
                "success": result.colour.success,
                "base_colour_hex": result.colour.base_colour_hex,
                "message": result.colour.message,
            }
            if result.colour.success:
                meta["clo3d_integration"]["base_colour_hex"] = result.colour.base_colour_hex

        if result.design:
            meta["design"] = {
                "has_design": result.design.has_design,
                "coverage_percent": round(result.design.design_coverage_percent, 2),
                "message": result.design.message,
            }

        metadata_path = run_dir / "extraction_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(meta, f, indent=2)
        result.metadata_path = str(metadata_path)


def main():
    parser = argparse.ArgumentParser(
        description="T-Shirt Appearance Extraction for CLO3D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tshirt_extractor.py input_images/ -o extraction_output/
  python tshirt_extractor.py input_images/ --skip-clip
        """,
    )
    parser.add_argument("input_folder", help="Directory containing garment images")
    parser.add_argument("-o", "--output", default="extraction_output", help="Base output directory")
    parser.add_argument("--skip-clip", action="store_true", help="Skip CLIP view selection")

    args = parser.parse_args()

    extractor = TShirtExtractor()

    # Apply override if --skip-clip is used (done via dependency injection for main)
    if args.skip_clip:
        global run_view_selection
        run_view_selection = lambda d: []

    try:
        result = extractor.run(args.input_folder, output_base=args.output)
        if not result.segmentation or not result.segmentation.is_valid:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
