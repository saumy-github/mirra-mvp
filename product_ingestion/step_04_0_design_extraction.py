"""Step 4 of product_ingestion: design extraction.

Extracts logos, prints, or graphics from the segmented garment.

Improvements over the original:
  1. Auto-Canny       — thresholds adapt to image brightness (median-based)
                         instead of fixed 50/150.
  2. Local variance   — replaces the fragile std/mean contrast ratio with a
                         per-patch variance map, catching low-contrast logos.
  3. FFT pattern det  — detects repeating all-over prints that Canny misses.
  4. Multi-contour    — merges all valid contours instead of keeping only the
                         largest one.
  5. Contour alpha    — the contour shape itself becomes the alpha channel,
                         not just a rectangular bounding box.
  6. Design type      — classifies the design as 'logo', 'text', or 'pattern'
                         using edge density and FFT energy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import cv2


# ─────────────────────────────────────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DesignResult:
    """Result from Stage 4: Design Extraction."""
    graphic_image: Optional[np.ndarray] = None   # RGBA crop of the design
    has_design: bool = False
    design_coverage_percent: float = 0.0
    design_type: str = ""                        # type of the main design (see regions for all)
    message: str = ""
    # P05 (two-level outlining): every design region found inside the garment, in the pixels of
    # the input image: [{"box": [x0, y0, x1, y1], "type": "text|graphic|logo|stripes|colour_block|pattern",
    #                    "confidence": float, "source": str}, ...].  [] = no design found.
    regions: list = field(default_factory=list)
    method: str = "v0"
    main_type: str = ""      # true type of the main region (design_type keeps the old "logo|text|pattern" vocabulary)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _auto_canny(gray: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    """
    Canny edge detection with automatic thresholds.

    How it works:
      Instead of hardcoding low=50, high=150 (which fails on dark or bright
      garments), we compute the median brightness of the image and set:

        low  = 0.66 × median   (catches softer edges)
        high = 1.33 × median   (ignores noise)

      The `sigma` parameter controls how wide the range is:
        sigma=0.33 is the standard (works for most images).

      Dark image (median=40)  → low=27, high=53  → catches subtle edges
      Bright image (median=200) → low=134, high=266 → ignores highlights
    """
    median = float(np.median(gray[gray > 0])) if np.any(gray > 0) else 128.0
    low = int(max(0, (1.0 - sigma) * median))
    high = int(min(255, (1.0 + sigma) * median))
    return cv2.Canny(gray, low, high)


def _local_variance_map(gray: np.ndarray, ksize: int = 15) -> np.ndarray:
    """
    Compute local variance at each pixel using a sliding window.

    Why this replaces std/mean:
      The old code computed ONE number (std/mean) for the entire ROI.
      A low-contrast logo on a medium-contrast background could average out
      to a low ratio and get rejected.

      Local variance computes contrast at every small patch (15×15 window).
      If ANY region has high variance, we know there's a design there —
      even if the rest of the garment is plain.

    How it works:
      variance = E[x²] - E[x]²

      1. Compute the local mean using a blur (box filter).
      2. Compute the local mean of x² using another blur.
      3. Subtract: variance = mean(x²) - mean(x)².

    Returns a float32 map where bright areas = high local contrast.
    """
    gray_f = gray.astype(np.float32)
    local_mean = cv2.blur(gray_f, (ksize, ksize))
    local_sq_mean = cv2.blur(gray_f ** 2, (ksize, ksize))
    variance = local_sq_mean - local_mean ** 2
    # Clip tiny negatives from float rounding
    variance = np.maximum(variance, 0.0)
    return variance


def _has_repeating_pattern(gray_masked: np.ndarray, mask: np.ndarray) -> tuple[bool, float]:
    """
    Detect repeating all-over prints using FFT (Fast Fourier Transform).

    Why we need this:
      Canny + contours works great for single logos (one blob of edges).
      But all-over prints (e.g. polka dots, stripes, floral) produce
      THOUSANDS of small contours that individually are too small to pass
      the area filter. They get rejected as "noise".

      FFT converts the image from "pixel space" to "frequency space".
      A repeating pattern shows up as strong peaks at specific frequencies.
      Plain fabric has NO peaks — just random noise spread evenly.

    How it works:
      1. Take the greyscale garment pixels.
      2. Compute 2D FFT → shift zero-frequency to center.
      3. Compute the magnitude spectrum (how strong each frequency is).
      4. Mask out the DC component (center pixel = average brightness,
         not a pattern).
      5. Compute the ratio:  peak_energy / mean_energy.
         High ratio (> 8) = repeating pattern.
         Low ratio = random texture / plain.

    Returns (is_pattern, energy_ratio).
    """
    # Apply mask — set background to the garment's mean grey
    # (avoids sharp mask boundary creating fake FFT peaks)
    garment_pixels = gray_masked[mask > 0]
    if len(garment_pixels) < 100:
        return False, 0.0

    mean_val = float(np.mean(garment_pixels))
    img_for_fft = np.where(mask > 0, gray_masked.astype(np.float32), mean_val)

    # 2D FFT
    f_transform = np.fft.fft2(img_for_fft)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)

    # Zero out the DC component (center 5×5 block)
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    magnitude[cy - 2:cy + 3, cx - 2:cx + 3] = 0

    mean_energy = float(np.mean(magnitude))
    peak_energy = float(np.max(magnitude))

    if mean_energy < 1e-6:
        return False, 0.0

    energy_ratio = peak_energy / mean_energy
    # Threshold: 8× above mean = repeating pattern
    return energy_ratio > 8.0, energy_ratio


def _classify_design_type(
    contour_mask: np.ndarray,
    gray: np.ndarray,
    garment_mask: np.ndarray,
    is_pattern: bool,
) -> str:
    """
    Classify the detected design as 'logo', 'text', or 'pattern'.

    How it works:
      - 'pattern' → if FFT detected repeating frequencies (from above).
      - 'text'    → text regions have very high edge density. Tiny strokes
                     produce many edges per unit area. We compute:
                       edge_density = (# edge pixels in design) / (# design pixels)
                     If > 0.3 (30% of the design area is edges), it's likely text.
      - 'logo'    → everything else (a single graphic region, not text,
                     not a repeating pattern).
    """
    if is_pattern:
        return "pattern"

    # Compute edge density inside the design region
    design_pixels = gray[contour_mask > 0]
    if len(design_pixels) < 10:
        return "logo"

    edges = cv2.Canny(gray, 50, 150)
    design_edges = edges[contour_mask > 0]
    edge_density = float(np.sum(design_edges > 0) / len(design_pixels))

    if edge_density > 0.3:
        return "text"

    return "logo"


# ─────────────────────────────────────────────────────────────────────────────
#  Main extractor
# ─────────────────────────────────────────────────────────────────────────────

class DesignExtractor:
    """
    Extracts logos, prints, or graphics from the segmented garment.

    Pipeline:
      1. Mask out background using alpha channel.
      2. Auto-Canny edge detection (adaptive thresholds).
      3. Morphological closing to join fragmented edges.
      4. Filter contours by area (1%–80% of garment).
      5. Local variance check (replaces old std/mean ratio).
      6. FFT check for repeating patterns.
      7. Merge all valid contours → contour-shaped alpha crop.
      8. Classify design type (logo / text / pattern).
    """

    def __init__(
        self,
        min_area_ratio: float = 0.01,     # 1% of garment
        max_area_ratio: float = 0.80,     # 80% of garment
        variance_threshold: float = 200,  # min local variance to be a "design"
    ):
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.variance_threshold = variance_threshold

    def extract(self, rgba_image: np.ndarray) -> DesignResult:
        """
        Detect and crop any graphic / print from the garment image.
        """
        if rgba_image is None or rgba_image.shape[2] < 4:
            return DesignResult(message="Invalid RGBA image")

        rgb = rgba_image[:, :, :3]
        alpha = rgba_image[:, :, 3]

        # ── Step 1: build garment mask ────────────────────────────────────
        # Pixels with alpha > 10 are garment (from segmentation stage).
        garment_mask = (alpha > 10).astype(np.uint8) * 255
        garment_area = int(np.sum(garment_mask > 0))
        if garment_area == 0:
            return DesignResult(message="Empty garment mask")

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray_masked = cv2.bitwise_and(gray, gray, mask=garment_mask)

        # ── Step 2: auto-Canny edge detection ─────────────────────────────
        # Thresholds are computed from the image's own median brightness,
        # so dark garments and bright garments both get good edges.
        blurred = cv2.GaussianBlur(gray_masked, (5, 5), 0)
        edges = _auto_canny(blurred)

        # ── Step 3: morphological closing ─────────────────────────────────
        # Joins edge fragments that are close together into solid regions.
        # A 7×7 kernel with 2 iterations bridges gaps up to ~14px wide.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # ── Step 4: find and filter contours by area ──────────────────────
        contours, _ = cv2.findContours(
            edges_closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )

        min_area = garment_area * self.min_area_ratio
        max_area = garment_area * self.max_area_ratio

        valid_contours = [
            c for c in contours
            if min_area <= cv2.contourArea(c) <= max_area
        ]

        # ── Step 5: local variance check ──────────────────────────────────
        # Instead of the old std/mean ratio on the whole ROI, we compute
        # local variance at every pixel. If the max variance inside any
        # contour exceeds our threshold, it's a real design, not plain fabric.
        variance_map = _local_variance_map(gray_masked)

        design_contours: List[np.ndarray] = []
        for contour in valid_contours:
            # Build a mask for just this contour
            contour_test = np.zeros_like(garment_mask)
            cv2.drawContours(contour_test, [contour], -1, 255, -1)

            # Check if max local variance inside this contour is high enough
            local_var = variance_map[contour_test > 0]
            if len(local_var) > 0 and float(np.max(local_var)) > self.variance_threshold:
                design_contours.append(contour)

        # ── Step 6: FFT check for repeating patterns ──────────────────────
        # If Canny found no valid contours (all-over print = tiny edges),
        # check FFT. If it detects a repeating pattern, treat the ENTIRE
        # garment as the design region.
        is_pattern, fft_energy = _has_repeating_pattern(gray_masked, garment_mask)

        # Override FFT pattern classification if the contours are sparse / small coverage.
        # Repeating all-over patterns cover most of the garment and have many contours.
        if is_pattern and design_contours:
            merged_temp = np.zeros_like(garment_mask)
            cv2.drawContours(merged_temp, design_contours, -1, 255, -1)
            temp_area = int(np.sum(merged_temp > 0))
            temp_coverage = temp_area / garment_area
            if temp_coverage < 0.35 or len(design_contours) < 15:
                is_pattern = False

        if not design_contours and not is_pattern:
            return DesignResult(
                message="No design found — likely plain garment"
            )

        # ── Step 7: build merged contour mask ─────────────────────────────
        # Instead of picking only the largest contour, we merge ALL valid
        # contours into one mask. This catches: logo + text, logo + badge, etc.
        #
        # For patterns (all-over print), we use the garment mask itself.
        if is_pattern and not design_contours:
            merged_mask = garment_mask.copy()
            design_type = "pattern"
        else:
            merged_mask = np.zeros_like(garment_mask)
            cv2.drawContours(merged_mask, design_contours, -1, 255, -1)
            design_type = _classify_design_type(
                merged_mask, gray, garment_mask, is_pattern
            )

        # Compute coverage
        design_area = int(np.sum(merged_mask > 0))
        coverage = float(design_area / garment_area * 100)

        # ── Step 8: crop with contour-shaped alpha ────────────────────────
        # The old code used a rectangular bounding box, losing the shape.
        # Now the contour mask IS the alpha — non-rectangular graphics
        # keep their actual shape.
        x, y, w, h = cv2.boundingRect(merged_mask)
        x = max(0, x)
        y = max(0, y)
        w = min(w, rgba_image.shape[1] - x)
        h = min(h, rgba_image.shape[0] - y)

        crop_rgb = rgb[y:y+h, x:x+w].copy()
        crop_contour = merged_mask[y:y+h, x:x+w]
        crop_alpha = np.minimum(alpha[y:y+h, x:x+w], crop_contour)
        crop_rgba = np.dstack([crop_rgb, crop_alpha])

        return DesignResult(
            graphic_image=crop_rgba,
            has_design=True,
            design_coverage_percent=coverage,
            design_type=design_type,
            regions=[{"box": [float(x), float(y), float(x + w), float(y + h)], "type": design_type,
                      "confidence": 0.5, "source": "v0"}],
            method="v0",
            message=(
                f"Design found: type={design_type}, "
                f"coverage={coverage:.1f}%, "
                f"contours={len(design_contours)}, "
                f"fft_energy={fft_energy:.1f}"
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Public helpers (unchanged API)
# ─────────────────────────────────────────────────────────────────────────────

def make_empty_graphic_like(rgba_image):
    """Create an empty transparent RGBA image matching the segmented garment size."""
    height, width = rgba_image.shape[:2]
    return np.zeros((height, width, 4), dtype=np.uint8)


# Default method of the pipeline.  "v0" is the original extractor (kept for before/after runs);
# "v3_combo" is the P05 two-level method (v2_combo = the same without Grounding DINO) (see cv_design_regions.py and CV/out/p05_design/REPORT.md).
# "v4_relabel" (P15b, default) = v3_combo + two fixes (caption text inside a print is kept, merged text lines are split)
# + zero-shot SigLIP 2 relabelling of each region (a "plain" prediction drops it).  "v3_fix" = the fixes only,
# "v4_nofix" = the relabelling only.  The SigLIP 2 model is loaded lazily on first use (CPU fallback); the CALLER
# guards the GPU (gpu_lock) and may call cv_design_regions.release_labeller() afterwards.
DEFAULT_METHOD = "v4_relabel"

_MAIN_TYPES = ("graphic", "logo", "text", "pattern", "stripes")


def _result_from_regions(rgba_image: np.ndarray, regions: list, method: str) -> DesignResult:
    """Build the DesignResult (compatible fields) from the detected regions."""
    alpha = rgba_image[:, :, 3]
    garment_area = max(int((alpha > 10).sum()), 1)
    designs = [r for r in regions if r["type"] in _MAIN_TYPES]
    if not designs:
        return DesignResult(regions=regions, method=method,
                            message=("No design found - likely plain garment" if not regions
                                     else "Only colour blocks found"))
    h, w = alpha.shape
    def _area(r):
        b = r["box"]
        return (b[2] - b[0]) * (b[3] - b[1])
    main = max(designs, key=_area)
    x0, y0, x1, y1 = [int(round(v)) for v in main["box"]]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    crop = rgba_image[y0:y1, x0:x1].copy()
    cov_mask = np.zeros((h, w), bool)
    for r in designs:
        bx = [int(round(v)) for v in r["box"]]
        cov_mask[max(0, bx[1]):bx[3], max(0, bx[0]):bx[2]] = True
    coverage = float((cov_mask & (alpha > 10)).sum() / garment_area * 100)
    types = ", ".join(sorted({r["type"] for r in regions}))
    # Step 3 (step_08_apply_fabric) only knows logo | text | pattern: graphic and stripes crops are applied
    # as an overlay like a logo, so they are reported as "logo" in design_type; main_type / regions keep the true type.
    compat = {"graphic": "logo", "stripes": "logo"}.get(main["type"], main["type"])
    return DesignResult(graphic_image=crop, has_design=True, design_coverage_percent=coverage,
                        design_type=compat, main_type=main["type"], regions=regions, method=method,
                        message=f"Design regions: {len(regions)} ({types}); main={main['type']}, coverage={coverage:.1f}%")


def extract_design(rgba_image, method: Optional[str] = None) -> DesignResult:
    """Extract the design(s) of a segmented cloth image.

    Keeps the original module API used by the runner: returns a DesignResult.
    method="v0": the original single-design extractor.  Any other value (default
    DEFAULT_METHOD) runs the two-level detector of cv_design_regions.py and returns every
    design region in DesignResult.regions; graphic_image is the crop of the main design.
    """
    method = method or DEFAULT_METHOD
    if method == "v0":
        return DesignExtractor().extract(rgba_image)
    if rgba_image is None or rgba_image.ndim != 3 or rgba_image.shape[2] < 4:
        return DesignResult(message="Invalid RGBA image")
    mask = rgba_image[:, :, 3] > 10
    if not mask.any():
        return DesignResult(message="Empty garment mask")
    try:
        try:
            from cv_design_regions import detect_regions
        except ImportError:
            from product_ingestion.cv_design_regions import detect_regions
        regions = detect_regions(rgba_image[:, :, :3], mask, method=method)
    except Exception as exc:  # noqa: BLE001  - never break the pipeline: fall back to v0
        res = DesignExtractor().extract(rgba_image)
        res.message = f"[fallback to v0: {type(exc).__name__}: {exc}] " + res.message
        return res
    return _result_from_regions(rgba_image, regions, method)
