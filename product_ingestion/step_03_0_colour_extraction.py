"""Step 3 of product_ingestion: colour extraction (K-Means in LAB).

Determines the dominant garment colour using K-Means clustering
in the perceptually uniform LAB colour space.

Improvements over the original:
  1. Float32 LAB conversion  — no precision loss from 8-bit rounding.
  2. Skin-tone exclusion     — HSV filter removes skin pixels before clustering
                                so they don't pollute garment colour.
  3. Adaptive K              — silhouette score picks the best K (2–8) instead
                                of always using K=5.
  4. Weighted voting         — base colour is the biggest cluster that isn't
                                near-white or near-black, instead of blindly
                                picking the mid-lightness cluster.
  5. CLO3D hex output        — a separate `clo3d_hex` field with uppercase hex
                                in "#RRGGBB" format compatible with CLO3D.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import cv2

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ─────────────────────────────────────────────────────────────────────────────
#  Skin-tone HSV range
# ─────────────────────────────────────────────────────────────────────────────
#  These cover the typical range of human skin tones in HSV space.
#  We use TWO ranges because skin can appear slightly reddish or yellowish.
#
#  Think of it as a colour filter:
#    - Hue 0–25   → reddish/orange skin
#    - Hue 330–360 → pinkish skin (wraps around)
#    - Saturation 20–170 → not too grey, not too vivid
#    - Value 80–255 → not too dark
#
#  Any pixel that falls inside these ranges gets removed before clustering.

_SKIN_LOWER_1 = np.array([0,   20,  80], dtype=np.uint8)
_SKIN_UPPER_1 = np.array([25, 170, 255], dtype=np.uint8)
_SKIN_LOWER_2 = np.array([165, 20,  80], dtype=np.uint8)   # 330°/2 = 165
_SKIN_UPPER_2 = np.array([180, 170, 255], dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColorInfo:
    """Information about a single extracted colour."""
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]
    hex_code: str          # lowercase "#rrggbb"
    clo3d_hex: str         # uppercase "#RRGGBB" — CLO3D compatible
    percentage: float
    role: str = ""         # "fabric" | "print" (v1 engine; empty for v0)

    def to_dict(self) -> dict:
        d = {
            "rgb": list(self.rgb),
            "lab": [round(v, 2) for v in self.lab],
            "hex": self.hex_code,
            "clo3d_hex": self.clo3d_hex,
            "percentage": round(self.percentage, 2),
        }
        if self.role:
            d["role"] = self.role
        return d


@dataclass
class ColourResult:
    """Result from Stage 3: Colour Extraction."""
    base_colour_hex: str = "#000000"        # lowercase — existing API
    clo3d_base_hex: str = "#000000"         # uppercase — for CLO3D
    palette: List[ColorInfo] = field(default_factory=list)
    k_used: int = 0                         # how many clusters were used
    skin_pixels_removed: int = 0            # how many skin pixels were filtered out
    success: bool = False
    message: str = ""
    # --- added by the v1 engine (CV project P04); all optional ---
    palette_roles: list = field(default_factory=list)   # [{"hex","share","role"}] sorted by share
    fabric_colours: list = field(default_factory=list)  # hex of every fabric colour (colour blocks), largest first
    region_map: dict = field(default_factory=dict)      # small JSON-serialisable summary of the colour regions
    label_map: object = field(default=None, repr=False)  # (H, W) int array, -1 = not garment; NOT for JSON
    method: str = ""

    def extra_json(self) -> dict:
        """Small JSON-safe dict with the new fields (the runner may merge it into colors.json)."""
        return {"method": self.method, "palette_roles": self.palette_roles,
                "fabric_colours": self.fabric_colours, "region_map": self.region_map}


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rgb_to_hex_lower(rgb: Tuple[int, int, int]) -> str:
    """RGB → '#rrggbb' (lowercase, existing format)."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _rgb_to_hex_upper(rgb: Tuple[int, int, int]) -> str:
    """RGB → '#RRGGBB' (uppercase, CLO3D format)."""
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _is_near_white_or_black(lab: Tuple[float, float, float]) -> bool:
    """
    Check if a LAB colour is near-white or near-black.

    In LAB:
      L = 0   → pure black
      L = 100 → pure white

    We treat L < 15 as "near black" and L > 85 as "near white".
    These are typically shadows/highlights on the garment, not the actual
    fabric colour.
    """
    return lab[0] < 15.0 or lab[0] > 85.0


