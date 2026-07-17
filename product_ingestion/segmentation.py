"""Step 1: Segmentation

# ═══════════════════════════════════════════════════════════════
#  STAGE 1 — SEGMENTATION
#
#  Method priority:
#    1. SAM 2  (facebook/sam2-hiera-large)
#              Promptable, runs at native resolution.
#              Device: MPS → CUDA → CPU  (full PyTorch support)
#
#    2. U²-Net (via rembg)
#              Salient-object segmentation fallback.
#              Device: CUDA → CPU
#              Note: ONNX Runtime does not support MPS; Apple Silicon
#              falls back to CPU for this stage only.
#
#  Device priority (resolved once at init, shared across all stages):
#    MPS (Apple Silicon) → CUDA (NVIDIA) → CPU
# ═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os

# MPS does not implement every PyTorch kernel (e.g. upsample_bicubic2d used
# by SAM 2's positional-embedding interpolation).  This env var tells PyTorch
# to fall back to CPU for any unsupported MPS op instead of raising
# NotImplementedError.  Everything else still runs on the MPS GPU.
# Must be set before torch is imported.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import cv2

# ── SAM 2 ────────────────────────────────────────────────────────────────────
try:
    import torch
    from transformers import Sam2Processor, Sam2Model
    HAS_SAM2 = True
except Exception:
    HAS_SAM2 = False

# ── U²-Net via rembg ─────────────────────────────────────────────────────────
try:
    from rembg import new_session, remove as rembg_remove
    HAS_U2NET = True
except Exception:
    HAS_U2NET = False


# ─────────────────────────────────────────────────────────────────────────────
#  Device resolution — MPS → CUDA → CPU
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_device() -> str:
    """Return the best available PyTorch device: MPS → CUDA → CPU."""
    if not HAS_SAM2:
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _onnx_providers(device: str) -> list[str]:
    """
    Map a PyTorch device string to ONNX Runtime execution providers.

    MPS is not supported by ONNX Runtime, so Apple Silicon falls back to CPU
    here. CUDA maps to CUDAExecutionProvider.
    """
    if device == "cuda":
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    # "mps" and "cpu" both use CPU for ONNX
    return ["CPUExecutionProvider"]


# ─────────────────────────────────────────────────────────────────────────────
#  Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SegmentationResult:
    """Result from Stage 1: Segmentation."""
    rgba_image: Optional[np.ndarray] = None      # H×W×4  RGBA (hard mask)
    mask: Optional[np.ndarray] = None            # H×W    uint8 (0/255)
    rgba_feathered: Optional[np.ndarray] = None  # H×W×4  RGBA (soft 3px feather)
    area_percent: float = 0.0
    is_valid: bool = False
    method: str = ""
    message: str = ""
    quality_score: float = 0.0        # [0, 1] composite quality
    quality_metrics: Optional[dict] = None  # detailed breakdown


# ─────────────────────────────────────────────────────────────────────────────
#  Main segmentor
# ─────────────────────────────────────────────────────────────────────────────

class GarmentSegmentor:
    """
    Isolates the garment from its background.

    Fallback chain:
      1. SAM 2  — prompted with center foreground + corner backgrounds.
                  If center-point mask is out of range, retries with a
                  3×3 grid of foreground points in the central 60 % of frame.
      2. U²-Net — salient object detection via rembg (worst-case fallback).
    """

    def __init__(self):
        self._device: str = _resolve_device()
        self._sam2_model = None
        self._sam2_processor = None
        self._u2net_session = None
        print(f"    GarmentSegmentor: device = '{self._device}'")

    # ── SAM 2 ────────────────────────────────────────────────────────────────

    def _load_sam2(self):
        """Lazy-load SAM 2 once. Subsequent calls are no-ops."""
        if self._sam2_model is not None:
            return
        if not HAS_SAM2:
            raise RuntimeError(
                "SAM 2 requires: pip install torch 'transformers>=4.42'"
            )
        print("    Loading SAM 2 (facebook/sam2-hiera-large) …")
        model_id = "facebook/sam2-hiera-large"
        self._sam2_processor = Sam2Processor.from_pretrained(model_id)
        self._sam2_model = (
            Sam2Model.from_pretrained(model_id)
            .to(self._device)
            .eval()
        )
        print(f"    ✓ SAM 2 ready on '{self._device}'")

    def _run_sam2_pass(
        self,
        pil_img: Image.Image,
        fg_points: list[list[int]],
        bg_points: list[list[int]],
    ) -> np.ndarray:
        """
        One SAM 2 forward pass.

        fg_points: [[x, y], ...]  — foreground prompts (label = 1)
        bg_points: [[x, y], ...]  — background prompts (label = 0)

        Returns a uint8 mask (0 | 255) at original image resolution.
        """
        import torch.nn.functional as F

        all_points = fg_points + bg_points
        all_labels = [1] * len(fg_points) + [0] * len(bg_points)

        # Processor expects:  [batch, num_point_sets, num_points, 2]
        inputs = self._sam2_processor(
            images=pil_img,
            input_points=[[all_points]],
            input_labels=[[all_labels]],
            return_tensors="pt",
        )
        inputs = {
            k: v.to(self._device) if hasattr(v, "to") else v
            for k, v in inputs.items()
        }

        with torch.no_grad():
            outputs = self._sam2_model(**inputs)

        # pred_masks shape varies across transformers versions:
        #   some:  [batch, num_masks, H, W]          → 4-D
        #   some:  [batch, 1, num_masks, H, W]       → 5-D
        # We squeeze away every leading dim until we have [num_masks, H, W],
        # then pick the mask with the highest IOU score.
        pred_masks = outputs.pred_masks.cpu().float()
        scores     = outputs.iou_scores.cpu().flatten()  # [num_masks]

        # Collapse to [num_masks, H, W] regardless of how many leading 1-dims
        while pred_masks.dim() > 3:
            pred_masks = pred_masks.squeeze(0)

        best_idx  = int(scores.argmax())
        best_mask = pred_masks[best_idx]  # [H_model, W_model]

        # Resize from SAM2's internal resolution back to original image size.
        orig_w, orig_h = pil_img.size     # PIL returns (width, height)
        resized = F.interpolate(
            best_mask.unsqueeze(0).unsqueeze(0),  # [1, 1, H_model, W_model]
            size=(orig_h, orig_w),
            mode="bilinear",
            align_corners=False,
        ).squeeze()  # [orig_h, orig_w]

        return (resized > 0.0).numpy().astype(np.uint8) * 255

    def segment_sam2(self, image_path: str) -> SegmentationResult:
        """
        Segment using SAM 2 with a two-pass prompting strategy.

        Pass 1 — single center foreground point + 4 corner background points.
        Pass 2 — if Pass 1 area is outside [5 %, 95 %], retry with a 3×3
                  foreground grid over the central 60 % of the image.
        """
        try:
            self._load_sam2()
        except RuntimeError as e:
            return SegmentationResult(
                is_valid=False, method="sam2", message=f"Load failed: {e}"
            )

        pil_img = Image.open(image_path).convert("RGB")
        W, H = pil_img.size

        # ── Pass 1: center point ──────────────────────────────────────────────
        print("    SAM2 Pass 1: center-point prompt …")
        fg_center  = [[W // 2, H // 2]]
        bg_corners = [[0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1]]

        mask_binary = self._run_sam2_pass(pil_img, fg_center, bg_corners)
        mask_binary = self._clean_mask(mask_binary)
        area_pct = float(np.sum(mask_binary > 0) / mask_binary.size * 100)

        if not (5.0 <= area_pct <= 95.0):
            # ── Pass 2: 3×3 grid in the central 60 % ─────────────────────────
            print(
                f"    SAM2 Pass 1 area = {area_pct:.1f}% (out of range). "
                "Retrying with 3×3 grid prompt …"
            )
            x0, x1 = int(W * 0.2), int(W * 0.8)
            y0, y1 = int(H * 0.2), int(H * 0.8)
            fg_grid = [
                [x0 + (x1 - x0) * c // 2, y0 + (y1 - y0) * r // 2]
                for r in range(3)
                for c in range(3)
            ]
            mask_binary = self._run_sam2_pass(pil_img, fg_grid, bg_corners)
            mask_binary = self._clean_mask(mask_binary)
            area_pct = float(np.sum(mask_binary > 0) / mask_binary.size * 100)

        is_valid = 5.0 <= area_pct <= 95.0
        rgba = np.dstack([np.array(pil_img), mask_binary])

        return SegmentationResult(
            rgba_image=rgba,
            mask=mask_binary,
            area_percent=area_pct,
            is_valid=is_valid,
            method="sam2",
            message="OK" if is_valid else f"Area {area_pct:.1f}% outside 5–95%",
        )

    # ── U²-Net via rembg ─────────────────────────────────────────────────────

    def _load_u2net(self):
        """Lazy-load rembg U²-Net session once. Subsequent calls are no-ops."""
        if self._u2net_session is not None:
            return
        if not HAS_U2NET:
            raise RuntimeError("U²-Net requires: pip install rembg")
        providers = _onnx_providers(self._device)
        print(f"    Loading U²-Net (rembg) with providers {providers} …")
        # "u2net" is rembg's default salient-object model
        self._u2net_session = new_session("u2net", providers=providers)
        print("    ✓ U²-Net ready")

    def segment_u2net(self, image_path: str) -> SegmentationResult:
        """
        Segment using U²-Net via rembg.

        Device note: ONNX Runtime does not support MPS.
          - CUDA → CUDAExecutionProvider (GPU)
          - MPS / CPU → CPUExecutionProvider
        """
        try:
            self._load_u2net()
        except RuntimeError as e:
            return SegmentationResult(
                is_valid=False, method="u2net", message=f"Load failed: {e}"
            )

        pil_img = Image.open(image_path).convert("RGB")

        # rembg returns a PIL RGBA image with alpha = segmentation mask
        result_pil: Image.Image = rembg_remove(pil_img, session=self._u2net_session)
        result_np = np.array(result_pil)          # H×W×4

        # Extract mask from alpha channel; binarise at 128
        mask_binary = (result_np[:, :, 3] > 128).astype(np.uint8) * 255
        mask_binary = self._clean_mask(mask_binary)

        # Rebuild RGBA using original RGB + cleaned mask
        orig_np = np.array(pil_img)
        rgba = np.dstack([orig_np, mask_binary])
        area_pct = float(np.sum(mask_binary > 0) / mask_binary.size * 100)
        is_valid = 5.0 <= area_pct <= 95.0

        return SegmentationResult(
            rgba_image=rgba,
            mask=mask_binary,
            area_percent=area_pct,
            is_valid=is_valid,
            method="u2net",
            message="OK" if is_valid else f"Area {area_pct:.1f}% outside 5–95%",
        )

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def segment(self, image_path: str) -> SegmentationResult:
        """Run segmentation with fallback chain: SAM 2 → U²-Net."""
        # 1. SAM 2 (primary)
        if HAS_SAM2:
            result = self.segment_sam2(image_path)
            if result.is_valid:
                return self._finalize_result(result, image_path)
            print(f"    ⚠  SAM2 invalid ({result.message}), falling back to U²-Net …")

        # 2. U²-Net (worst-case fallback)
        if HAS_U2NET:
            result = self.segment_u2net(image_path)
            if result.is_valid:
                return self._finalize_result(result, image_path)
            print(f"    ⚠  U²-Net invalid ({result.message})")

        return SegmentationResult(
            is_valid=False,
            method="none",
            message="All segmentation methods failed for this image.",
        )

    def _finalize_result(
        self, result: SegmentationResult, image_path: str
    ) -> SegmentationResult:
        """Compute quality metrics and feathered RGBA for a valid result."""
        quality_score, quality_metrics = GarmentSegmentor._compute_quality(result.mask)
        result.quality_score = quality_score
        result.quality_metrics = quality_metrics

        pil_img = Image.open(image_path).convert("RGB")
        rgb = np.array(pil_img)
        result.rgba_feathered = GarmentSegmentor._feather_mask(result.mask, rgb)

        print(
            f"    Quality: {quality_score:.3f} "
            f"(coverage={quality_metrics['area_percent']:.1f}%, "
            f"sharpness={quality_metrics['edge_sharpness_score']:.2f}, "
            f"holes={quality_metrics['hole_count']})"
        )
        return result

    # ── Shared utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _clean_mask(mask: np.ndarray) -> np.ndarray:
        """Morphological open + close → largest component → fill holes."""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = GarmentSegmentor._keep_largest_component(mask)
        return GarmentSegmentor._fill_holes(mask)

    @staticmethod
    def _keep_largest_component(mask: np.ndarray) -> np.ndarray:
        """Discard all connected components except the largest one."""
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        if n_labels <= 1:
            return mask
        largest_idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        out = np.zeros_like(mask)
        out[labels == largest_idx] = 255
        return out

    @staticmethod
    def _fill_holes(mask: np.ndarray) -> np.ndarray:
        """Fill enclosed holes in the binary mask via flood-fill inversion.

        Algorithm:
          1. Invert mask → background is 255, garment is 0.
          2. Flood-fill the external background (from corner) to 0.
          3. Whatever remains 255 in the flooded image = isolated internal holes.
          4. OR with original mask to fill those holes.
        """
        inverted = cv2.bitwise_not(mask)
        flooded = inverted.copy()
        h, w = flooded.shape
        flood_mask = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(flooded, flood_mask, (0, 0), 0)
        # flooded now contains only internal hole pixels (255); external bg is 0
        return cv2.bitwise_or(mask, flooded)

    @staticmethod
    def _feather_mask(mask: np.ndarray, rgb: np.ndarray, radius: int = 3) -> np.ndarray:
        """Return RGBA with a soft alpha feather at mask edges.

        Inside the mask: alpha = 255.  At the boundary: gaussian-blurred falloff.
        Outside: alpha = 0.  Used for texture projection (base_garment_feathered).
        """
        blur_size = radius * 4 + 1  # must be odd
        soft = cv2.GaussianBlur(mask.astype(np.float32), (blur_size, blur_size), 0)
        alpha = np.where(mask > 0, 255, soft).astype(np.uint8)
        return np.dstack([rgb, alpha])

    @staticmethod
    def _compute_quality(mask: np.ndarray) -> tuple[float, dict]:
        """Compute composite quality score and per-metric breakdown.

        Returns (quality_score in [0, 1], metrics dict).
        """
        area_pct = float(np.sum(mask > 0) / max(1, mask.size) * 100)

        # Coverage score: peak [10%, 80%], drops off outside that range.
        if 10.0 <= area_pct <= 80.0:
            coverage_score = 1.0
        elif area_pct < 10.0:
            coverage_score = area_pct / 10.0
        else:
            coverage_score = max(0.0, (95.0 - area_pct) / 15.0)

        # Edge sharpness: Sobel gradient magnitude averaged over the boundary.
        d_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated  = cv2.dilate(mask, d_kernel, iterations=1)
        eroded   = cv2.erode(mask,  d_kernel, iterations=1)
        boundary = (dilated.astype(np.int32) - eroded.astype(np.int32)).clip(0, 255).astype(np.uint8)
        boundary_count = int(np.sum(boundary > 0))
        if boundary_count > 0:
            sx = cv2.Sobel(mask.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
            sy = cv2.Sobel(mask.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
            grad_mag = cv2.magnitude(sx, sy)
            boundary_sharpness = float(np.mean(grad_mag[boundary > 0]))
            edge_sharpness_score = min(1.0, boundary_sharpness / 100.0)
        else:
            # No boundary pixels = mask is entirely empty or entirely full.
            # Empty mask → worst score; full mask → treat as sharp (edge at image border).
            edge_sharpness_score = 0.0 if area_pct < 1.0 else 1.0

        # Hole count: connected components in the inverted mask (excluding external bg).
        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(mask), connectivity=8
        )
        # Label 0 = background (external); labels 1..n = holes + noise.
        # Discard tiny components (< 50px) as noise.
        hole_count = sum(
            1 for i in range(1, n_labels)
            if stats[i, cv2.CC_STAT_AREA] >= 50
        )
        hole_penalty = min(1.0, hole_count / 10.0)

        quality_score = (
            0.5 * coverage_score
            + 0.3 * edge_sharpness_score
            + 0.2 * (1.0 - hole_penalty)
        )

        return quality_score, {
            "area_percent":          round(area_pct, 2),
            "coverage_score":        round(coverage_score, 3),
            "edge_sharpness_score":  round(edge_sharpness_score, 3),
            "hole_count":            hole_count,
            "hole_penalty":          round(hole_penalty, 3),
            "quality_score":         round(quality_score, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_transparent_bg(rgba: np.ndarray) -> bool:
    """Return True if image edges are mostly transparent (good segmentation)."""
    if rgba is None or rgba.shape[2] < 4:
        return False
    alpha = rgba[:, :, 3]
    edge_alpha = np.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
    return float(np.mean(edge_alpha)) < 50


def run_segmentation(image_path: str | Path) -> tuple[SegmentationResult, bool]:
    """Public entry point: segment the garment and validate edge transparency."""
    segmentor = GarmentSegmentor()
    result = segmentor.segment(str(image_path))
    transparent_bg_ok = bool(
        result.rgba_image is not None and validate_transparent_bg(result.rgba_image)
    )
    return result, transparent_bg_ok
