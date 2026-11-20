"""Step 2: Segmentation

# ═══════════════════════════════════════════════════════════════
#  STAGE 2 — SEGMENTATION
#
#  Selectable methods (CV project plans P01 and P15a, see
#  CV/out/p01_segmentation/REPORT.md for the comparison):
#
#    method="v1_auto" (default)  see below: v1 or v1_all chosen per photo.
#    method="v1"             SegFormer garment region (Upper-clothes + Dress)
#                            -> box + interior point -> SAM 2 (single mask)
#                            -> clean (small holes only).
#                            Fallbacks: SegFormer with Skirt added -> RMBG-1.4 box
#                            -> SAM 2, then v0.
#    method="v1_auto"        v1 or v1_all, chosen per photo (plan P15a): the Skirt region is
#                            added when it is at least 1 % of the photo and no head (Face +
#                            Hair < 1 %) is visible; otherwise plain v1. Fixes the lower half
#                            of a colour-block top labelled "Skirt" without including the
#                            real skirt of a person.
#    method="v1_all"         Same, but the garment region also includes Skirt
#                            (SegFormer often labels the lower half of a top as
#                            Skirt on cropped photos) and SegFormer's arm / face /
#                            hair / leg pixels are removed from the SAM 2 mask.
#    method="v0"             The original pipeline, unchanged: SAM 2 with a
#                            centre point + 4 corner background points and the
#                            highest-predicted-IoU candidate, flood fill from
#                            pixel (0, 0), U²-Net fallback, old quality score.
#
#  Select with run_segmentation(path, method="v0") or the environment
#  variable MIRRA_SEG_METHOD=v0.
#
#  Device priority (resolved once at init): MPS → CUDA → CPU
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

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import cv_segment as cs
    HAS_CV_SEGMENT = True
except Exception:  # noqa: BLE001
    cs = None
    HAS_CV_SEGMENT = False

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

DEFAULT_METHOD = "v1_auto"
V1_MIN_AREA_PCT = 1.0   # smallest valid garment area (% of image) for a mask prompted by the clothes parser


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
    # added by the CV project (P01); optional, ignored by older code
    outline_polygon: Optional[list] = None   # simplified garment outline [[x, y], ...] in pixels
    details: Optional[dict] = field(default=None)  # how the mask was made (boxes, prompts, fallbacks)


# ─────────────────────────────────────────────────────────────────────────────
#  Main segmentor
# ─────────────────────────────────────────────────────────────────────────────

class GarmentSegmentor:
    """
    Isolates the garment from its background.

    method="v1" (default): see the module docstring and `segment_v1`.
    method="v0": the original fallback chain
      1. SAM 2  — prompted with center foreground + corner backgrounds.
                  If center-point mask is out of range, retries with a
                  3×3 grid of foreground points in the central 60 % of frame.
      2. U²-Net — salient object detection via rembg (worst-case fallback).
    """

    def __init__(self, method: Optional[str] = None):
        self.method = (method or os.environ.get("MIRRA_SEG_METHOD") or DEFAULT_METHOD).lower()
        if self.method not in ("v0", "v1", "v1_all", "v1_auto"):
            raise ValueError(f"unknown segmentation method {self.method!r} (use 'v0', 'v1', 'v1_all' or 'v1_auto')")
        if self.method != "v0" and not (HAS_CV_SEGMENT and HAS_SAM2):
            print("    v1 needs cv_segment + SAM 2; falling back to v0")
            self.method = "v0"
        self._device: str = _resolve_device()
        self._sam2_model = None
        self._sam2_processor = None
        self._u2net_session = None
        self._sam2w = None
        print(f"    GarmentSegmentor: method = '{self.method}', device = '{self._device}'")

    # ── SAM 2 (v0 path) ──────────────────────────────────────────────────────

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
        One SAM 2 forward pass (v0).

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
        Segment using SAM 2 with a two-pass prompting strategy (v0).

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
        mask_binary = self._clean_mask(mask_binary, legacy=self.method == "v0")
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
            mask_binary = self._clean_mask(mask_binary, legacy=self.method == "v0")
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

    # ── U²-Net via rembg (v0 path) ───────────────────────────────────────────

    def _load_u2net(self):
        """Lazy-load rembg U²-Net session once. Subsequent calls are no-ops."""
        if self._u2net_session is not None:
            return
        if not HAS_U2NET:
            raise RuntimeError("U²-Net requires: pip install rembg onnxruntime")
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
        mask_binary = self._clean_mask(mask_binary, legacy=self.method == "v0")

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

    # ── v1: SegFormer region -> SAM 2 box + point -> minus skin ──────────────

    def _get_sam2w(self):
        if self._sam2w is None:
            print("    Loading SAM 2 (facebook/sam2-hiera-large) …")
            self._sam2w = cs.Sam2Wrapper(device=self._device).load()
        return self._sam2w

    def _segformer_labels(self, pil_img: Image.Image) -> Optional[np.ndarray]:
        """SegFormer clothes-parser label map, or None when the model is unavailable. The model is freed at once."""
        try:
            sf = cs.SegformerWrapper(device=self._device).load()
        except Exception as e:  # noqa: BLE001
            print(f"    SegFormer unavailable ({e})")
            return None
        try:
            return sf.labels(pil_img)
        finally:
            sf.unload()

    def _salient_box(self, pil_img: Image.Image) -> Optional[list]:
        """Box of the RMBG-1.4 salient object (fallback when SegFormer finds no garment)."""
        try:
            sw = cs.SalientWrapper(device=self._device).load()
        except Exception as e:  # noqa: BLE001
            print(f"    RMBG-1.4 unavailable ({e})")
            return None
        try:
            soft = sw.soft(pil_img)
        finally:
            sw.unload()
        return cs.bbox_of(cs.largest_component(cs.to_u8(soft > 127)))

    @staticmethod
    def _interior_point(mask: np.ndarray) -> list:
        dt = cv2.distanceTransform(cs.to_u8(mask), cv2.DIST_L2, 5)
        y, x = np.unravel_index(int(np.argmax(dt)), dt.shape)
        return [int(x), int(y)]

    def segment_v1(self, image_path: str) -> SegmentationResult:
        """
        1. SegFormer (sayeed99/segformer_b3_clothes) labels the photo. Garment region g = Upper-clothes + Dress
           (v1; Skirt is added when that is < 0.5 % of the image) or Upper-clothes + Dress + Skirt (v1_all).
        2. Box = bbox of the largest connected component of g; point = the pixel of that component farthest
           from its border (one positive point).
           If SegFormer finds < 0.5 % garment, the box comes from RMBG-1.4's salient object and the point is the
           image centre (fallback).
        3. SAM 2 with box + point, single-mask output.
        4. v1_all only: pixels SegFormer labels as face, hair, arms or legs are removed from the mask.
        5. Open/close, largest component, fill holes smaller than 2 % of the garment.
        Returns an invalid result when the area is outside 5-95 % so segment() falls back to the v0 chain.
        """
        pil_img = Image.open(image_path).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        H, W = bgr.shape[:2]
        details: dict = {}
        use_all = self.method == "v1_all"

        labels = self._segformer_labels(pil_img)
        if self.method == "v1_auto":
            if labels is not None:
                use_all, auto_info = cs.auto_skirt_decision(labels)
                details["auto"] = {**auto_info, "use_all": use_all}
        garment = None
        if labels is not None:
            garment = cs.to_u8(np.isin(labels, cs.SEG_GARMENT_ALL if use_all else cs.SEG_GARMENT_TOP))
            if garment.sum() < 0.005 * garment.size:
                garment = cs.to_u8(np.isin(labels, cs.SEG_GARMENT_ALL))
        box = point = None
        if garment is not None and garment.sum() >= 0.005 * garment.size:
            lc = cs.largest_component(garment)
            box = cs.bbox_of(lc)
            point = self._interior_point(lc)
            details["prompt"] = "segformer_box+interior_point"
        else:
            box = self._salient_box(pil_img)
            point = [W // 2, H // 2]
            details["prompt"] = "rmbg_box+centre_point (fallback)"
        if box is None or box[2] <= box[0] or box[3] <= box[1]:
            return SegmentationResult(is_valid=False, method=self.method, message="no box from SegFormer or RMBG")
        details["box"], details["point"] = [int(v) for v in box], point

        sam = self._get_sam2w()
        sam.set_image(pil_img)
        masks, scores = sam.predict(points=[point], labels=[1], box=box, multimask=False)
        sam_iou = float(scores[0])
        raw_mask = cs.to_u8(masks[0])
        mask = raw_mask
        holes_before = cs.count_holes(cs.largest_component(raw_mask))[0]
        if use_all and labels is not None:
            mask = cs.sam2_minus_skin(mask, labels)
        mask = self._clean_mask(mask)
        area_pct = float(np.sum(mask > 0) / mask.size * 100)
        # A parser-prompted mask may legitimately be small: a top in a full-body model photo covers 2-5 % of the
        # image (found on DeepFashion In-shop photos, CV plan P10). The 5 % floor was meant for v0's centre point,
        # where a tiny mask usually means SAM 2 picked the print; it stays for the RMBG/centre-point fallback.
        min_area = V1_MIN_AREA_PCT if details["prompt"].startswith("segformer") else 5.0
        is_valid = min_area <= area_pct <= 95.0

        agreement = cs.iou(mask, garment) if garment is not None and garment.any() else None
        rgba = np.dstack([np.array(pil_img), mask])
        res = SegmentationResult(
            rgba_image=rgba, mask=mask, area_percent=area_pct, is_valid=is_valid, method=self.method,
            message="OK" if is_valid else f"Area {area_pct:.1f}% outside {min_area:g}–95%", details=details)
        res._signals = {"sam_iou": sam_iou, "agreement_iou": agreement, "holes_before_fill": holes_before}  # type: ignore[attr-defined]
        return res

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def segment(self, image_path: str) -> SegmentationResult:
        """Run segmentation with the selected method (default v1; v1 falls back to v0)."""
        if self.method in ("v1", "v1_all", "v1_auto"):
            try:
                result = self.segment_v1(image_path)
            except Exception as e:  # noqa: BLE001
                print(f"    ⚠  {self.method} failed ({e}), falling back to the v0 chain …")
                result = SegmentationResult(is_valid=False, method=self.method, message=str(e))
            if result.is_valid:
                return self._finalize_result(result, image_path)
            print(f"    ⚠  {self.method} invalid ({result.message}), falling back to the v0 chain …")
        return self._segment_v0_chain(image_path)

    def _segment_v0_chain(self, image_path: str) -> SegmentationResult:
        """The original SAM 2 → U²-Net fallback chain."""
        legacy = self.method == "v0"
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
        pil_img = Image.open(image_path).convert("RGB")
        rgb = np.array(pil_img)
        if self.method == "v0":
            quality_score, quality_metrics = GarmentSegmentor._compute_quality_v0(result.mask)
        else:
            sig = getattr(result, "_signals", {})
            quality_score, quality_metrics = cs.compute_quality(
                result.mask, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), **sig)
            # keep the v0 key names that other code reads
            quality_metrics.setdefault("edge_sharpness_score", quality_metrics.get("edge_alignment"))
        result.quality_score = quality_score
        result.quality_metrics = quality_metrics
        result.rgba_feathered = GarmentSegmentor._feather_mask(result.mask, rgb)
        if HAS_CV_SEGMENT:
            try:
                poly, _ = cs.mask_to_outline(result.mask)
                result.outline_polygon = poly.tolist()
            except Exception:  # noqa: BLE001
                pass

        print(
            f"    Quality: {quality_score:.3f} "
            f"(coverage={quality_metrics['area_percent']:.1f}%, "
            f"edge={quality_metrics.get('edge_sharpness_score')}, "
            f"holes={quality_metrics['hole_count']})"
        )
        return result

    # ── Shared utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _clean_mask(mask: np.ndarray, legacy: bool = False) -> np.ndarray:
        """Morphological open + close → largest component → fill holes.

        legacy=True is the v0 behaviour (flood fill from pixel (0, 0), every hole filled).
        Otherwise only holes smaller than 2 % of the garment are filled (B5 fix).
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = GarmentSegmentor._keep_largest_component(mask)
        if legacy:
            return GarmentSegmentor._fill_holes_legacy(mask)
        return GarmentSegmentor._fill_holes(mask, max_frac=0.02)

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
    def _fill_holes_legacy(mask: np.ndarray) -> np.ndarray:
        """v0 hole filling: flood fill the inverted mask from pixel (0, 0).

        Known bug B5: when the garment touches the top-left corner that pixel is garment,
        nothing is flooded, and every background pixel stays "hole" and is OR-ed into the mask.
        """
        inverted = cv2.bitwise_not(mask)
        flooded = inverted.copy()
        h, w = flooded.shape
        flood_mask = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(flooded, flood_mask, (0, 0), 0)
        return cv2.bitwise_or(mask, flooded)

    @staticmethod
    def _fill_holes(mask: np.ndarray, max_frac: Optional[float] = None) -> np.ndarray:
        """Fill enclosed holes of a binary mask (B5 fixed).

        The mask is padded with a 1-px background border first, so the outside background is always one
        connected region (a garment touching the corner no longer floods the background).
        max_frac: fill only holes up to this share of the garment area (the cleaning uses 0.02);
        None fills every enclosed hole.
        """
        if max_frac is None:
            max_frac = float("inf")
        if cs is not None:
            return cs.fill_small_holes(mask, max_frac)
        padded = np.pad(mask, 1, constant_values=0)
        flooded = cv2.bitwise_not(padded)
        cv2.floodFill(flooded, np.zeros((flooded.shape[0] + 2, flooded.shape[1] + 2), np.uint8), (0, 0), 0)
        return cv2.bitwise_or(padded, flooded)[1:-1, 1:-1]

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
    def _compute_quality(mask: np.ndarray, bgr: Optional[np.ndarray] = None) -> tuple[float, dict]:
        """Quality score and the six classic keys, with B6/B7 fixed.

        edge_sharpness_score  = share of the mask boundary lying on a Canny edge of the photo (needs `bgr`;
                                0.0 without a photo). The v0 value was measured on the binary mask itself
                                and was always ~1.0 (B6).
        hole_count            = enclosed holes (>= 50 px) only; the outside background is not a hole (B7).
        The richer signals (SAM 2 predicted IoU, border-touch ratio, agreement of two methods) are added to
        result.quality_metrics by _finalize_result.
        """
        score, m = cs.compute_quality(mask, bgr)
        edge = m["edge_alignment"] if m["edge_alignment"] is not None else 0.0
        return score, {
            "area_percent":         m["area_percent"],
            "coverage_score":       m["coverage_score"],
            "edge_sharpness_score": edge,
            "hole_count":           m["holes_before_fill"],
            "hole_penalty":         m["hole_penalty"],
            "quality_score":        m["quality_score"],
        }

    @staticmethod
    def _compute_quality_v0(mask: np.ndarray) -> tuple[float, dict]:
        """The original v0 quality score, kept unchanged for before/after comparisons.

        Known flaws: edge_sharpness_score is computed on the binary mask (always ~1.0, B6) and hole_count
        counts the outside background as a hole (always >= 1, B7).
        """
        area_pct = float(np.sum(mask > 0) / max(1, mask.size) * 100)
        if 10.0 <= area_pct <= 80.0:
            coverage_score = 1.0
        elif area_pct < 10.0:
            coverage_score = area_pct / 10.0
        else:
            coverage_score = max(0.0, (95.0 - area_pct) / 15.0)

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
            edge_sharpness_score = 0.0 if area_pct < 1.0 else 1.0

        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(mask), connectivity=8
        )
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


def run_segmentation(image_path: str | Path, method: Optional[str] = None) -> tuple[SegmentationResult, bool]:
    """Public entry point: segment the garment and validate edge transparency.

    method: "v1" (default), "v1_auto", "v1_all" or "v0" (the original pipeline); also selectable with MIRRA_SEG_METHOD.
    """
    segmentor = GarmentSegmentor(method=method)
    result = segmentor.segment(str(image_path))
    transparent_bg_ok = bool(
        result.rgba_image is not None and validate_transparent_bg(result.rgba_image)
    )
    return result, transparent_bg_ok
