"""Garment segmentation helpers for the CV project (plan P01).

Everything here is plain functions plus small model wrappers, so that both the
pipeline (`step_02_0_segmentation.py`) and the experiment scripts
(`CV/scripts/p01_*.py`) use the same code.

Contents
  * mask utilities        clean_mask / fill_small_holes (B5 fix) / largest_component / bbox_of / iou
  * model wrappers        Sam2Wrapper, SegformerWrapper, SalientWrapper (BRIA RMBG-1.4),
                          YoloWrapper (person masks), YoloeWrapper (text prompts), GDinoWrapper
  * classical methods     grabcut_box, grabcut_refine, kmeans_region, meanshift_region,
                          region_growing, mrf_smooth
  * combinations          sam2_minus_skin, weighted_vote
  * quality signals       compute_quality (replaces the old always-1.0 sharpness and hole count)
  * outline               mask_to_outline (smoothed, simplified polygon)

No model is loaded at import time. Every wrapper has `.load()` and `.unload()`.
"""
from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# SegFormer (sayeed99/segformer_b3_clothes) label ids
SEG_LABELS = {0: "Background", 1: "Hat", 2: "Hair", 3: "Sunglasses", 4: "Upper-clothes", 5: "Skirt",
              6: "Pants", 7: "Dress", 8: "Belt", 9: "Left-shoe", 10: "Right-shoe", 11: "Face",
              12: "Left-leg", 13: "Right-leg", 14: "Left-arm", 15: "Right-arm", 16: "Bag", 17: "Scarf"}
SEG_GARMENT_TOP = (4, 7)            # Upper-clothes, Dress
SEG_GARMENT_ALL = (4, 5, 7)         # + Skirt (flat photos where the lower half is labelled Skirt)
SEG_SKIN = (2, 11, 12, 13, 14, 15)  # Hair, Face, legs, arms  (removed from a SAM 2 mask)


AUTO_SKIRT_MIN_FRAC = 0.01    # the largest Skirt component must cover >= 1 % of the image
AUTO_HEAD_MAX_FRAC = 0.01     # Face + Hair pixels below 1 % of the image = no head in the photo


def auto_skirt_decision(labels: np.ndarray) -> tuple[bool, dict]:
    """v1_auto rule (plan P15a): decide whether SegFormer's "Skirt" region belongs to the garment (use_all = True).

    A "Skirt" region counts as part of the garment when the photo shows no head, i.e. SegFormer finds Face + Hair
    on < 1 % of the image (flat product photos, and close-up photos of a top worn by a model that are cropped at the
    neck: SegFormer then labels the lower half of the top, for example a colour block, as "Skirt"). When a head is
    visible the person wears a real skirt, so the skirt is NOT part of the garment (the v1 TOP region is kept).
    Needs a Skirt component >= 1 % of the image; without one the answer is False (= plain v1).
    Returns (use_all, features).
    """
    n = float(labels.size)
    skirt = largest_component(to_u8(labels == 5)) > 0 if (labels == 5).any() else np.zeros(labels.shape, bool)
    skirt_frac = float(skirt.sum() / n)
    head_frac = float(np.isin(labels, (2, 11)).sum() / n)
    use_all = bool(skirt_frac >= AUTO_SKIRT_MIN_FRAC and head_frac < AUTO_HEAD_MAX_FRAC)
    return use_all, {"skirt_frac": round(skirt_frac, 4), "head_frac": round(head_frac, 4), "rule": "skirt_without_head"}


def pick_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def free_gpu() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


# ───────────────────────────── mask utilities ─────────────────────────────

def to_u8(mask: np.ndarray) -> np.ndarray:
    return (mask > 0).astype(np.uint8) * 255


def largest_component(mask: np.ndarray) -> np.ndarray:
    """uint8 0/255 in -> uint8 0/255 with only the largest 8-connected component."""
    m = to_u8(mask)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return m
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return ((labels == idx) * 255).astype(np.uint8)


