"""Two-level design-region detection for Step 4 (CV project plan P05).

Level 1 = the garment outline (a boolean mask, given).
Level 2 = every design region inside the garment, each with a type:
          text | graphic | logo | stripes | colour_block | pattern.

Everything here is classical computer vision (numpy / OpenCV / scikit-image) except the
optional SAM 2 and SigLIP helpers, which import torch lazily.  All boxes are returned in the
PIXELS of the input image: {"box": [x0, y0, x1, y1], "type": str, "confidence": float,
"source": str}.

Main entry point:  detect_regions(rgb, mask, method="v4_relabel") -> list[dict]

Methods built on the v3 flow (P05 + P15b):
  v3_combo   colour + OCR + Hough + colour blocks + cleaned Grounding DINO, priority NMS (P05 default, unchanged)
  v3_fix     v3_combo + two P15b fixes: (a) a text box inside a graphic box is kept (captions under prints),
             (b) an OCR box that holds two text lines of very different glyph height is split in two
  v4_nofix   v3_combo + zero-shot SigLIP 2 relabelling of every non-colour-block region (padded crop, single
             prompt; a "plain" prediction drops the region)
  v4_relabel v3_fix + the SigLIP 2 relabelling   (pipeline default)

Fixes over the v0 extractor (step_04_0_design_extraction.py, method="v0"):
  * B4: the periodicity test now works on an inner patch (away from the outline), with a Hann
    window and the shading removed, and compares each spectral peak with the radially averaged
    spectrum (median per ring) instead of "global max / global mean".
  * The garment outline is never an edge: a band just inside the outline is ignored and the
    background is not painted black.
  * The variance test uses a percentile, not the max.
  * Shading (folds, light gradients) is removed with a colour-block aware fabric model.
"""
from __future__ import annotations

import contextlib
import math
from dataclasses import dataclass, field

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

# Callable returning a context manager that guards GPU use (the CV runner sets it to gpu_lock("p05")).
GPU_CTX = lambda: contextlib.nullcontext()  # noqa: E731
USE_OCR = True     # False: skip EasyOCR (text then comes from the connected-component text detector)
WORK = 512          # working resolution (longest side)
SEED = 0
TYPES = ("text", "graphic", "logo", "stripes", "colour_block", "pattern")


# ───────────────────────────── preparation ─────────────────────────────

@dataclass
class Prep:
    rgb: np.ndarray            # working-resolution RGB uint8
    mask: np.ndarray           # garment mask (bool), working res
    inner: np.ndarray          # mask eroded by the outline band (bool)
    lab: np.ndarray            # float32 Lab
    scale: float               # working px per original px
    area: int
    diag: float                # sqrt(area)
    band: int
    flat: np.ndarray = None    # L residual after shading removal (float32)
    dev: np.ndarray = None     # deltaE2000 to the local fabric colour (float32)
    blocks: list = field(default_factory=list)   # [{"box":..., "lab":..., "share":...}]
    block_id: np.ndarray = None
    info: dict = field(default_factory=dict)


