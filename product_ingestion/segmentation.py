"""Step 1: Segmentation

# ═══════════════════════════════════════════════════════════════
#  STAGE 1 — SEGMENTATION
# ═══════════════════════════════════════════════════════════════

"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import cv2

try:
    import torch
    from transformers import AutoModelForImageSegmentation
    HAS_RMBG = True
except Exception:
    HAS_RMBG = False


@dataclass
class SegmentationResult:
    """Result from Stage 1: Segmentation."""
    rgba_image: Optional[np.ndarray] = None  # H×W×4  RGBA
    mask: Optional[np.ndarray] = None        # H×W    uint8 (0/255)
    area_percent: float = 0.0
    is_valid: bool = False
    method: str = ""
    message: str = ""


class GarmentSegmentor:
    """
    Isolates the T-shirt from background (and human body).

    Primary method : RMBG-1.4 (briaai/RMBG-1.4)
    Fallback       : GrabCut + morphological cleanup
    """

    def __init__(self):
        self._rmbg_model = None

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
        pred = output
        while isinstance(pred, (list, tuple)):
            pred = pred[0]
        pred = pred.squeeze()
        if pred.dim() == 3:
            pred = pred[0]
        pred = pred.cpu().float().numpy()

        mask_resized = cv2.resize(pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel, iterations=2)
        mask_binary = cv2.morphologyEx(mask_binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        mask_binary = self._keep_largest_component(mask_binary)

        orig_np = np.array(pil_img)
        rgba = np.dstack([orig_np, mask_binary])

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

    def segment(self, image_path: str) -> SegmentationResult:
        """Try RMBG-1.4 first, fall back to GrabCut."""
        if HAS_RMBG:
            result = self.segment_rmbg(image_path)
            if result.is_valid:
                return result
            print(f"    ⚠️  RMBG result invalid ({result.message}), trying GrabCut …")

        return self.segment_grabcut(image_path)

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


def validate_transparent_bg(rgba: np.ndarray) -> bool:
    """Check that the image has a transparent background (alpha < 10 on edges)."""
    if rgba is None or rgba.shape[2] < 4:
        return False
    alpha = rgba[:, :, 3]
    edge_alpha = np.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
    return float(np.mean(edge_alpha)) < 50


def run_segmentation(image_path: str | Path) -> tuple[SegmentationResult, bool]:
    """Segment the selected cloth image and report edge transparency validity."""
    segmentor = GarmentSegmentor()
    result = segmentor.segment(str(image_path))
    transparent_bg_ok = bool(result.rgba_image is not None and validate_transparent_bg(result.rgba_image))
    return result, transparent_bg_ok