def count_holes(mask: np.ndarray, min_area: int = 50) -> tuple[int, list[int]]:
    """Enclosed background regions (holes) of a 0/255 mask, counted BEFORE filling.

    The mask is padded with a 1 px background border so that the outside background is one
    component (label of the corner) and is never counted as a hole (fixes B7). Returns
    (count of holes with area >= min_area, their areas).
    """
    m = np.pad(to_u8(mask), 1, constant_values=0)
    inv = (m == 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    outside = labels[0, 0]
    areas = [int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n) if i != outside]
    return sum(1 for a in areas if a >= min_area), areas


def fill_small_holes(mask: np.ndarray, max_frac: float = 0.02) -> np.ndarray:
    """Fill enclosed holes smaller than `max_frac` of the garment area (B5 fix).

    The mask is padded with a 1 px background border before the flood fill, so a mask that
    touches the top-left corner no longer floods the background. Larger holes are kept
    (a real opening, for example a gap between an arm and the torso).
    """
    m = to_u8(mask)
    area = int((m > 0).sum())
    if area == 0:
        return m
    padded = np.pad(m, 1, constant_values=0)
    inv = (padded == 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    outside = labels[0, 0]
    out = padded.copy()
    limit = max_frac * area
    for i in range(1, n):
        if i != outside and stats[i, cv2.CC_STAT_AREA] <= limit:
            out[labels == i] = 255
    return out[1:-1, 1:-1]


def clean_mask(mask: np.ndarray, *, legacy_fill: bool = False, hole_frac: float = 0.02,
               open_close: bool = True) -> np.ndarray:
    """Open + close, keep the largest component, fill small holes.

    legacy_fill=True reproduces the v0 behaviour (flood fill from pixel (0, 0), fills every
    hole and floods the background when the garment touches the top-left corner).
    """
    m = to_u8(mask)
    if open_close:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k, iterations=2)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=2)
    m = largest_component(m)
    if legacy_fill:
        inv = cv2.bitwise_not(m)
        flooded = inv.copy()
        h, w = flooded.shape
        cv2.floodFill(flooded, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 0)
        return cv2.bitwise_or(m, flooded)
    return fill_small_holes(m, hole_frac)


def bbox_of(mask: np.ndarray, pad_frac: float = 0.0) -> Optional[list[int]]:
    ys, xs = np.nonzero(mask > 0)
    if len(xs) == 0:
        return None
    h, w = mask.shape[:2]
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    px, py = int((x1 - x0) * pad_frac), int((y1 - y0) * pad_frac)
    return [max(0, x0 - px), max(0, y0 - py), min(w - 1, x1 + px), min(h - 1, y1 + py)]


