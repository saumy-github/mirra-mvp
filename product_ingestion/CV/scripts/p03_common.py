"""Shared helpers for the P03 filter study: photo loading, scoring regions, colour reading.

Photos larger than MAX_SIDE on the longest side are shrunk with INTER_AREA (c_001, c_003);
the small photos (c_002, c_004, c_005) stay at native size. All scoring is done at this working size.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "product_ingestion"))
sys.path.insert(0, str(HERE))
import cv_enhance as ce  # noqa: E402

CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
REF = ROOT / "out" / "p00_baseline" / "reference"
OUT = ROOT / "out" / "p03_filters"
MAX_SIDE = 768
SEED = 0


def disk(r: int):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def load_case(cloth: str, max_side: int = MAX_SIDE) -> dict:
    labels = json.loads((REF / "labels.json").read_text(encoding="utf-8"))["cloths"][cloth]
    f = glob.glob(str(REPO / "product_ingestion" / "input" / cloth / "*"))[0]
    bgr = cv2.imread(f, cv2.IMREAD_COLOR)
    mask = cv2.imread(str(REF / cloth / "garment_mask.png"), cv2.IMREAD_GRAYSCALE)
    h, w = bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1.0:
        bgr = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    mask = mask > 127
    H, W = mask.shape
    case = {"cloth": cloth, "rgb": rgb, "mask": mask, "labels": labels, "shape": (H, W)}
    band = max(3, int(round(0.012 * max(H, W))))
    inner = cv2.erode(mask.astype(np.uint8), disk(band)) > 0
    boxes = []
    for d in labels["designs"]:
        x0, y0, x1, y1 = d["box"]
        boxes.append((d["type"], int(x0 / 100 * W), int(y0 / 100 * H), int(x1 / 100 * W), int(y1 / 100 * H)))
    Dbox = np.zeros((H, W), np.uint8)       # print-type design boxes (not colour blocks)
    for t, x0, y0, x1, y1 in boxes:
        if t != "colour_block":
            Dbox[y0:y1, x0:x1] = 1
    D = (Dbox > 0) & inner
    margin = band
    Ddil = cv2.dilate(Dbox, disk(margin)) > 0
    F = inner & ~Ddil
    split = labels.get("colour_block_split_y")
    ignore = np.zeros((H, W), bool)
    if split is not None:                  # boundary between two colour blocks: real colour edge, not a print edge
        y = int(split / 100 * H)
        ignore[max(0, y - 2 * band): y + 2 * band, :] = True
        F &= ~ignore
    case.update(band=band, inner=inner, D=D, F=F, ignore=ignore,
                r_tol=max(1, int(round(0.005 * max(H, W)))))
    return case


def fabric_entries(case):
    return [e for e in case["labels"]["palette"] if e["role"].startswith("fabric")]


def retry_mem(fn):
    """Retry a function a few times on MemoryError (the machine is shared and short of RAM)."""
    import functools, gc, time as _t

    @functools.wraps(fn)
    def wrapper(*a, **k):
        for i in range(8):
            try:
                return fn(*a, **k)
            except MemoryError:
                gc.collect()
                _t.sleep(2 + i)
        return fn(*a, **k)
    return wrapper


@retry_mem
def lab_of(rgb_u8):
    return rgb2lab(rgb_u8.astype(np.float64) / 255.0)


def lab_pixels(rgb, mask):
    """Lab values of the masked pixels only, shape (N, 3) (saves memory)."""
    return lab_of(rgb[mask][None])[0]


def read_fabric_colour(rgb, case, k=None, seed=SEED):
    """Read the fabric colour(s) from the fabric-only area F with k-means in Lab (k = number of
    reference fabric colours). Returns (centres_lab [k,3], pooled within-cluster std of L,
    labels over F pixels)."""
    F = case["F"]
    lab = lab_pixels(rgb, F)
    k = k or len(fabric_entries(case))
    if k == 1:
        cen = np.median(lab, 0)[None]
        lab_idx = np.zeros(len(lab), int)
    else:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=k, n_init=3, random_state=seed).fit(lab[:: max(1, len(lab) // 20000)])
        cen = km.cluster_centers_
        lab_idx = km.predict(lab)
    res = []
    for i in range(len(cen)):
        sel = lab[lab_idx == i, 0]
        res.append((sel - sel.mean()) if len(sel) else np.zeros(0))
    pooled = float(np.concatenate(res).std()) if res else 0.0
    return cen, pooled


@retry_mem
def delta_e_fabric(rgb, case):
    """Share-weighted CIEDE2000 between the read fabric colours and the reference fabric palette
    (each reference entry matched to the nearest read colour). Also returns pooled std of L."""
    ents = fabric_entries(case)
    cen, std_L = read_fabric_colour(rgb, case, k=len(ents))
    tot = sum(e["share"] for e in ents)
    de = 0.0
    for e in ents:
        ref = np.array(e["lab"], float)
        d = deltaE_ciede2000(np.repeat(ref[None], len(cen), 0), cen)
        de += (e["share"] / tot) * float(d.min())
    return de, std_L


def design_contrast(rgb, case):
    """Std of luminance L inside the design boxes (0 when the photo has none)."""
    D = case["D"]
    if not D.any():
        return float("nan")
    return float(lab_pixels(rgb, D)[:, 0].std())


def edge_metrics(edges, case, thin=True):
    """Edge scores. edges: uint8/bool (H, W). With thin=True the edge map is first reduced to
    1-pixel lines (skeletonize), so detectors that output thick or blobby edges (Laplacian noise
    blobs, upsampled coarse pyramid levels) get no credit for thickness.
    recall  = share of design-box pixels within r_tol px of an edge pixel
    fa_cov  = share of plain-fabric pixels within r_tol px of an edge pixel
    precision = recall / (recall + fa_cov)   (area-normalised: equal-sized design and fabric regions)
    f1      = harmonic mean of precision and recall
    fer     = fold false-edge rate = edge pixels on plain fabric / plain-fabric pixels (percent)
    Only D (design boxes) and F (plain fabric, away from outline, design boxes and colour-block
    boundary) are scored; everything else is ignored."""
    e = (np.asarray(edges) > 0)
    if thin:
        from skimage.morphology import skeletonize
        e = skeletonize(e)
    e = e.astype(np.uint8)
    D, F = case["D"], case["F"]
    dil = cv2.dilate(e, disk(case["r_tol"])) > 0
    out = {"fer_pct": 100.0 * float((e > 0)[F].mean()) if F.any() else float("nan"),
           "fa_cov": float(dil[F].mean()) if F.any() else float("nan")}
    if D.any():
        rec = float(dil[D].mean())
        out["recall"] = rec
        out["design_edge_density_pct"] = 100.0 * float((e > 0)[D].mean())
        denom = rec + out["fa_cov"]
        prec = rec / denom if denom > 0 else 0.0
        out["precision"] = prec
        out["f1"] = 2 * prec * rec / (prec + rec) if prec + rec > 0 else 0.0
    else:
        out["recall"] = out["precision"] = out["f1"] = out["design_edge_density_pct"] = float("nan")
    return out


def save_rgba(path: Path, rgb, mask):
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.dstack([cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (mask * 255).astype(np.uint8)])
    cv2.imwrite(str(path), rgba)


def label_tile(tile_bgr, text, scale=0.4):
    cv2.putText(tile_bgr, text, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 255), 1, cv2.LINE_AA)
    return tile_bgr


def crop_box(mask, pad=4):
    ys, xs = np.where(mask)
    return max(0, ys.min() - pad), ys.max() + pad, max(0, xs.min() - pad), xs.max() + pad