def _remove_skin_pixels(rgb_pixels: np.ndarray) -> tuple[np.ndarray, int]:
    """
    Remove pixels that look like skin.

    How it works:
      1. Convert RGB pixels to HSV colour space.
         (HSV separates colour (Hue) from brightness (Value), making it
          easier to identify skin tones regardless of lighting.)
      2. Check if each pixel's Hue/Saturation/Value falls within known
         skin-tone ranges.
      3. Remove those pixels.

    Returns the filtered pixels and the count of removed pixels.
    """
    # cv2.cvtColor needs a 2D image shape: (N, 1, 3)
    # cv2.inRange also needs the same shape to match the boundary arrays.
    hsv_2d = cv2.cvtColor(
        rgb_pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_RGB2HSV,
    )  # shape: (N, 1, 3) — keep this shape for inRange

    # Build a mask: True = skin pixel
    skin_mask_1 = cv2.inRange(hsv_2d, _SKIN_LOWER_1, _SKIN_UPPER_1).flatten().astype(bool)
    skin_mask_2 = cv2.inRange(hsv_2d, _SKIN_LOWER_2, _SKIN_UPPER_2).flatten().astype(bool)
    is_skin = skin_mask_1 | skin_mask_2

    removed = int(np.sum(is_skin))
    return rgb_pixels[~is_skin], removed


def _rgb_to_lab_float32(rgb_pixels: np.ndarray) -> np.ndarray:
    """
    Convert RGB pixels to LAB using float32 for better precision.

    The old code did:
      pixels.astype(np.uint8) → cv2.cvtColor → float32
    This loses precision because uint8 only has 256 levels.

    The new code:
      pixels → float32 [0..1] → cv2.cvtColor → LAB
    cv2 treats float32 input as [0..1] range and returns full-precision LAB.
    """
    pixels_f32 = rgb_pixels.astype(np.float32) / 255.0
    lab = cv2.cvtColor(
        pixels_f32.reshape(-1, 1, 3),
        cv2.COLOR_RGB2LAB,
    ).reshape(-1, 3)
    return lab


def _find_best_k(lab_pixels: np.ndarray, k_min: int = 2, k_max: int = 8) -> int:
    """
    Find the optimal number of clusters using the silhouette score.

    What is silhouette score?
      For each pixel, it measures:
        a) How similar it is to pixels in its own cluster.
        b) How different it is from pixels in the nearest other cluster.

      Score ranges from -1 to +1:
        +1  → clusters are well separated (good)
         0  → clusters overlap (meh)
        -1  → pixels are in the wrong cluster (bad)

    We try K = 2, 3, 4, ... 8 and pick the K with the highest score.
    This means a plain white t-shirt gets K=2 (white + shadow), while a
    tie-dye shirt might get K=7.

    To keep it fast, we subsample to 5000 pixels for the scoring step.
    """
    n = len(lab_pixels)
    if n < k_max:
        return min(n, k_min)

    # Subsample for speed — silhouette on 50k pixels is slow
    rng = np.random.default_rng(42)
    if n > 5000:
        sample_idx = rng.choice(n, 5000, replace=False)
        sample = lab_pixels[sample_idx]
    else:
        sample = lab_pixels

    best_k = k_min
    best_score = -1.0

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100)
        labels = km.fit_predict(sample)

        # silhouette_score needs at least 2 unique labels
        if len(set(labels)) < 2:
            continue

        score = silhouette_score(sample, labels, sample_size=min(2000, len(sample)))
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


# ─────────────────────────────────────────────────────────────────────────────
#  Main extractor
# ─────────────────────────────────────────────────────────────────────────────