def iou(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a > 0, b > 0
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 1.0


def border_touch_ratio(mask: np.ndarray) -> float:
    """Share of the 4 image border lines covered by the mask (0 = garment fully inside the frame)."""
    m = mask > 0
    edge = np.concatenate([m[0], m[-1], m[:, 0], m[:, -1]])
    return float(edge.mean())


# ───────────────────────────── SAM 2 ─────────────────────────────

class Sam2Wrapper:
    """facebook/sam2-hiera-large through transformers. One image embedding, many prompts."""

    def __init__(self, model_id: str = "facebook/sam2-hiera-large", device: Optional[str] = None):
        self.model_id = model_id
        self.device = device or pick_device()
        self.model = None
        self.processor = None
        self._emb = None
        self._emb_key = None

    def load(self):
        if self.model is not None:
            return self
        from transformers import Sam2Model, Sam2Processor
        self.processor = Sam2Processor.from_pretrained(self.model_id)
        self.model = Sam2Model.from_pretrained(self.model_id).to(self.device).eval()
        return self

    def unload(self):
        self.model = None
        self.processor = None
        self._emb = None
        free_gpu()

    def set_image(self, pil_img):
        """Compute and keep the image embedding (the expensive part)."""
        import torch
        self._pil = pil_img
        inputs = self.processor(images=pil_img, return_tensors="pt")
        with torch.no_grad():
            self._emb = self.model.get_image_embeddings(inputs["pixel_values"].to(self.device))
        self._orig_size = inputs["original_sizes"]

    def predict(self, points=None, labels=None, box=None, multimask: bool = True):
        """Run the prompt encoder + mask decoder on the stored embedding.

        points: [[x, y], ...] pixel coords, labels: [1|0, ...]; box: [x0, y0, x1, y1] pixels.
        Returns (masks bool [n, H, W], predicted_iou [n]).
        """
        import torch
        kw = {}
        if points:
            kw["input_points"] = [[points]]
            kw["input_labels"] = [[labels]]
        if box is not None:
            kw["input_boxes"] = [[list(map(float, box))]]
        inputs = self.processor(images=self._pil, return_tensors="pt", **kw)
        inputs.pop("pixel_values", None)
        inputs = {k: (v.to(self.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model(image_embeddings=self._emb, multimask_output=multimask,
                             **{k: v for k, v in inputs.items() if k in ("input_points", "input_labels", "input_boxes")})
        masks = self.processor.post_process_masks(out.pred_masks.cpu(), self._orig_size, binarize=True)[0]
        scores = out.iou_scores.cpu().float().reshape(-1)
        masks = masks.reshape(-1, masks.shape[-2], masks.shape[-1]).numpy().astype(bool)
        return masks, scores.numpy()


# ───────────────────────────── SegFormer clothes parser ─────────────────────────────

class SegformerWrapper:
    def __init__(self, model_id: str = "sayeed99/segformer_b3_clothes", device: Optional[str] = None):
        self.model_id, self.device = model_id, device or pick_device()
        self.model = self.proc = None

    def load(self):
        if self.model is None:
            from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor
            self.proc = SegformerImageProcessor.from_pretrained(self.model_id)
            self.model = AutoModelForSemanticSegmentation.from_pretrained(self.model_id).to(self.device).eval()
        return self

    def unload(self):
        self.model = self.proc = None
        free_gpu()

    def labels(self, pil_img) -> np.ndarray:
        """Label map (uint8, H x W, ids in SEG_LABELS)."""
        import torch
        import torch.nn.functional as F
        inputs = self.proc(images=pil_img, return_tensors="pt")
        with torch.no_grad():
            logits = self.model(pixel_values=inputs["pixel_values"].to(self.device)).logits
        w, h = pil_img.size
        up = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
        return up.argmax(1)[0].cpu().numpy().astype(np.uint8)


def seg_mask(labels: np.ndarray, classes=SEG_GARMENT_TOP) -> np.ndarray:
    return to_u8(np.isin(labels, classes))


# ───────────────────────────── salient object (BRIA RMBG-1.4, U²-Net family) ─────────────────────────────

class SalientWrapper:
    """briaai/RMBG-1.4 (an IS-Net, same family as U²-Net). rembg's own U²-Net needs onnxruntime,
    which is not installed in the repo .venv, so this is the runnable salient-object model."""

    def __init__(self, model_id: str = "briaai/RMBG-1.4", device: Optional[str] = None):
        self.model_id, self.device = model_id, device or pick_device()
        self.model = None

    def load(self):
        if self.model is None:
            from transformers import AutoModelForImageSegmentation
            self.model = AutoModelForImageSegmentation.from_pretrained(self.model_id, trust_remote_code=True)
            self.model = self.model.to(self.device).eval()
        return self

    def unload(self):
        self.model = None
        free_gpu()

    def soft(self, pil_img) -> np.ndarray:
        """Foreground probability, uint8 H x W (0-255)."""
        import torch
        import torch.nn.functional as F
        w, h = pil_img.size
        arr = np.asarray(pil_img.convert("RGB").resize((1024, 1024), 2), dtype=np.float32) / 255.0
        t = torch.from_numpy(arr).permute(2, 0, 1)[None]
        t = (t - 0.5) / 1.0
        with torch.no_grad():
            out = self.model(t.to(self.device))
        res = out[0][0] if isinstance(out[0], (list, tuple)) else out[0]
        res = F.interpolate(res, size=(h, w), mode="bilinear", align_corners=False)[0, 0]
        res = res.float().cpu().numpy()
        res = (res - res.min()) / max(1e-6, res.max() - res.min())
        return (res * 255).astype(np.uint8)


# ───────────────────────────── YOLO (person) and YOLOE (text prompts) ─────────────────────────────

class YoloWrapper:
    def __init__(self, weights: str, device: Optional[str] = None):
        self.weights, self.device = weights, device or pick_device()
        self.model = None

    def load(self):
        if self.model is None:
            from ultralytics import YOLO
            self.model = YOLO(self.weights)
        return self

    def unload(self):
        self.model = None
        free_gpu()

    def person(self, bgr: np.ndarray):
        """Largest 'person' (COCO class 0) instance. Returns (mask uint8 0/255 | None, conf, box)."""
        r = self.model.predict(bgr, classes=[0], imgsz=640, retina_masks=True, device=self.device,
                               verbose=False, conf=0.25)[0]
        if r.masks is None or len(r.masks) == 0:
            return None, 0.0, None
        areas = r.masks.data.sum((1, 2)).cpu().numpy()
        i = int(np.argmax(areas))
        m = to_u8(r.masks.data[i].cpu().numpy())
        h, w = bgr.shape[:2]
        if m.shape != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        return m, float(r.boxes.conf[i]), r.boxes.xyxy[i].cpu().numpy().tolist()


class YoloeWrapper(YoloWrapper):
    """YOLOE: text-prompted open-vocabulary segmentation (`set_classes` with text embeddings)."""

    def __init__(self, weights: str, device: Optional[str] = None):
        super().__init__(weights, device)
        self._names = None

    def load(self):
        if self.model is None:
            from ultralytics import YOLOE
            self.model = YOLOE(self.weights)
        return self

    def set_prompts(self, names: list[str]):
        if self._names != names:
            self.model.set_classes(names, self.model.get_text_pe(names))
            self._names = list(names)

    def best(self, bgr: np.ndarray, conf: float = 0.05):
        """Highest-confidence instance. Returns (mask uint8 0/255 | None, conf, box, cls_name)."""
        r = self.model.predict(bgr, imgsz=640, retina_masks=True, device=self.device, verbose=False, conf=conf)[0]
        if r.masks is None or len(r.masks) == 0:
            return None, 0.0, None, ""
        i = int(np.argmax(r.boxes.conf.cpu().numpy()))
        m = to_u8(r.masks.data[i].cpu().numpy())
        h, w = bgr.shape[:2]
        if m.shape != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        return m, float(r.boxes.conf[i]), r.boxes.xyxy[i].cpu().numpy().tolist(), self._names[int(r.boxes.cls[i])]


# ───────────────────────────── Grounding DINO (text -> box) ─────────────────────────────

class GDinoWrapper:
    def __init__(self, model_id: str = "IDEA-Research/grounding-dino-tiny", device: Optional[str] = None):
        self.model_id, self.device = model_id, device or pick_device()
        self.model = self.proc = None

    def load(self):
        if self.model is None:
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
            self.proc = AutoProcessor.from_pretrained(self.model_id)
            self.model = AutoModelForZeroShotObjectDetection.from_pretrained(self.model_id).to(self.device).eval()
        return self

    def unload(self):
        self.model = self.proc = None
        free_gpu()

    def box(self, pil_img, text: str = "t-shirt.", box_thr: float = 0.25, text_thr: float = 0.2):
        """Best box for the text query. Returns (box xyxy pixels | None, score)."""
        import torch
        inputs = self.proc(images=pil_img, text=text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model(**inputs)
        w, h = pil_img.size
        res = self.proc.post_process_grounded_object_detection(
            out, inputs["input_ids"], threshold=box_thr, text_threshold=text_thr, target_sizes=[(h, w)])[0]
        if len(res["scores"]) == 0:
            return None, 0.0
        i = int(res["scores"].argmax())
        return res["boxes"][i].cpu().numpy().tolist(), float(res["scores"][i])


# ───────────────────────────── classical methods (syllabus Unit III) ─────────────────────────────

def _shrink(bgr: np.ndarray, max_side: int = 640):
    h, w = bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s == 1.0:
        return bgr, 1.0
    return cv2.resize(bgr, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA), s


def _up(mask_small: np.ndarray, shape) -> np.ndarray:
    return to_u8(cv2.resize(to_u8(mask_small), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST))


def grabcut_box(bgr: np.ndarray, box=None, iters: int = 5, margin: float = 0.08) -> np.ndarray:
    """GrabCut (graph cut with GMM colour models) initialised from a rectangle.
    Default rectangle: the image minus an 8 % margin (no detector)."""
    small, s = _shrink(bgr)
    h, w = small.shape[:2]
    if box is None:
        rect = (int(w * margin), int(h * margin), int(w * (1 - 2 * margin)), int(h * (1 - 2 * margin)))
    else:
        x0, y0, x1, y1 = [v * s for v in box]
        rect = (int(x0), int(y0), max(2, int(x1 - x0)), max(2, int(y1 - y0)))
    mask = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(0)
    try:
        cv2.grabCut(small, mask, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return np.zeros(bgr.shape[:2], np.uint8)
    return _up((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), bgr.shape[:2])


def grabcut_refine(bgr: np.ndarray, init_mask: np.ndarray, band_frac: float = 0.02, iters: int = 4) -> np.ndarray:
    """GrabCut border refinement: sure foreground = erode(mask), sure background = outside dilate(mask),
    the band in between (band_frac of the image diagonal on each side) is left to the graph cut."""
    small, s = _shrink(bgr)
    m = cv2.resize(to_u8(init_mask), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    if m.sum() == 0:
        return to_u8(init_mask)
    r = max(2, int(band_frac * np.hypot(*small.shape[:2])))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    sure_fg = cv2.erode(m, k) > 0
    maybe = cv2.dilate(m, k) > 0
    gc_mask = np.full(m.shape, cv2.GC_BGD, np.uint8)
    gc_mask[maybe] = cv2.GC_PR_BGD
    gc_mask[m > 0] = cv2.GC_PR_FGD
    gc_mask[sure_fg] = cv2.GC_FGD
    if not sure_fg.any() or (gc_mask == cv2.GC_BGD).sum() < 50:
        return to_u8(init_mask)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.setRNGSeed(0)
    try:
        cv2.grabCut(small, gc_mask, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return to_u8(init_mask)
    out = _up((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), bgr.shape[:2])
    return out


def _centre_patch(shape, frac: float = 0.15):
    h, w = shape[:2]
    return slice(int(h * (0.5 - frac)), int(h * (0.5 + frac))), slice(int(w * (0.5 - frac)), int(w * (0.5 + frac)))


def kmeans_region(bgr: np.ndarray, k: int = 4, seed: int = 0) -> np.ndarray:
    """K-means colour clustering (Lab + a weak spatial term); the garment is the cluster that
    occupies most of the central patch, then the largest connected region."""
    small, s = _shrink(bgr, 320)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    feats = np.dstack([lab, 0.15 * xx / w * 255, 0.15 * yy / h * 255]).reshape(-1, 5)
    cv2.setRNGSeed(seed)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lab_idx, _ = cv2.kmeans(feats, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    lab_idx = lab_idx.reshape(h, w)
    ys, xs = _centre_patch((h, w))
    c = int(np.bincount(lab_idx[ys, xs].ravel(), minlength=k).argmax())
    return _up(largest_component(to_u8(lab_idx == c)), bgr.shape[:2])


def meanshift_region(bgr: np.ndarray, sp: int = 12, sr: int = 22, k: int = 4, seed: int = 0) -> np.ndarray:
    """Mean-shift filtering (cv2.pyrMeanShiftFiltering, edge-preserving smoothing into flat colour
    regions), then colour quantisation with K-means on the filtered image; garment = cluster of the
    central patch -> largest connected region."""
    small, s = _shrink(bgr, 320)
    ms = cv2.pyrMeanShiftFiltering(small, sp, sr, maxLevel=2)
    lab = cv2.cvtColor(ms, cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
    cv2.setRNGSeed(seed)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, idx, _ = cv2.kmeans(lab, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    h, w = small.shape[:2]
    idx = idx.reshape(h, w)
    ys, xs = _centre_patch((h, w))
    c = int(np.bincount(idx[ys, xs].ravel(), minlength=k).argmax())
    return _up(largest_component(to_u8(idx == c)), bgr.shape[:2])


def region_growing(bgr: np.ndarray, tol: tuple[int, int, int] = (22, 9, 9)) -> np.ndarray:
    """Region growing from a seed at the image centre: 4-connected neighbours join while their
    Lab colour stays within `tol` of the seed colour (cv2.floodFill, fixed range)."""
    small, s = _shrink(bgr, 480)
    small = cv2.GaussianBlur(small, (5, 5), 0)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    h, w = lab.shape[:2]
    ys, xs = _centre_patch((h, w), 0.03)
    seed_col = np.median(lab[ys, xs].reshape(-1, 3), 0).astype(np.uint8)
    lab[ys, xs] = seed_col
    msk = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | cv2.FLOODFILL_FIXED_RANGE | cv2.FLOODFILL_MASK_ONLY | (255 << 8)
    cv2.floodFill(lab, msk, (w // 2, h // 2), 0, tol, tol, flags)
    return _up(msk[1:-1, 1:-1] > 0, bgr.shape[:2])


def mrf_smooth(prob: np.ndarray, bgr: np.ndarray, iters: int = 12, lam: float = 1.6, sigma: float = 18.0) -> np.ndarray:
    """MRF smoothing of a foreground probability map (mean-field inference of a Potts model whose
    neighbour weights fall with the colour difference, so the border snaps to image edges).

    prob: float 0..1 (or uint8 0..255) H x W; returns uint8 0/255.
    """
    if prob.dtype != np.float32:
        p = prob.astype(np.float32)
        if p.max() > 1.5:
            p /= 255.0
    else:
        p = prob
    small, s = _shrink(bgr, 480)
    h, w = small.shape[:2]
    p = cv2.resize(p, (w, h), interpolation=cv2.INTER_AREA)
    img = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    eps = 1e-3
    unary = np.log((p + eps) / (1 - p + eps))          # log-odds from the data term
    def w_pair(a, b):
        d = ((a - b) ** 2).sum(-1)
        return np.exp(-d / (2 * sigma ** 2))
    wr = np.zeros((h, w), np.float32); wr[:, :-1] = w_pair(img[:, :-1], img[:, 1:])
    wl = np.zeros((h, w), np.float32); wl[:, 1:] = wr[:, :-1]
    wd = np.zeros((h, w), np.float32); wd[:-1] = w_pair(img[:-1], img[1:])
    wu = np.zeros((h, w), np.float32); wu[1:] = wd[:-1]
    q = p.copy()
    for _ in range(iters):
        s_ = 2 * q - 1
        msg = np.zeros_like(q)
        msg[:, :-1] += wr[:, :-1] * s_[:, 1:]
        msg[:, 1:] += wl[:, 1:] * s_[:, :-1]
        msg[:-1] += wd[:-1] * s_[1:]
        msg[1:] += wu[1:] * s_[:-1]
        q = 1 / (1 + np.exp(-(unary + 2 * lam * msg)))
    return _up(q > 0.5, bgr.shape[:2])


# ───────────────────────────── combinations ─────────────────────────────

def sam2_minus_skin(mask: np.ndarray, seg_labels: np.ndarray, classes=SEG_SKIN) -> np.ndarray:
    """SAM 2 mask minus the pixels SegFormer labels as arms, legs, face or hair."""
    return to_u8((mask > 0) & ~np.isin(seg_labels, classes))


def weighted_vote(masks: list[np.ndarray], weights: list[float], thr: float = 0.5) -> np.ndarray:
    """Confidence-weighted majority vote: pixel is garment when the weight share voting for it exceeds `thr`."""
    ws = np.array(weights, np.float32)
    ws = ws / max(ws.sum(), 1e-6)
    acc = np.zeros(masks[0].shape, np.float32)
    for m, w in zip(masks, ws):
        acc += w * (m > 0)
    return to_u8(acc > thr)


# ───────────────────────────── SAM 2 candidate rules ─────────────────────────────

def pick_candidate(masks: np.ndarray, scores: np.ndarray, rule: str = "iou",
                   other: Optional[np.ndarray] = None, max_border: float = 0.25) -> int:
    """Choose one of the multimask candidates.

    iou       highest predicted IoU (v0)
    largest_inside  largest candidate whose border-touch ratio < max_border and area < 85 % of the image
    agree     highest IoU with `other` (a mask from another model)
    """
    n = len(masks)
    if rule == "iou" or n == 1:
        return int(np.argmax(scores))
    areas = masks.reshape(n, -1).sum(1)
    if rule == "largest_inside":
        ok = [i for i in range(n) if border_touch_ratio(masks[i]) < max_border and areas[i] < 0.85 * masks[0].size]
        if not ok:
            return int(np.argmax(scores))
        return int(max(ok, key=lambda i: areas[i]))
    if rule == "agree" and other is not None:
        return int(np.argmax([iou(masks[i], other) for i in range(n)]))
    return int(np.argmax(scores))


# ───────────────────────────── quality signals ─────────────────────────────

def compute_quality(mask: np.ndarray, bgr: Optional[np.ndarray] = None, *, sam_iou: Optional[float] = None,
                    agreement_iou: Optional[float] = None, holes_before_fill: Optional[int] = None) -> tuple[float, dict]:
    """Meaningful quality signals (replaces the v0 score, whose sharpness was ~1.0 and hole count 1 always).

    area_percent            share of the image covered by the mask
    coverage_score          1 inside [10 %, 80 %] and falling outside
    border_touch_ratio      share of the image border covered by the mask (a cut-off garment or a mask that
                            swallowed the background scores high)
    holes_before_fill       enclosed holes >= 50 px counted before filling (outside background not counted)
    edge_alignment          share of mask-boundary pixels that lie within 2 px of a Canny edge of the PHOTO
                            (the v0 sharpness was measured on the binary mask itself, so it was always ~1)
    sam_pred_iou            SAM 2's own predicted IoU of the chosen mask (None when SAM 2 was not used)
    agreement_iou           IoU between this mask and a second method's mask (None when there is none)
    quality_score           coverage_score x mean of the available terms (1 - 4 x border_touch_ratio, edge_alignment,
                            agreement_iou, sam_pred_iou), each in [0, 1]
    """
    m = to_u8(mask)
    area_pct = float((m > 0).sum() / max(1, m.size) * 100)
    if 10.0 <= area_pct <= 80.0:
        coverage = 1.0
    elif area_pct < 10.0:
        coverage = area_pct / 10.0
    else:
        coverage = max(0.0, (95.0 - area_pct) / 15.0)
    btr = border_touch_ratio(m)
    n_holes = holes_before_fill if holes_before_fill is not None else count_holes(m)[0]
    edge_align = None
    if bgr is not None and m.any():
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        v = np.median(gray)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), int(max(0, 0.66 * v)), int(min(255, 1.33 * v) + 30)) > 0
        near = cv2.dilate(edges.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        bnd = (m > 0) ^ (cv2.erode(m, np.ones((3, 3), np.uint8)) > 0)
        # image border pixels are not real edges
        bnd[0, :] = bnd[-1, :] = False
        bnd[:, 0] = bnd[:, -1] = False
        edge_align = float(near[bnd].mean()) if bnd.any() else 0.0
    terms = [1.0 - min(1.0, btr * 4.0)]
    if edge_align is not None:
        terms.append(edge_align)
    if agreement_iou is not None:
        terms.append(agreement_iou)
    if sam_iou is not None:
        terms.append(float(np.clip(sam_iou, 0, 1)))
    # coverage multiplies: an empty or tiny mask can never score high whatever the other terms say
    score = float(coverage * np.mean(terms))
    metrics = {
        "area_percent": round(area_pct, 2),
        "coverage_score": round(coverage, 3),
        "border_touch_ratio": round(btr, 4),
        "holes_before_fill": int(n_holes),
        "hole_count": int(n_holes),
        "edge_alignment": None if edge_align is None else round(edge_align, 3),
        "edge_sharpness_score": None if edge_align is None else round(edge_align, 3),
        "sam_pred_iou": None if sam_iou is None else round(float(sam_iou), 3),
        "agreement_iou": None if agreement_iou is None else round(float(agreement_iou), 3),
        "hole_penalty": round(min(1.0, n_holes / 10.0), 3),
        "quality_score": round(score, 3),
    }
    return score, metrics


# ───────────────────────────── outline ─────────────────────────────

def mask_to_outline(mask: np.ndarray, smooth_px: float = 0.004, simplify_frac: float = 0.0015):
    """Garment outline from the mask contour.

    1. the mask is smoothed (Gaussian on the 0/255 mask, re-thresholded) with sigma = smooth_px * diagonal,
    2. the largest external contour is taken,
    3. it is simplified with Douglas-Peucker (epsilon = simplify_frac * contour length... of the diagonal).

    Returns (polygon Nx2 int array in pixel coordinates, dense contour Mx2).
    """
    m = to_u8(mask)
    h, w = m.shape
    sigma = max(1.0, smooth_px * np.hypot(h, w))
    sm = cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigma) > 127
    cnts, _ = cv2.findContours(sm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return np.zeros((0, 2), int), np.zeros((0, 2), int)
    c = max(cnts, key=cv2.contourArea)
    eps = simplify_frac * np.hypot(h, w)
    poly = cv2.approxPolyDP(c, eps, True)
    return poly[:, 0, :], c[:, 0, :]


def draw_outline(bgr: np.ndarray, polygon: np.ndarray, colour=(0, 255, 255), thickness: int = 3, dots: bool = True):
    out = bgr.copy()
    if len(polygon) > 2:
        cv2.polylines(out, [polygon.reshape(-1, 1, 2).astype(np.int32)], True, colour, thickness, cv2.LINE_AA)
        if dots:
            for x, y in polygon:
                cv2.circle(out, (int(x), int(y)), thickness + 1, (0, 0, 255), -1, cv2.LINE_AA)
    return out


def overlay(bgr: np.ndarray, mask: np.ndarray, colour=(0, 200, 0), alpha: float = 0.45) -> np.ndarray:
    out = bgr.copy().astype(np.float32)
    m = mask > 0
    out[m] = out[m] * (1 - alpha) + np.array(colour, np.float32) * alpha
    cnts, _ = cv2.findContours(to_u8(mask), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = out.astype(np.uint8)
    cv2.drawContours(out, cnts, -1, (0, 255, 255), 2)
    return out