def _kern(k: int):
    k = max(1, int(k)) | 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def _de2000(lab_a: np.ndarray, lab_b: np.ndarray) -> np.ndarray:
    """deltaE2000 between two (h, w, 3) Lab images (chunked to keep memory small)."""
    h, w = lab_a.shape[:2]
    out = np.zeros((h, w), np.float32)
    step = max(1, 65536 // w)
    for y in range(0, h, step):
        out[y:y + step] = deltaE_ciede2000(lab_a[y:y + step], lab_b[y:y + step]).astype(np.float32)
    return out


def prepare(rgb: np.ndarray, mask: np.ndarray, work: int = WORK, band_frac: float = 0.03) -> Prep:
    h, w = mask.shape
    s = min(3.0, work / max(h, w))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    rgb_s = cv2.resize(rgb, None, fx=s, fy=s, interpolation=interp)
    m = cv2.resize(mask.astype(np.uint8), (rgb_s.shape[1], rgb_s.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    area = int(m.sum())
    diag = math.sqrt(max(area, 1))
    band = max(3, int(round(band_frac * diag)))
    inner = cv2.erode(m.astype(np.uint8), _kern(2 * band + 1)) > 0
    lab = rgb2lab(rgb_s.astype(np.float32) / 255.0).astype(np.float32)
    P = Prep(rgb_s, m, inner, lab, s, area, diag, band)
    _fabric_model(P)
    return P


def _normalised_conv(vals: np.ndarray, wt: np.ndarray, sigma: float):
    k = int(sigma * 6) | 1
    num = cv2.GaussianBlur(vals * wt[..., None], (k, k), sigma)
    den = cv2.GaussianBlur(wt, (k, k), sigma)
    return num, den


def _fabric_model(P: Prep, k_clusters: int = 4, t_fab: float = 9.0) -> None:
    """Estimate the local fabric colour everywhere (shading removal, colour-block aware).

    1. k-means on Lab of the inner garment pixels; neighbouring clusters (deltaE < 12) merge.
    2. A cluster is a *block* when, after a large opening, one connected piece holds >= 15 % of
       the inner area.  One block covering >= 60 % means "single fabric"; two or more blocks
       that differ by deltaE >= 20 mean "colour-blocked garment".
    3. Per block, the fabric colour field is a normalised Gaussian convolution of the block
       pixels that are close to the block median (so prints are excluded) - this follows soft
       shading.  Each pixel is compared with the field of ITS block -> deviation map `dev`.
    """
    lab, inner = P.lab, P.inner
    ys, xs = np.nonzero(inner)
    if len(ys) < 50:
        P.dev = np.zeros(inner.shape, np.float32)
        P.flat = np.zeros(inner.shape, np.float32)
        P.block_id = np.zeros(inner.shape, np.int32)
        return
    pix = lab[ys, xs]
    rng = np.random.RandomState(SEED)
    sub = pix[rng.choice(len(pix), min(len(pix), 20000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    k = min(k_clusters, max(1, len(sub) // 50))
    cv2.setRNGSeed(SEED)
    _, _, centres = cv2.kmeans(sub.astype(np.float32), k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    # assign every inner pixel to nearest centre
    d = ((pix[:, None, :] - centres[None]) ** 2).sum(-1)
    lbl = d.argmin(1)
    # merge close centres (union-find on deltaE < 12)
    par = list(range(k))
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for i in range(k):
        for j in range(i + 1, k):
            if deltaE_ciede2000(centres[i][None], centres[j][None])[0] < 12:
                par[find(j)] = find(i)
    roots = np.array([find(i) for i in range(k)])
    lbl = roots[lbl]
    cl_map = np.full(inner.shape, -1, np.int32)
    cl_map[ys, xs] = lbl
    open_k = _kern(max(3, int(0.06 * P.diag)))
    n_inner = int(inner.sum())
    comps = []
    for c in np.unique(lbl):
        cm = (cl_map == c).astype(np.uint8)
        cm = cv2.morphologyEx(cm, cv2.MORPH_OPEN, open_k)
        n, cc, st, _ = cv2.connectedComponentsWithStats(cm)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] >= 0.15 * n_inner:
                comps.append((cc == i, int(c)))
    comps.sort(key=lambda t: -t[0].sum())
    blocks = []
    if comps and comps[0][0].sum() >= 0.60 * n_inner:
        comps = comps[:1]
    # keep blocks whose colours differ by >= 20 from earlier kept blocks, else treat as one fabric
    kept = []
    for cm, c in comps:
        med = np.median(lab[cm], axis=0)
        if all(deltaE_ciede2000(med[None], kk[2][None])[0] >= 20 for kk in kept):
            kept.append((cm, c, med))
    if not kept:                      # no big comp: use the whole inner area as one fabric
        kept = [(inner.copy(), 0, np.median(pix, axis=0))]
    # block id map: nearest block (distance transform)
    if len(kept) == 1:
        bid = np.zeros(inner.shape, np.int32)
    else:
        dts = np.stack([cv2.distanceTransform((~k_[0]).astype(np.uint8), cv2.DIST_L2, 3) for k_ in kept])
        bid = dts.argmin(0).astype(np.int32)
    sigma = max(4.0, 0.12 * P.diag)
    dev = np.zeros(inner.shape, np.float32)
    flat = np.zeros(inner.shape, np.float32)
    P.blocks = []
    for bi, (cm, c, med) in enumerate(kept):
        region = (bid == bi) & P.mask
        ref = np.broadcast_to(med.astype(np.float32), lab.shape).copy()
        de0 = _de2000(lab, ref)
        wt = (region & inner & (de0 < t_fab)).astype(np.float32)
        if wt.sum() < 20:
            wt = (region & inner).astype(np.float32)
        num, den = _normalised_conv(lab, wt, sigma)
        field_ = np.where(den[..., None] > 1e-3, num / np.maximum(den[..., None], 1e-6), med[None, None, :]).astype(np.float32)
        de = _de2000(lab, field_)
        dev[region] = de[region]
        flat[region] = (lab[..., 0] - field_[..., 0])[region]
        ys2, xs2 = np.nonzero(cm)
        P.blocks.append({"box": [int(xs2.min()), int(ys2.min()), int(xs2.max()) + 1, int(ys2.max()) + 1],
                         "lab": [float(v) for v in med], "share": float(cm.sum() / n_inner)})
    P.dev, P.flat, P.block_id = dev, flat, bid
    P.info["n_blocks"] = len(kept)


# ───────────────────────────── geometry helpers ─────────────────────────────

def _to_orig(P: Prep, box):
    s = P.scale
    return [float(box[0] / s), float(box[1] / s), float(box[2] / s), float(box[3] / s)]


def _box_iou(a, b) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _contain(a, b) -> float:
    """share of box a that lies inside box b"""
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    return inter / aa if aa > 0 else 0.0


# ───────────────────────────── B4: periodicity test ─────────────────────────────

def _inner_patch(P: Prep):
    """Largest central rectangle that is >= 95 % inside the inner garment mask."""
    ys, xs = np.nonzero(P.inner)
    if len(ys) == 0:
        return None
    cy, cx = int(np.median(ys)), int(np.median(xs))
    best = None
    hh = max(P.inner.shape) // 2
    for r in range(hh, 7, -4):
        y0, y1 = max(0, cy - r), min(P.inner.shape[0], cy + r)
        x0, x1 = max(0, cx - r), min(P.inner.shape[1], cx + r)
        if P.inner[y0:y1, x0:x1].mean() >= 0.95:
            best = (x0, y0, x1, y1)
            break
    return best


def periodicity(P: Prep, min_ratio: float = 12.0, rel_min: float = 2.0) -> dict:
    """B4 fix: windowed FFT on an inner patch of the shading-free luminance.

    Each spectrum bin is compared with the MEDIAN of its own radius ring (radially averaged
    spectrum).  A real repeating print gives (at least two) bins far above their ring, and a
    strong share of the patch energy; fold shading gives broadband low-frequency energy only
    and so has no isolated peak above its ring.  Because the spectrum of a real image is
    point-symmetric, "symmetric peak pairs" is checked as: peak at (u, v) AND mirrored peak at
    (-u, -v) both above threshold, then counted as one pair; >= 2 distinct pairs (or one pair
    with a harmonic) are required.
    """
    box = _inner_patch(P)
    out = {"periodic": False, "ratio": 0.0, "n_pairs": 0, "period_px": 0.0, "angle": 0.0}
    if box is None:
        return out
    x0, y0, x1, y1 = box
    patch = P.flat[y0:y1, x0:x1].astype(np.float32)
    n = min(patch.shape)
    if n < 48:
        return out
    patch = cv2.resize(patch, (n, n), interpolation=cv2.INTER_AREA) if patch.shape[0] != patch.shape[1] else patch[:n, :n]
    patch = patch - patch.mean()
    win = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
    mag = np.abs(np.fft.fftshift(np.fft.fft2(patch * win)))
    cy = cx = n // 2
    yy, xx = np.indices(mag.shape)
    rr = np.hypot(yy - cy, xx - cx)
    ring = rr.astype(int)
    rmax = int(0.45 * n)
    med = np.zeros(rmax + 2, np.float32)
    for r in range(rmax + 2):
        sel = ring == r
        med[r] = np.median(mag[sel]) if sel.any() else 1.0
    ratio_map = mag / (med[np.clip(ring, 0, rmax + 1)] + 1e-6)
    valid = (rr >= max(8, 0.03 * n)) & (rr <= rmax)      # low radii = folds / shading, not prints
    loc_med = cv2.medianBlur(np.clip(mag / (mag.max() + 1e-9) * 255, 0, 255).astype(np.uint8), 11).astype(np.float32) / 255 * (mag.max() + 1e-9)
    sharp = mag / (loc_med + 1e-6)                        # a print gives a sharp spike, a fold a broad lobe
    # local maxima
    mx = cv2.dilate(mag, np.ones((5, 5), np.uint8))
    cand = valid & (mag >= mx) & (ratio_map >= min_ratio) & (sharp >= 4.0)
    pts = np.argwhere(cand)
    # energy share of the peaks (the pattern must carry real energy, not a noise spike)
    tot = float((mag[valid] ** 2).sum()) + 1e-9
    pairs = []
    used = np.zeros(len(pts), bool)
    for i, (py, px) in enumerate(pts):
        if used[i]:
            continue
        my, mx_ = 2 * cy - py, 2 * cx - px
        j = None
        for jj, (qy, qx) in enumerate(pts):
            if not used[jj] and jj != i and abs(qy - my) <= 2 and abs(qx - mx_) <= 2:
                j = jj; break
        if j is not None:
            used[i] = used[j] = True
            e = float(mag[py, px] ** 2 + mag[pts[j][0], pts[j][1]] ** 2) / tot
            pairs.append((float(ratio_map[py, px]), e, float(rr[py, px]), float(math.degrees(math.atan2(py - cy, px - cx)))))
    out["n_pairs"] = len(pairs)
    if pairs:
        pairs.sort(reverse=True)
        out["ratio"] = pairs[0][0]
        out["period_px"] = float(n / max(pairs[0][2], 1e-6))
        out["angle"] = pairs[0][3]
        out["energy_share"] = float(sum(p[1] for p in pairs))
    # decision: >= 2 distinct pairs OR one very strong pair with real energy
    out["periodic"] = bool(len(pairs) >= 2 or (pairs and pairs[0][0] >= 4 * min_ratio and pairs[0][1] >= 0.02))
    return out


# ───────────────────────────── proposal methods ─────────────────────────────

def _boxes_from_mask(D: np.ndarray, close_frac: float, P: Prep, min_frac: float = 0.0006, max_frac: float = 0.85):
    """Group a binary design mask into regions (morphological closing then connected pieces)."""
    D = D.astype(np.uint8)
    ck = _kern(max(3, int(close_frac * P.diag)))
    G = cv2.morphologyEx(D, cv2.MORPH_CLOSE, ck)
    n, cc, st, _ = cv2.connectedComponentsWithStats(G)
    regs = []
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < min_frac * P.area or a > max_frac * P.area:
            continue
        x, y, w, h = st[i, :4]
        regs.append({"box": [int(x), int(y), int(x + w), int(y + h)], "ink": float(D[cc == i].mean()), "mask": (cc == i)})
    return regs


def propose_colour(P: Prep, thr: float = 12.0, close_frac: float = 0.028) -> list:
    """(c) pixels that differ from the local fabric colour by deltaE2000 > thr -> regions."""
    D = (P.dev > thr) & P.inner
    D = cv2.morphologyEx(D.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)) > 0
    P.info["dev_cov"] = float(D.sum() / max(P.inner.sum(), 1))
    P.info["dev_mask"] = D
    regs = _boxes_from_mask(D, close_frac, P)
    for r in regs:
        r["source"] = "colour"
        r["confidence"] = float(min(1.0, np.median(P.dev[r["mask"] & D]) / 40.0)) if (r["mask"] & D).any() else 0.3
    return regs


def propose_classical(P: Prep) -> list:
    """(b) fixed v0: auto-Canny on the shading-free luminance, outline band ignored,
    closing, external contours, percentile variance test, area filter."""
    g = np.clip(128 + P.flat, 0, 255).astype(np.uint8)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    med = float(np.median(g[P.inner])) if P.inner.any() else 128.0
    sigma = 0.33
    # on a flattened image the median is ~128; use the robust spread of the residual instead
    spread = float(np.percentile(np.abs(P.flat[P.inner]), 75)) if P.inner.any() else 5.0
    hi = max(20.0, 3.0 * spread)
    edges = cv2.Canny(g, 0.5 * hi, hi)
    edges[~P.inner] = 0                       # outline band ignored
    ek = _kern(max(3, int(0.03 * P.diag)))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, ek, iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gf = P.flat.astype(np.float32)
    k = 9
    var = cv2.blur(gf ** 2, (k, k)) - cv2.blur(gf, (k, k)) ** 2
    regs = []
    for c in contours:
        a = cv2.contourArea(c)
        if a < 0.003 * P.area or a > 0.8 * P.area:
            continue
        cm = np.zeros(P.inner.shape, np.uint8)
        cv2.drawContours(cm, [c], -1, 1, -1)
        cm = (cm > 0) & P.inner
        if cm.sum() < 10:
            continue
        p90 = float(np.percentile(var[cm], 90))      # percentile, not max
        if p90 < 60.0:
            continue
        x, y, w, h = cv2.boundingRect(c)
        regs.append({"box": [x, y, x + w, y + h], "mask": cm, "source": "classical", "confidence": min(1.0, p90 / 600.0)})
    return regs


def _haar_energy(img: np.ndarray, levels: int = 2) -> list:
    """Haar DWT detail energies (LH, HL, HH) per level, upsampled to the image size."""
    out = []
    cur = img.astype(np.float32)
    h, w = img.shape
    for _ in range(levels):
        hh, ww = cur.shape[0] // 2 * 2, cur.shape[1] // 2 * 2
        c = cur[:hh, :ww]
        a, b, cc_, d = c[0::2, 0::2], c[0::2, 1::2], c[1::2, 0::2], c[1::2, 1::2]
        ll = (a + b + cc_ + d) / 4
        lh = (a + b - cc_ - d) / 4
        hl = (a - b + cc_ - d) / 4
        hhh = (a - b - cc_ + d) / 4
        for band in (lh, hl, hhh):
            e = cv2.GaussianBlur(np.abs(band), (0, 0), 1.5)
            out.append(cv2.resize(e, (w, h), interpolation=cv2.INTER_LINEAR))
        cur = ll
    return out


def texture_features(P: Prep) -> np.ndarray:
    """Per-pixel texture vector: Gabor bank magnitudes (4 orientations x 3 wavelengths) +
    2-level Haar DWT detail energies, on the shading-free luminance."""
    g = P.flat.astype(np.float32)
    feats = []
    for lam in (4.0, 8.0, 16.0):
        for th in np.arange(4) * np.pi / 4:
            ks = int(lam * 2.5) | 1
            ke = cv2.getGaborKernel((ks, ks), lam * 0.56, th, lam, 1.0, 0, ktype=cv2.CV_32F)
            ko = cv2.getGaborKernel((ks, ks), lam * 0.56, th, lam, 1.0, np.pi / 2, ktype=cv2.CV_32F)
            ke -= ke.mean(); ko -= ko.mean()
            e, o = cv2.filter2D(g, cv2.CV_32F, ke), cv2.filter2D(g, cv2.CV_32F, ko)
            feats.append(cv2.GaussianBlur(np.sqrt(e * e + o * o), (0, 0), lam * 0.8))
    feats += _haar_energy(g, 2)
    return np.stack(feats, -1)


def propose_texture(P: Prep, k: int = 3, close_frac: float = 0.03) -> list:
    """(d) texture segmentation: Gabor + DWT features, k-means in the inner garment; the
    low-energy cluster is the fabric, the remaining pixels become regions."""
    F = texture_features(P)
    ys, xs = np.nonzero(P.inner)
    if len(ys) < 100:
        return []
    X = F[ys, xs]
    X = np.log1p(np.maximum(X, 0))
    X = (X - X.mean(0)) / (X.std(0) + 1e-6)
    rng = np.random.RandomState(SEED)
    sub = X[rng.choice(len(X), min(len(X), 15000), replace=False)].astype(np.float32)
    cv2.setRNGSeed(SEED)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.1)
    _, _, cen = cv2.kmeans(sub, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    lbl = ((X[:, None, :] - cen[None]) ** 2).sum(-1).argmin(1)
    energy = np.array([np.exp(0) * X[lbl == c].mean() if (lbl == c).any() else 9 for c in range(k)])
    fabric = int(np.argmin(energy.mean(1) if energy.ndim > 1 else energy))
    D = np.zeros(P.inner.shape, bool)
    D[ys[lbl != fabric], xs[lbl != fabric]] = True
    # fabric cluster must be the big one, else nothing is a design
    share_fab = float((lbl == fabric).mean())
    P.info["tex_fabric_share"] = share_fab
    if share_fab < 0.3:
        return []
    D = cv2.morphologyEx(D.astype(np.uint8), cv2.MORPH_OPEN, _kern(3)) > 0
    regs = _boxes_from_mask(D, close_frac, P, min_frac=0.003)
    for r in regs:
        r["source"] = "texture"; r["confidence"] = 0.5
    P.info["tex_mask"] = D
    return regs


def propose_stripes(P: Prep) -> list:
    """(d) Hough lines -> parallel, regularly spaced line family = stripes."""
    g = np.clip(128 + P.flat, 0, 255).astype(np.uint8)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    spread = float(np.percentile(np.abs(P.flat[P.inner]), 75)) if P.inner.any() else 5.0
    hi = max(20.0, 3.0 * spread)
    edges = cv2.Canny(g, 0.5 * hi, hi)
    er = cv2.erode(P.inner.astype(np.uint8), _kern(max(3, int(0.02 * P.diag)))) > 0
    edges[~er] = 0
    ys, xs = np.nonzero(P.inner)
    if len(ys) == 0:
        return []
    bw = xs.max() - xs.min()
    bh = ys.max() - ys.min()
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=25, minLineLength=int(0.18 * max(bw, bh)), maxLineGap=int(0.03 * P.diag))
    if lines is None or len(lines) < 6:
        return []
    L = lines[:, 0, :].astype(np.float32)
    ang = np.degrees(np.arctan2(L[:, 3] - L[:, 1], L[:, 2] - L[:, 0])) % 180
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    hist, edges_a = np.histogram(ang, bins=36, range=(0, 180), weights=ln)
    # circular smoothing over angle bins
    hs = hist + np.roll(hist, 1) + np.roll(hist, -1)
    a0 = (np.argmax(hs) + 0.5) * 5.0
    dif = np.abs(((ang - a0 + 90) % 180) - 90)
    keep = dif <= 8
    if keep.sum() < 6:
        return []
    L, ln, ang = L[keep], ln[keep], ang[keep]
    th = math.radians(a0)
    nx, ny = -math.sin(th), math.cos(th)      # normal
    mid = np.stack([(L[:, 0] + L[:, 2]) / 2, (L[:, 1] + L[:, 3]) / 2], 1)
    rho = mid[:, 0] * nx + mid[:, 1] * ny
    order = np.argsort(rho)
    rho_s = rho[order]
    # cluster offsets (merge lines closer than 2 px)
    groups, cur = [], [order[0]]
    for a, b in zip(order[:-1], order[1:]):
        if rho[b] - rho[a] <= 2.5:
            cur.append(b)
        else:
            groups.append(cur); cur = [b]
    groups.append(cur)
    if len(groups) < 6:
        return []
    r_med = np.array([np.mean(rho[g]) for g in groups])
    # find the longest run of regularly spaced offsets
    sp = np.diff(r_med)
    best = (0, 0)
    i = 0
    while i < len(sp):
        j = i
        while j + 1 < len(sp) and abs(sp[j + 1] - np.median(sp[i:j + 1])) <= 0.45 * np.median(sp[i:j + 1]):
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
        i = j + 1
    nlines = best[1] - best[0] + 2
    if nlines < 6:
        return []
    sel = [idx for g in groups[best[0]:best[1] + 2] for idx in g]
    pts = np.concatenate([L[sel][:, :2], L[sel][:, 2:]], 0)
    x0, y0 = pts.min(0); x1, y1 = pts.max(0)
    sp_sel = np.diff(r_med[best[0]:best[1] + 2])
    pad = float(np.median(sp_sel)) * 0.5
    box = [int(max(0, x0)), int(max(0, y0 - pad)), int(x1), int(y1 + pad)]
    cm = np.zeros(P.inner.shape, bool)
    cm[box[1]:box[3], box[0]:box[2]] = True
    cm &= P.inner
    P.info["stripe_lines"] = int(nlines)
    return [{"box": box, "mask": cm, "type": "stripes", "source": "hough", "confidence": min(1.0, nlines / 12)}]


def propose_blocks(P: Prep) -> list:
    """colour_block regions from the fabric model (>= 2 big, clearly different colour blocks)."""
    if len(P.blocks) < 2:
        return []
    return [{"box": list(b["box"]), "mask": None, "type": "colour_block", "source": "blocks", "confidence": 0.9}
            for b in P.blocks]


def propose_text_cc(P: Prep) -> list:
    """(e, fallback) text-like groups from connected components of the deviation mask:
    >= 3 letter-sized pieces of similar height aligned along a line.  Used when the EasyOCR
    detector weights are not available offline."""
    D = (P.dev > 12.0) & P.inner
    n, cc, st, _ = cv2.connectedComponentsWithStats(D.astype(np.uint8))
    comps = [(i, st[i]) for i in range(1, n) if st[i, 4] >= 6]
    if len(comps) < 3:
        return []
    boxes = np.array([[s[0], s[1], s[0] + s[2], s[1] + s[3]] for _, s in comps], np.float32)
    h = boxes[:, 3] - boxes[:, 1]
    # link components with similar height that are close horizontally and vertically overlapping
    m = len(boxes)
    par = list(range(m))
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for i in range(m):
        for j in range(i + 1, m):
            hi_, hj = h[i], h[j]
            if max(hi_, hj) > 2.2 * max(1.0, min(hi_, hj)):
                continue
            ov = min(boxes[i, 3], boxes[j, 3]) - max(boxes[i, 1], boxes[j, 1])
            if ov < 0.4 * min(hi_, hj):
                continue
            gap = max(boxes[i, 0], boxes[j, 0]) - min(boxes[i, 2], boxes[j, 2])
            if gap <= 0.9 * max(hi_, hj):
                par[find(i)] = find(j)
    groups = {}
    for i in range(m):
        groups.setdefault(find(i), []).append(i)
    regs = []
    for g in groups.values():
        if len(g) < 3:
            continue
        b = boxes[g]
        x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
        if (x1 - x0) < 1.5 * (y1 - y0):
            continue
        cm = np.isin(cc, [comps[i][0] for i in g])
        regs.append({"box": [int(x0), int(y0), int(x1), int(y1)], "mask": cm, "type": "text", "source": "text_cc", "confidence": 0.6})
    return regs


_OCR = None


def ocr_available() -> bool:
    """EasyOCR needs its CRAFT detector weights in ~/.EasyOCR/model (cannot download offline)."""
    import os
    return os.path.exists(os.path.join(os.path.expanduser("~"), ".EasyOCR", "model", "craft_mlt_25k.pth"))


def propose_ocr(P: Prep, rgb_full: np.ndarray | None = None) -> list:
    """(e) EasyOCR text detection boxes inside the garment (returns [] if weights unavailable)."""
    if not USE_OCR or not ocr_available():
        return []
    import gc
    import easyocr
    import torch
    with GPU_CTX():
        reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available(), download_enabled=False, recognizer=False, verbose=False)
        res = reader.detect(cv2.cvtColor(P.rgb, cv2.COLOR_RGB2BGR), text_threshold=0.5, low_text=0.3)
        del reader
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    regs = []
    for b in res[0][0]:
        x0, x1, y0, y1 = [int(v) for v in b]
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        if 0 <= cy < P.mask.shape[0] and 0 <= cx < P.mask.shape[1] and P.mask[cy, cx]:
            regs.append({"box": [x0, y0, x1, y1], "mask": None, "type": "text", "source": "ocr", "confidence": 0.8})
    return regs


# ───────────────────────────── SAM 2 ─────────────────────────────

def propose_sam2(P: Prep, grid: int = 7, min_frac: float = 0.001, max_frac: float = 0.45, model=None) -> list:
    """(f) SAM 2 point-grid prompts inside the garment.  Keeps masks that differ from the fabric
    (mean deltaE2000 of the mask > 10) and are neither tiny nor the whole garment."""
    import gc
    import torch
    from transformers import Sam2Model, Sam2Processor
    from PIL import Image
    with GPU_CTX():
        path = "facebook/sam2-hiera-large"
        own = model is None
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        proc = Sam2Processor.from_pretrained(path)
        mdl = Sam2Model.from_pretrained(path, torch_dtype=torch.float16 if dev == "cuda" else torch.float32, low_cpu_mem_usage=True).to(dev).eval()
        img = Image.fromarray(P.rgb)
        ys, xs = np.nonzero(P.inner)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        pts = []
        for gy in np.linspace(y0, y1, grid + 2)[1:-1]:
            for gx in np.linspace(x0, x1, grid + 2)[1:-1]:
                if P.inner[int(gy), int(gx)]:
                    pts.append([float(gx), float(gy)])
        masks_all, scores = [], []
        with torch.no_grad():
            for i in range(0, len(pts), 8):
                chunk = pts[i:i + 8]
                inp = proc(images=img, input_points=[[[p] for p in chunk]], input_labels=[[[1] for _ in chunk]], return_tensors="pt")
                inp = {k: (v.to(dev, torch.float16) if (dev == "cuda" and v.dtype == torch.float32) else v.to(dev)) if hasattr(v, "to") else v for k, v in inp.items()}
                out = mdl(**inp, multimask_output=False)
                m = proc.post_process_masks(out.pred_masks.float().cpu(), inp["original_sizes"].cpu())[0]   # (n_obj, 1, H, W)
                sc = out.iou_scores.float().cpu().numpy().reshape(len(chunk), -1)
                for k in range(len(chunk)):
                    masks_all.append(m[k, 0].numpy() > 0)
                    scores.append(float(sc[k].max()))
        del mdl, proc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    regs = []
    seen = []
    for m, sc in zip(masks_all, scores):
        m = m & P.mask
        a = int(m.sum())
        if a < min_frac * P.area or a > max_frac * P.area:
            continue
        if float(np.mean(P.dev[m & P.inner])) < 6.0 if (m & P.inner).any() else True:
            continue
        if any((m & s).sum() / max((m | s).sum(), 1) > 0.7 for s in seen):
            continue
        seen.append(m)
        yy, xx = np.nonzero(m)
        regs.append({"box": [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1], "mask": m,
                     "source": "sam2", "confidence": sc})
    return regs



# ───────────────────────────── Grounding DINO ─────────────────────────────

GDINO_PROMPT = "logo. text. graphic print. stripes."


def propose_gdino(P: Prep, prompt: str = GDINO_PROMPT, thr: float = 0.25) -> list:
    """(g) Grounding DINO (tiny) open-vocabulary detection on the garment crop."""
    import gc
    import torch
    from PIL import Image
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    ys, xs = np.nonzero(P.mask)
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    crop = P.rgb.copy()
    crop[~P.mask] = np.round(np.median(P.rgb[P.inner], axis=0)).astype(np.uint8) if P.inner.any() else 127   # neutral background
    crop = Image.fromarray(crop[by0:by1, bx0:bx1])
    name = "IDEA-Research/grounding-dino-tiny"
    regs = []
    with GPU_CTX():
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        proc = AutoProcessor.from_pretrained(name)
        mdl = AutoModelForZeroShotObjectDetection.from_pretrained(name).to(dev).eval()
        with torch.no_grad():
            inp = proc(images=crop, text=prompt, return_tensors="pt").to(dev)
            out = mdl(**inp)
        res = proc.post_process_grounded_object_detection(out, inp["input_ids"], threshold=thr, text_threshold=thr,
                                                          target_sizes=[crop.size[::-1]])[0]
        del mdl, proc, out, inp
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    gw, gh = bx1 - bx0, by1 - by0
    for b, sc, lb in zip(res["boxes"].cpu().numpy(), res["scores"].cpu().numpy(), res.get("text_labels", res.get("labels", []))):
        x0, y0, x1, y1 = b[0] + bx0, b[1] + by0, b[2] + bx0, b[3] + by0
        if (x1 - x0) * (y1 - y0) > 0.7 * gw * gh:
            continue
        lbl = str(lb)
        t = "text" if "text" in lbl else "logo" if "logo" in lbl else "stripes" if "stripe" in lbl else "graphic" if "graphic" in lbl or "print" in lbl else "any"
        regs.append({"box": [int(x0), int(y0), int(x1), int(y1)], "mask": None, "type": t, "source": "gdino", "confidence": float(sc)})
    return regs


# ───────────────────────────── labelling ─────────────────────────────

def describe(P: Prep, box, D: np.ndarray) -> dict:
    x0, y0, x1, y1 = [int(v) for v in box]
    sub = D[y0:y1, x0:x1].astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(sub)
    comps = st[1:][st[1:, 4] >= 4]
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    d = {"aspect": bw / bh, "rel_area": bw * bh / P.area, "fill": float(sub.mean()) if sub.size else 0.0, "n_comp": int(len(comps))}
    if len(comps):
        d["h_med_rel"] = float(np.median(comps[:, 3]) / bh)
        cy = comps[:, 1] + comps[:, 3] / 2
        d["cy_spread"] = float(np.std(cy) / max(np.median(comps[:, 3]), 1))
        d["h_cv"] = float(np.std(comps[:, 3]) / max(np.mean(comps[:, 3]), 1))
    else:
        d["h_med_rel"] = d["cy_spread"] = d["h_cv"] = 0.0
    return d


def rule_label(P: Prep, box, D: np.ndarray) -> str:
    """Rule-based type for a region that is not already stripes / colour_block."""
    d = describe(P, box, D)
    textlike = d["n_comp"] >= 3 and d["aspect"] >= 1.6 and d["fill"] < 0.6 and d["cy_spread"] < 0.9
    if textlike:
        return "text"
    if d["rel_area"] < 0.03:
        return "logo"
    return "graphic"


# ───────────────────────────── merging ─────────────────────────────

def nms_merge(regs: list, iou_thr: float = 0.5, contain_thr: float = 0.85) -> list:
    """Non-maximum suppression on boxes (same-type boxes contained in a bigger one or heavily
    overlapping are merged into the more confident / larger one)."""
    regs = sorted(regs, key=lambda r: (-r.get("confidence", 0), -(r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1])))
    out = []
    for r in regs:
        drop = False
        for k in out:
            same = r["type"] == k["type"] or "any" in (r["type"], k["type"])
            if same and (_box_iou(r["box"], k["box"]) > iou_thr or _contain(r["box"], k["box"]) > contain_thr):
                drop = True
                break
        if not drop:
            out.append(r)
    return out


_PRIO = {"hough": 0, "ocr": 1, "text_cc": 2, "gdino": 3, "colour": 4, "sam2": 5, "fft": 6}


def nms_priority(regs: list, iou_thr: float = 0.5, contain_thr: float = 0.85, keep_text_in_graphic: bool = False) -> list:
    """Class-agnostic NMS with a source priority (hough > ocr > text_cc > gdino > colour > sam2).
    colour_block regions are exempt (they describe the fabric, not a print).
    keep_text_in_graphic (P15b fix a): a text box that merely lies inside a bigger non-text box (a caption under
    a print) is not suppressed by containment; only real overlap (IoU) suppresses it."""
    keep_blocks = [r for r in regs if r.get("type") == "colour_block"]
    rest = sorted([r for r in regs if r.get("type") != "colour_block"],
                  key=lambda r: (_PRIO.get(r.get("source", ""), 9), -r.get("confidence", 0)))
    out = []
    for r in rest:
        def _hit(k):
            if _box_iou(r["box"], k["box"]) > iou_thr:
                return True
            if keep_text_in_graphic and r.get("type") == "text" and (k.get("type") != "text" or r.get("split")):
                return False        # caption inside a print, or a separate text line split out of a bigger text box
            return _contain(r["box"], k["box"]) > contain_thr
        if any(_hit(k) for k in out):
            continue
        out.append(r)
    return out + keep_blocks


def _gdino_regions(P: Prep, raw: list, stripes: list, D: np.ndarray) -> list:
    """Clean Grounding DINO output: class-agnostic NMS on score, drop near-whole-garment boxes,
    keep 'text' as is, keep 'stripes' only when the Hough detector agrees, otherwise label by size rules."""
    ys, xs = np.nonzero(P.mask)
    gbox_area = float((xs.max() - xs.min()) * (ys.max() - ys.min()))
    raw = sorted(raw, key=lambda r: -r["confidence"])
    kept = []
    for r in raw:
        a = (r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1])
        if a > 0.6 * gbox_area or r["confidence"] < 0.3:
            continue
        if any(_box_iou(r["box"], k["box"]) > 0.6 for k in kept):
            continue
        kept.append(dict(r))
    out = []
    for r in kept:
        t = r["type"]
        if t == "stripes" and not any(_box_iou(r["box"], s_["box"]) > 0.3 for s_ in stripes):
            t = "any"
        if t in ("logo", "graphic", "any"):
            t = rule_label(P, r["box"], D) if t == "any" or True else t
        r["type"] = t
        out.append(r)
    return out


# ───────────────────────────── P15b fix b: split merged text lines ─────────────────────────────

def split_text_lines(P: Prep, regs: list, small_frac: float = 0.5, min_small: int = 2, pad_frac: float = 0.01) -> list:
    """An OCR / text box that holds two lines of very different glyph size (a big word and a small script line)
    is split into one box per line.  Inside the box the ink (deltaE2000 > 12 from the local fabric) is cut into
    connected pieces; pieces shorter than `small_frac` of the tallest piece form the small line.  A split needs
    >= `min_small` small pieces laid out like a text line (wider than 1.4x its height) that are tiny compared with
    the big line; otherwise the box is returned unchanged.  Both new boxes are the tight boxes of their ink."""
    out = []
    ink_all = (P.dev > 12.0) & P.inner
    H, W = ink_all.shape
    for r in regs:
        if r.get("type") != "text" or r.get("source") not in ("ocr", "text_cc"):
            out.append(r)
            continue
        x0, y0, x1, y1 = [int(round(v)) for v in r["box"]]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < 8 or y1 - y0 < 8:
            out.append(r)
            continue
        n, cc, st, _ = cv2.connectedComponentsWithStats(ink_all[y0:y1, x0:x1].astype(np.uint8))
        comps = [st[i] for i in range(1, n) if st[i, 4] >= 2]
        if len(comps) < min_small + 1:
            out.append(r)
            continue
        hmax = max(int(c[3]) for c in comps)
        big = [c for c in comps if c[3] >= small_frac * hmax]
        small = [c for c in comps if c[3] < small_frac * hmax]

        def tight(cs):
            xa = min(int(c[0]) for c in cs)
            ya = min(int(c[1]) for c in cs)
            xb = max(int(c[0] + c[2]) for c in cs)
            yb = max(int(c[1] + c[3]) for c in cs)
            return xa, ya, xb, yb

        if len(small) < min_small or not big:
            out.append(r)
            continue
        sb, bb = tight(small), tight(big)
        sw, sh = sb[2] - sb[0], max(1, sb[3] - sb[1])
        big_area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        if sw < 1.4 * sh or sw * sh > 0.25 * big_area:
            out.append(r)
            continue
        pad = max(1, int(round(pad_frac * P.diag)))
        for b in (bb, sb):
            out.append({**r, "split": True,
                        "box": [max(0, x0 + b[0] - pad), max(0, y0 + b[1] - pad), min(W, x0 + b[2] + pad), min(H, y0 + b[3] + pad)]})
    return out


# ───────────────────────────── P15b: zero-shot relabelling (SigLIP 2) ─────────────────────────────

RELABEL_MODEL = "google/siglip2-base-patch16-224"
RELABEL_DEVICE = None          # None = cuda when available, else cpu.  The CALLER guards the GPU (gpu_lock).
RELABEL_PAD = 0.15
RELABEL_CLASSES = ["text", "graphic", "logo", "stripes", "pattern", "plain"]
RELABEL_PROMPTS = {
    "text": "a t-shirt with text",
    "graphic": "a t-shirt with a graphic print",
    "logo": "a t-shirt with a small logo",
    "stripes": "a t-shirt with stripes",
    "pattern": "a t-shirt with an all-over pattern",
    "plain": "a plain t-shirt",
}
_LABELLER = None


class _Labeller:
    """Zero-shot region typer: SigLIP 2 (base, patch16-224), one prompt per class, loaded once and reused."""

    def __init__(self, device: str | None = None):
        import torch
        from transformers import AutoModel, AutoProcessor
        self.torch = torch
        self.dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.proc = AutoProcessor.from_pretrained(RELABEL_MODEL)
        self.model = AutoModel.from_pretrained(
            RELABEL_MODEL, torch_dtype=torch.float16 if self.dev == "cuda" else torch.float32).to(self.dev).eval()
        self.text = None
        self._text_feats()

    def _to_cpu(self):
        self.dev = "cpu"
        self.model = self.model.float().to("cpu")
        self.text = None

    def _text_feats(self):
        torch = self.torch
        with torch.no_grad():
            t = self.proc(text=[RELABEL_PROMPTS[c] for c in RELABEL_CLASSES], padding="max_length", max_length=64,
                          return_tensors="pt").to(self.dev)
            f = self.model.get_text_features(**t)
        self.text = torch.nn.functional.normalize(f.float(), dim=-1)

    def probs(self, crop_rgb: np.ndarray) -> np.ndarray:
        from PIL import Image
        torch = self.torch
        for attempt in (0, 1):
            try:
                if self.text is None:
                    self._text_feats()
                with torch.no_grad():
                    inp = self.proc(images=Image.fromarray(crop_rgb), return_tensors="pt").to(self.dev)
                    inp = {k: v.half() if (self.dev == "cuda" and v.dtype == torch.float32) else v for k, v in inp.items()}
                    f = torch.nn.functional.normalize(self.model.get_image_features(**inp).float(), dim=-1)
                    return torch.softmax((f @ self.text.T).squeeze(0) * 100, -1).cpu().numpy()
            except RuntimeError:          # e.g. CUDA out of memory: finish on the CPU
                if attempt == 1 or self.dev == "cpu":
                    raise
                self._to_cpu()


def get_labeller() -> "_Labeller":
    """The shared SigLIP 2 labeller (loaded lazily, once)."""
    global _LABELLER
    if _LABELLER is None:
        try:
            _LABELLER = _Labeller(RELABEL_DEVICE)
        except RuntimeError:              # CUDA unavailable / out of memory at load time: CPU fallback
            _LABELLER = _Labeller("cpu")
    return _LABELLER


def release_labeller() -> None:
    """Free the labeller and its GPU memory (call before leaving the caller's gpu_lock)."""
    global _LABELLER
    import gc
    _LABELLER = None
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def _crop_padded(rgb: np.ndarray, box, pad: float = RELABEL_PAD) -> np.ndarray:
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    xa, xb = max(0, int(x0 - pad * bw)), min(w, int(x1 + pad * bw))
    ya, yb = max(0, int(y0 - pad * bh)), min(h, int(y1 + pad * bh))
    return rgb[ya:max(yb, ya + 1), xa:max(xb, xa + 1)]


def relabel_regions(rgb: np.ndarray, regs: list, labeller: "_Labeller | None" = None) -> list:
    """Re-type every region (boxes in the pixels of `rgb`) with the zero-shot labeller; colour_block regions keep
    their type; a region predicted "plain" is dropped.  Falls back to the input regions if the model is unavailable."""
    if not any(r["type"] != "colour_block" for r in regs):
        return regs
    try:
        L = labeller or get_labeller()
    except Exception as exc:  # noqa: BLE001  - model missing: keep the rule-based types
        import warnings
        warnings.warn(f"relabelling skipped ({type(exc).__name__}: {exc})")
        return regs
    out = []
    for r in regs:
        if r["type"] == "colour_block":
            out.append(r)
            continue
        p = L.probs(_crop_padded(rgb, r["box"]))
        t = RELABEL_CLASSES[int(p.argmax())]
        if t == "plain":
            continue
        out.append({**r, "type": t, "source": r.get("source", "") + "+siglip2"})
    return out


# ───────────────────────────── top-level ─────────────────────────────

METHODS = ("v4_relabel", "v4_nofix", "v3_fix", "v3_combo", "b_classical", "c_colour", "d_texture", "d_stripes", "e_text", "f_sam2", "g_gdino", "h_combo", "v2_combo")


def _finish(P: Prep, regs: list, D: np.ndarray, rule_types: bool = True) -> list:
    out = []
    for r in regs:
        t = r.get("type")
        if t is None or t == "any":
            t = rule_label(P, r["box"], D) if rule_types else "graphic"
        out.append({**{k: v for k, v in r.items() if k not in ("mask",)}, "type": t, "_mask": r.get("mask")})
    return out


def to_original(P: Prep, regs: list, keep_mask: bool = False) -> list:
    res = []
    for r in regs:
        o = {"box": _to_orig(P, r["box"]), "type": r["type"], "confidence": float(r.get("confidence", 0.5)), "source": r.get("source", "")}
        if keep_mask and r.get("_mask") is not None:
            o["_mask_work"] = r["_mask"]
        res.append(o)
    return res


def _ocr_cached(P: Prep, cache: dict) -> list:
    if "ocr" not in cache:
        try:
            cache["ocr"] = propose_ocr(P)
        except Exception:  # noqa: BLE001  - no weights / no memory: fall back to the connected-component text detector
            cache["ocr"] = []
    return [dict(r) for r in cache["ocr"]]


def detect_regions(rgb: np.ndarray, mask: np.ndarray, method: str = "h_combo", prep: Prep | None = None,
                   cache: dict | None = None) -> list:
    """Detect and label the design regions of one garment.

    rgb: HxWx3 uint8 RGB.  mask: HxW bool garment mask.  Returns boxes in input pixels.
    `cache` (optional dict) lets expensive proposals (sam2) be passed in/out between methods.
    """
    v3_flow = method in ("v3_combo", "v3_fix", "v4_nofix", "v4_relabel")
    fixes = method in ("v3_fix", "v4_relabel")          # P15b fixes (text in graphic, split merged text lines)
    relabel = method in ("v4_nofix", "v4_relabel")      # P15b zero-shot SigLIP 2 relabelling
    P = prep or prepare(rgb, mask)
    cache = cache if cache is not None else {}
    per = periodicity(P)
    P.info["periodicity"] = per
    colour = propose_colour(P)
    D = P.info.get("dev_mask", np.zeros(P.inner.shape, bool))
    plain = P.info["dev_cov"] < 0.004 and not per["periodic"]
    regs: list = []
    if method == "b_classical":
        regs = propose_classical(P)
    elif method == "c_colour":
        regs = colour
    elif method == "d_texture":
        regs = propose_texture(P)
    elif method == "d_stripes":
        regs = propose_stripes(P)
    elif method == "e_text":
        regs = _ocr_cached(P, cache) or propose_text_cc(P)
    elif method == "g_gdino":
        regs = cache.get("gdino") or propose_gdino(P)
        cache["gdino"] = regs
    elif method == "f_sam2":
        regs = cache.get("sam2") or propose_sam2(P)
        cache["sam2"] = regs
    elif v3_flow:
        stripes = propose_stripes(P)
        text = _ocr_cached(P, cache) or propose_text_cc(P)
        if not plain:
            gd = cache.get("gdino")
            if gd is None:
                try:
                    gd = propose_gdino(P)
                except Exception:  # noqa: BLE001  - model not available: continue without it
                    gd = []
                cache["gdino"] = gd
            gdr = _gdino_regions(P, gd, stripes, D)
            regs += gdr
            # a (confident) Grounding DINO text box that contains a much smaller OCR fragment replaces it
            text = [t for t in text if not any(g["type"] == "text" and _contain(t["box"], g["box"]) > 0.9 and
                                               (t["box"][2] - t["box"][0]) * (t["box"][3] - t["box"][1]) < 0.4 * (g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1])
                                               for g in gdr)]
        if fixes:
            text = split_text_lines(P, list(text))
        regs += list(text) + list(stripes) + list(colour) + propose_blocks(P)
        if per["periodic"] and P.info["dev_cov"] > 0.35 and not stripes:
            ys, xs = np.nonzero(P.inner)
            regs.append({"box": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], "mask": P.inner,
                         "type": "pattern", "source": "fft", "confidence": 0.7})
    elif method in ("h_combo", "v2_combo"):
        stripes = propose_stripes(P)
        text = _ocr_cached(P, cache) or propose_text_cc(P)
        regs = list(text) + list(stripes)
        # colour regions that are not inside text / stripes
        for r in colour:
            if any(_contain(r["box"], k["box"]) > 0.6 for k in regs):     # colour region mostly inside a text / stripes box
                continue
            regs.append(r)
        if method == "h_combo" and ("sam2" in cache):
            for r in cache["sam2"]:
                if not any(_box_iou(r["box"], k["box"]) > 0.3 for k in regs):
                    regs.append(r)
        regs += propose_blocks(P)
        # all-over periodic print
        if per["periodic"] and P.info["dev_cov"] > 0.35 and not stripes:
            ys, xs = np.nonzero(P.inner)
            regs.append({"box": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], "mask": P.inner,
                         "type": "pattern", "source": "fft", "confidence": 0.7})
    else:
        raise ValueError(method)
    for r in regs:
        r.setdefault("type", "any")
    if method in ("v2_combo", "h_combo") and plain and not [r for r in regs if r["type"] in ("stripes", "pattern")]:
        regs = [r for r in regs if r["type"] == "colour_block"]
    if v3_flow:
        for r in regs:
            r.setdefault("type", "any")
        if plain:
            regs = [r for r in regs if r["type"] == "colour_block"]
        regs = nms_priority(regs, keep_text_in_graphic=fixes)
    else:
        regs = nms_merge(regs)
    regs = _finish(P, regs, D)
    res = to_original(P, regs, keep_mask=False)
    if relabel:
        res = relabel_regions(rgb, res)
    return res