class ColourExtractor:
    """
    Determines the dominant garment colour using K-Means clustering
    in the perceptually uniform LAB colour space.

    Improvements:
      - Float32 LAB for better precision
      - Skin-tone pixels are excluded before clustering
      - Adaptive K (silhouette score picks 2–8)
      - Base colour = largest cluster that isn't near-white/near-black
    """

    def __init__(self, max_samples: int = 50_000):
        self.max_samples = max_samples

    def extract(self, rgba_image: np.ndarray) -> ColourResult:
        """
        Extract dominant colour and palette from an RGBA garment image.

        Pipeline:
          1. Grab non-transparent pixels (alpha > 10).
          2. Remove skin-tone pixels.
          3. Subsample to max_samples for speed.
          4. Convert RGB → LAB (float32 precision).
          5. Find optimal K via silhouette score.
          6. Run K-Means with optimal K.
          7. Build palette; pick base colour via weighted voting.
        """
        if not HAS_SKLEARN:
            return ColourResult(success=False, message="scikit-learn not installed")

        if rgba_image is None or rgba_image.shape[2] < 4:
            return ColourResult(success=False, message="Invalid RGBA image")

        # ── Step 1: extract non-transparent pixels ────────────────────────
        # Pixels with alpha <= 10 are background (from segmentation stage).
        alpha = rgba_image[:, :, 3]
        mask = alpha > 10
        rgb_pixels = rgba_image[:, :, :3][mask]   # shape (N, 3)

        if len(rgb_pixels) < 2:
            return ColourResult(success=False, message="Not enough opaque pixels")

        # ── Step 2: remove skin-tone pixels ───────────────────────────────
        # When segmentation isn't perfect (e.g. neck/arms visible), skin
        # pixels can pull the colour toward beige/brown.  We filter them
        # out so only fabric pixels remain.
        rgb_pixels, skin_removed = _remove_skin_pixels(rgb_pixels)

        if len(rgb_pixels) < 2:
            return ColourResult(
                success=False,
                message="All pixels were filtered as skin — check segmentation",
            )

        # ── Step 3: subsample for performance ─────────────────────────────
        if len(rgb_pixels) > self.max_samples:
            idx = np.random.default_rng(42).choice(
                len(rgb_pixels), self.max_samples, replace=False
            )
            rgb_pixels = rgb_pixels[idx]

        # ── Step 4: convert to LAB (float32 for precision) ────────────────
        lab_pixels = _rgb_to_lab_float32(rgb_pixels)

        # ── Step 5: find optimal K ────────────────────────────────────────
        best_k = _find_best_k(lab_pixels)

        # ── Step 6: run K-Means with optimal K ───────────────────────────
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lab_pixels)

        # ── Step 7: build palette ─────────────────────────────────────────
        palette: List[ColorInfo] = []
        total = len(labels)

        for i in range(best_k):
            cluster_mask = labels == i
            pct = float(np.sum(cluster_mask) / total * 100)

            lab_center = kmeans.cluster_centers_[i]
            # Use mean of original RGB pixels in this cluster (more accurate
            # than converting the LAB center back, which can clip).
            mean_rgb = tuple(int(v) for v in np.mean(rgb_pixels[cluster_mask], axis=0))

            palette.append(ColorInfo(
                rgb=mean_rgb,
                lab=tuple(float(v) for v in lab_center),
                hex_code=_rgb_to_hex_lower(mean_rgb),
                clo3d_hex=_rgb_to_hex_upper(mean_rgb),
                percentage=pct,
            ))

        # ── Pick base colour via weighted voting ─────────────────────────
        # Sort by percentage (largest first).
        # Pick the first cluster that is NOT near-white and NOT near-black.
        # If every cluster is near-white/black (unlikely), just take the
        # biggest one.
        palette.sort(key=lambda c: c.percentage, reverse=True)

        base_colour = palette[0]  # default: biggest cluster
        for entry in palette:
            if not _is_near_white_or_black(entry.lab):
                base_colour = entry
                break

        return ColourResult(
            base_colour_hex=base_colour.hex_code,        # existing API
            clo3d_base_hex=base_colour.clo3d_hex,        # CLO3D output
            palette=palette,
            k_used=best_k,
            skin_pixels_removed=skin_removed,
            success=True,
            message="OK",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Public helpers (unchanged API)
# ─────────────────────────────────────────────────────────────────────────────

def validate_hex(hex_code: str) -> bool:
    """Validate a hex colour code."""
    if not hex_code.startswith("#") or len(hex_code) != 7:
        return False
    try:
        int(hex_code[1:], 16)
        return True
    except ValueError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  v1 engine (CV project P04): palette + colour region map
# ─────────────────────────────────────────────────────────────────────────────
#  Fixes over v0 (kept above, selectable with method="v0"):
#    B1  skin is removed by label (SegFormer mask passed in) or by a guarded
#        YCrCb model; the whole garment is never deleted and the removed count
#        is reported correctly.
#    B2  the base colour is the largest colour AFTER merging clusters closer
#        than `merge_de` (CIEDE2000); near-white / near-black is never skipped.
#    B3  flat single colours and empty clusters are handled (no NaN, no crash).
#  A garment is never reduced to one colour: the result carries a palette with
#  a role (fabric / print) per colour and a colour region map.

V1_DEFAULT = dict(
    cluster="meanshift",  # meanshift | kmeans | kmedoids | gmm   (meanshift chosen in P04)
    skin="auto",          # none | hsv | ycrcb | auto | mask (needs skin_mask=)
    merge_de=5.0,         # merge clusters closer than this CIEDE2000
    shade_dl=0.0,         # >0: also merge same-hue clusters differing only in lightness by <= this
    min_share=0.02,       # drop colours below this share of the garment
    max_k=8,
    ms_bandwidth=10.0,    # mean-shift bandwidth in Lab units
    subsample=20000,
    wb="none",            # none | greyworld | prepare (cv_enhance.prepare_for_colour)
    clahe=False,
    clean_k=3,            # mode-filter kernel for the region map (0 = off)
    seed=42,
)


def _de2000(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """CIEDE2000 between Lab arrays (cv2 float Lab == skimage Lab, D65)."""
    a = np.atleast_2d(np.asarray(a, np.float64))
    b = np.atleast_2d(np.asarray(b, np.float64))
    try:
        from skimage.color import deltaE_ciede2000
        return deltaE_ciede2000(a, b)
    except Exception:  # noqa: BLE001
        return np.linalg.norm(a - b, axis=1)


def _skin_candidates(rgb: np.ndarray, mode: str) -> np.ndarray:
    """Per-pixel skin-colour test on an (H, W, 3) uint8 RGB image."""
    if mode == "hsv":  # the v0 range
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        return (cv2.inRange(hsv, _SKIN_LOWER_1, _SKIN_UPPER_1) > 0) | (cv2.inRange(hsv, _SKIN_LOWER_2, _SKIN_UPPER_2) > 0)
    ycc = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    cr, cb = ycc[..., 1], ycc[..., 2]
    return (cr >= 135) & (cr <= 173) & (cb >= 77) & (cb <= 127) & (ycc[..., 0] > 40)


def _skin_keep(rgb, mask, mode, skin_mask=None, guard=0.35):
    """Return (keep_mask, n_removed). Never removes (almost) the whole garment."""
    n = int(mask.sum())
    if mode == "none" or n == 0:
        return mask, 0
    if mode == "mask" or (skin_mask is not None and mode in ("auto", "segformer")):
        if skin_mask is None:
            return mask, 0
        cand = skin_mask.astype(bool) & mask
        if cand.sum() > 0.6 * n:  # parser failed on a flat photo; do not delete the garment
            return mask, 0
    elif mode in ("hsv", "ycrcb"):
        cand = _skin_candidates(rgb, mode) & mask
        if cand.sum() >= n:        # unguarded ablation modes still never empty the garment
            return mask, 0
    else:  # auto: guarded YCrCb
        cand = _skin_candidates(rgb, "ycrcb") & mask
        if cand.sum() > guard * n:  # garment itself is skin-coloured (tan, coral, pink, brown fabric)
            return mask, 0
        # keep only blobs (arm, neck, hand); isolated skin-like specks are fabric/print
        k = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n_cc, lab_cc, stats, _ = cv2.connectedComponentsWithStats(k, connectivity=8)
        big = np.zeros(n_cc, bool)
        big[1:] = stats[1:, cv2.CC_STAT_AREA] >= max(30, 0.003 * n)
        cand = big[lab_cc] & cand
    return mask & ~cand, int(cand.sum())


def _enhance(rgb, mask, wb, clahe):
    out = rgb
    if wb == "prepare":   # cv_enhance.prepare_for_colour: bilateral denoise + per-region shading removal (P03)
        try:
            import cv_enhance
            out = cv_enhance.prepare_for_colour(rgb, mask)
        except Exception:  # noqa: BLE001  (module missing or failed: use the photo as it is)
            out = rgb
    if wb == "greyworld" and mask.any():
        m = rgb[mask].reshape(-1, 3).mean(0)
        gain = m.mean() / np.maximum(m, 1.0)
        out = np.clip(out.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    if clahe:
        lab = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
        lab[..., 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[..., 0])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return out


# ── clustering back-ends: all return LAB centres (K, 3) ────────────────────

def _kmeans_centres(lab, max_k, seed):
    n = len(lab)
    sample = lab if n <= 4000 else lab[np.random.default_rng(seed).choice(n, 4000, replace=False)]
    best, best_s = None, -2.0
    for k in range(2, min(max_k, len(np.unique(sample.round(1), axis=0))) + 1):
        km = KMeans(n_clusters=k, random_state=seed, n_init=3, max_iter=100).fit(sample)
        if len(set(km.labels_)) < 2:
            continue
        s = silhouette_score(sample, km.labels_, sample_size=min(2000, len(sample)), random_state=seed)
        if s > best_s:
            best, best_s = km, s
    return best.cluster_centers_ if best is not None else sample.mean(0, keepdims=True)


def _kmedoids_centres(lab, max_k, seed, n_sub=1500, iters=30):
    """Simple K-medoids (alternate / Voronoi-iteration PAM) on a pixel subsample; K by silhouette."""
    from sklearn.metrics import pairwise_distances
    rng = np.random.default_rng(seed)
    x = lab if len(lab) <= n_sub else lab[rng.choice(len(lab), n_sub, replace=False)]
    d = pairwise_distances(x)
    best, best_s = None, -2.0
    for k in range(2, min(max_k, len(np.unique(x.round(1), axis=0))) + 1):
        med = [int(rng.integers(len(x)))]            # k-medoids++ initialisation
        for _ in range(k - 1):
            dm = d[:, med].min(1) ** 2
            med.append(int(rng.choice(len(x), p=dm / dm.sum())) if dm.sum() > 0 else int(rng.integers(len(x))))
        med = np.array(med)
        for _ in range(iters):
            lbl = d[:, med].argmin(1)
            new = med.copy()
            for j in range(k):
                idx = np.where(lbl == j)[0]
                if len(idx):
                    new[j] = idx[d[np.ix_(idx, idx)].sum(1).argmin()]
            if (new == med).all():
                break
            med = new
        lbl = d[:, med].argmin(1)
        if len(set(lbl)) < 2:
            continue
        s = silhouette_score(d, lbl, metric="precomputed")
        if s > best_s:
            best, best_s = x[med], s
    return best if best is not None else np.median(x, 0, keepdims=True)


def _gmm_centres(lab, max_k, seed):
    from sklearn.mixture import GaussianMixture
    n = len(lab)
    sample = lab if n <= 8000 else lab[np.random.default_rng(seed).choice(n, 8000, replace=False)]
    best, best_b = None, np.inf
    for k in range(1, max_k + 1):
        g = GaussianMixture(k, covariance_type="full", reg_covar=1e-2, random_state=seed, n_init=1, max_iter=100).fit(sample)
        b = g.bic(sample)
        if b < best_b:
            best, best_b = g, b
    return best.means_


def _meanshift_centres(lab, max_k, seed, bandwidth=10.0):
    from sklearn.cluster import MeanShift
    n = len(lab)
    sample = lab if n <= 3000 else lab[np.random.default_rng(seed).choice(n, 3000, replace=False)]
    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True, max_iter=50).fit(sample)
    return ms.cluster_centers_


_CLUSTERERS = {"kmeans": _kmeans_centres, "kmedoids": _kmedoids_centres, "gmm": _gmm_centres, "meanshift": _meanshift_centres}


def _assign(lab, centres, chunk=100_000):
    out = np.empty(len(lab), np.int32)
    for i in range(0, len(lab), chunk):
        d = ((lab[i:i + chunk, None, :] - centres[None, :, :]) ** 2).sum(-1)
        out[i:i + chunk] = d.argmin(1)
    return out


def _merge_centres(centres, counts, thr, shade_dl=0.0):
    """Agglomerative merge: close in CIEDE2000, or (optionally) same hue differing only in lightness."""
    c = [np.asarray(v, np.float64) for v in centres]
    w = [float(x) for x in counts]
    while len(c) > 1:
        best, pair = None, None
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                d = float(_de2000(c[i], c[j])[0])
                close = d < thr
                if shade_dl > 0 and not close:
                    dl = abs(c[i][0] - c[j][0])
                    dab = float(np.hypot(c[i][1] - c[j][1], c[i][2] - c[j][2]))
                    close = dl <= shade_dl and dab <= 6.0
                    d = dl / 10.0 if close else d
                if close and (best is None or d < best):
                    best, pair = d, (i, j)
        if pair is None:
            break
        i, j = pair
        tot = (w[i] + w[j]) or 1.0
        c[i] = (c[i] * w[i] + c[j] * w[j]) / tot
        w[i] = w[i] + w[j]
        del c[j], w[j]
    return np.array(c), np.array(w)


def _mode_filter(lbl, mask, k, ksize):
    """Majority vote of labels inside a ksize x ksize window (garment pixels only)."""
    if ksize < 3:
        return lbl
    votes = np.zeros(lbl.shape + (k,), np.float32)
    for j in range(k):
        votes[..., j] = cv2.boxFilter(((lbl == j) & mask).astype(np.float32), -1, (ksize, ksize), normalize=False)
    new = votes.argmax(-1).astype(lbl.dtype)
    new[~mask] = -1
    return new


def _roles_and_regions(lbl, mask, shares):
    """Role per colour (fabric / print) and a small region summary from connected components."""
    n_garment = int(mask.sum())
    infos = []
    for k, sh in enumerate(shares):
        km = (lbl == k).astype(np.uint8)
        n_cc, cc, stats, _ = cv2.connectedComponentsWithStats(km, connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA] if n_cc > 1 else np.array([0])
        if n_cc > 1:
            li = 1 + int(areas.argmax())
            comp = (cc == li).astype(np.uint8)
            ring = (cv2.dilate(comp, np.ones((3, 3), np.uint8)) & (1 - comp)).astype(bool)
            outside = int((ring & ~mask).sum())
            other = int((ring & mask).sum())
            touch = outside / max(outside + other, 1)
            x, y, w, h = (int(stats[li, i]) for i in (0, 1, 2, 3))
            bbox = [x, y, x + w, y + h]
            largest = float(areas.max()) / max(n_garment, 1)
        else:
            touch, bbox, largest = 0.0, [0, 0, 0, 0], 0.0
        n_comp = int((areas >= max(4, 0.001 * n_garment)).sum())   # specks are noise, not components
        infos.append(dict(index=k, share=float(sh), n_components=n_comp, largest_component_share=round(largest, 4),
                          garment_edge_touch=round(touch, 3), bbox=bbox))
    order = np.argsort(-np.asarray(shares))
    for rank, k in enumerate(order):
        i = infos[int(k)]
        i["role"] = "fabric" if (rank == 0 or (i["largest_component_share"] >= 0.08 and i["garment_edge_touch"] >= 0.08)) else "print"
    return infos


def extract_palette_v1(rgba_image, skin_mask=None, **overrides) -> ColourResult:
    """Palette + roles + region map for the garment pixels (alpha > 10)."""
    cfg = {**V1_DEFAULT, **overrides}
    if not HAS_SKLEARN:
        return ColourResult(success=False, message="scikit-learn not installed")
    if rgba_image is None or rgba_image.ndim != 3 or rgba_image.shape[2] < 4:
        return ColourResult(success=False, message="Invalid RGBA image")
    rgb = np.ascontiguousarray(rgba_image[:, :, :3])
    mask = rgba_image[:, :, 3] > 10
    if int(mask.sum()) < 2:
        return ColourResult(success=False, message="Not enough opaque pixels")
    rgb = _enhance(rgb, mask, cfg["wb"], cfg["clahe"])
    keep, removed = _skin_keep(rgb, mask, cfg["skin"], skin_mask)
    if int(keep.sum()) < 2:           # never delete the whole garment
        keep, removed = mask, 0

    ys, xs = np.nonzero(keep)
    pix = rgb[ys, xs]
    lab = _rgb_to_lab_float32(pix)
    rng = np.random.default_rng(cfg["seed"])
    sub = lab if len(lab) <= cfg["subsample"] else lab[rng.choice(len(lab), cfg["subsample"], replace=False)]

    if len(np.unique(sub.round(1), axis=0)) < 2:                      # B3: perfectly flat colour
        centres = sub.mean(0, keepdims=True)
    else:
        if cfg["cluster"] == "meanshift":
            centres = _meanshift_centres(sub, cfg["max_k"], cfg["seed"], cfg["ms_bandwidth"])
        else:
            centres = _CLUSTERERS[cfg["cluster"]](sub, cfg["max_k"], cfg["seed"])
    centres = np.asarray(centres, np.float64)
    cnt = np.bincount(_assign(sub, centres), minlength=len(centres))
    centres, cnt = _merge_centres(centres, cnt, cfg["merge_de"], cfg["shade_dl"])

    # assign every garment pixel, drop tiny colours, repeat until stable
    while True:
        idx = _assign(lab, centres)
        cnt = np.bincount(idx, minlength=len(centres)).astype(float)
        small = (cnt / len(idx) < cfg["min_share"]) & (cnt < cnt.max())
        if len(centres) > 1 and small.any():
            centres = centres[~small]
            continue
        break

    lbl = np.full(mask.shape, -1, np.int32)
    lbl[ys, xs] = idx
    if cfg["clean_k"]:
        lbl = _mode_filter(lbl, keep, len(centres), int(cfg["clean_k"]))
    flat = lbl[ys, xs]
    counts = np.bincount(flat, minlength=len(centres))
    used = np.nonzero(counts > 0)[0]
    remap = -np.ones(len(centres), np.int32)
    remap[used] = np.arange(len(used))
    lbl[lbl >= 0] = remap[lbl[lbl >= 0]]
    flat = lbl[ys, xs]
    K = len(used)
    counts = np.bincount(flat, minlength=K)
    shares = counts / counts.sum()

    infos = _roles_and_regions(lbl, keep, shares)
    palette: List[ColorInfo] = []
    for k in range(K):
        sel = pix[flat == k]
        mean_rgb = tuple(int(round(v)) for v in sel.mean(0))
        lab_c = tuple(float(v) for v in _rgb_to_lab_float32(np.array([mean_rgb], np.uint8))[0])
        palette.append(ColorInfo(rgb=mean_rgb, lab=lab_c, hex_code=_rgb_to_hex_lower(mean_rgb),
                                 clo3d_hex=_rgb_to_hex_upper(mean_rgb), percentage=float(shares[k] * 100),
                                 role=infos[k]["role"]))
        infos[k]["hex"] = palette[-1].hex_code
    order = sorted(range(K), key=lambda k: -shares[k])
    new_pos = {old: new for new, old in enumerate(order)}
    palette = [palette[k] for k in order]
    regions = [{**infos[k], "index": new_pos[k]} for k in order]
    lbl2 = lbl.copy()
    lbl2[lbl >= 0] = np.array([new_pos[k] for k in range(K)], np.int32)[lbl[lbl >= 0]]

    fabric = [p for p in palette if p.role == "fabric"]
    base = fabric[0] if fabric else palette[0]                       # largest fabric colour (compatibility)
    return ColourResult(
        base_colour_hex=base.hex_code, clo3d_base_hex=base.clo3d_hex, palette=palette, k_used=K,
        skin_pixels_removed=int(removed), success=True, message="OK",
        palette_roles=[{"hex": p.hex_code, "share": round(p.percentage / 100, 4), "role": p.role} for p in palette],
        fabric_colours=[p.hex_code for p in fabric],
        region_map={"method": f"v1:{cfg['cluster']}", "n_regions": K, "regions": regions},
        label_map=lbl2, method=f"v1:{cfg['cluster']}",
    )


def extract_colours(rgba_image, method: str = "v1", **kwargs) -> tuple[ColourResult, bool]:
    """Extract palette (every major colour with role and share), colour region map,
    and the compatibility base colour; returns (ColourResult, hex_valid).

    method="v1" (default): the P04 engine (see V1_DEFAULT; override any option by keyword,
    e.g. cluster="kmeans", skin="none", skin_mask=<bool HxW from a clothes parser>).
    method="v0": the original K-Means pipeline (kept for before/after comparison).
    """
    if method == "v0":
        result = ColourExtractor().extract(rgba_image)
        result.method = "v0"
    else:
        result = extract_palette_v1(rgba_image, **kwargs)
    return result, bool(result.success and validate_hex(result.base_colour_hex))
