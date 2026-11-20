"""P03 part A: image enhancement, restoration and shading removal on the 5 Mirra photos, plus a
fold-flatness study on VITON-HD product photos.

Run from the repo root:
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p03_enhance_study.py [--viton 50]

Outputs under out/p03_filters/:
    enhance/<method>/<cloth>.png            single methods on the clean photo (RGBA, garment mask as alpha)
    enhance/<method>/gallery.jpg            original (top) vs enhanced (bottom), the 5 photos
    enhance/gallery_<cloth>.jpg             one photo, every single method
    enhance_chains/<chain>/<cloth>.jpg      chains (wb -> denoise -> shading -> contrast)
    enhance_degraded/<deg>/<method>/<cloth>.jpg   single methods on synthetically degraded photos
    enhance_scores.csv                      one row per (cloth, degradation, method)
    viton_flatness.csv                      one row per (VITON-HD image, method)
Metrics: de2000 = share-weighted CIEDE2000 between the fabric colours read from the fabric-only
area and the reference fabric palette; std_L = pooled within-cluster std of L (lower = flatter fabric);
design_std_L = std of L inside the design boxes (shows whether a method erases print).
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import time

import cv2
import numpy as np

from p03_common import (CLOTHS, OUT, SEED, ce, crop_box, delta_e_fabric, design_contrast,
                        label_tile, lab_pixels, load_case, save_rgba)

THUMB = 130
JPG = [cv2.IMWRITE_JPEG_QUALITY, 85]
SINGLES = [k for k in ce.ENHANCERS if k != "none"]
WB = ["none", "grey_world"]
DEN = ["none", "denoise_bilateral9", "denoise_nlm"]
SHD = ["none", "shading_divide", "shading_divide_regions", "shading_homomorphic"]
CON = ["none", "clahe_L_2"]
SHORT = {"none": "", "grey_world": "gw", "denoise_bilateral9": "bil9", "denoise_nlm": "nlm",
         "shading_divide": "shdiv", "shading_divide_regions": "shreg", "shading_homomorphic": "homo", "clahe_L_2": "clahe"}
CHAINS = {}
for wb, dn, sh, co in itertools.product(WB, DEN, SHD, CON):
    steps = [s for s in (wb, dn, sh, co) if s != "none"]
    CHAINS["+".join(SHORT[s] for s in steps) or "none"] = steps
CHAINS.pop("none")


def degrade(rgb, kind, mask):
    f = rgb.astype(np.float32)
    h, w = rgb.shape[:2]
    if kind == "clean":
        return rgb.copy()
    if kind == "cast":                      # warm colour cast (white-balance error)
        f = f * np.array([1.2, 1.0, 0.8], np.float32)
    elif kind == "dark":                    # under-exposure
        f = 255.0 * (f / 255.0) ** 1.8
    elif kind == "noise":                   # sensor noise, sigma 12 grey levels
        rng = np.random.default_rng(SEED)
        f = f + rng.normal(0, 12, f.shape).astype(np.float32)
    elif kind == "shade":                   # uneven lighting: horizontal ramp + soft dark blob
        xx = np.linspace(0.6, 1.2, w, dtype=np.float32)[None, :]
        yy, xg = np.mgrid[0:h, 0:w].astype(np.float32)
        blob = 1.0 - 0.35 * np.exp(-(((xg - 0.3 * w) / (0.2 * w)) ** 2 + ((yy - 0.6 * h) / (0.2 * h)) ** 2))
        f = f * (xx * blob)[..., None]
    else:
        raise ValueError(kind)
    return np.clip(f, 0, 255).astype(np.uint8)


DEGS = ["clean", "cast", "dark", "noise", "shade"]


def thumb(rgb, mask, box):
    y0, y1, x0, x1 = box
    c = np.where(mask[..., None], rgb, 128)[y0:y1, x0:x1]
    s = THUMB / max(c.shape[:2])
    c = cv2.resize(c, (max(1, int(c.shape[1] * s)), max(1, int(c.shape[0] * s))), interpolation=cv2.INTER_AREA)
    t = np.full((THUMB, THUMB, 3), 128, np.uint8)
    t[:c.shape[0], :c.shape[1]] = c
    return cv2.cvtColor(t, cv2.COLOR_RGB2BGR)


def run_mirra():
    rows = []
    cases = {c: load_case(c) for c in CLOTHS}
    boxes = {c: crop_box(cases[c]["mask"]) for c in CLOTHS}
    gal_method = {m: {} for m in SINGLES}          # method -> cloth -> thumb (clean)
    for cloth in CLOTHS:
        case = cases[cloth]
        rgb, mask = case["rgb"], case["mask"]
        tiles_photo = [("original", thumb(rgb, mask, boxes[cloth]))]
        for deg in DEGS:
            src = degrade(rgb, deg, mask)
            base_de, base_std = delta_e_fabric(src, case)
            base_dc = design_contrast(src, case)
            rows.append(dict(cloth=cloth, degradation=deg, kind="single", method="none",
                             de2000=round(base_de, 4), std_L=round(base_std, 4),
                             design_std_L=round(base_dc, 4) if base_dc == base_dc else "", time_ms=0.0))
            for m in SINGLES:
                t0 = time.perf_counter()
                out = ce.ENHANCERS[m](src, mask)
                ms = (time.perf_counter() - t0) * 1000
                out = np.where(mask[..., None], out, 0).astype(np.uint8)
                de, sd = delta_e_fabric(out, case)
                dc = design_contrast(out, case)
                rows.append(dict(cloth=cloth, degradation=deg, kind="single", method=m,
                                 de2000=round(de, 4), std_L=round(sd, 4),
                                 design_std_L=round(dc, 4) if dc == dc else "", time_ms=round(ms, 1)))
                if deg == "clean":
                    save_rgba(OUT / "enhance" / m / f"{cloth}.png", out, mask)
                    th = thumb(out, mask, boxes[cloth])
                    gal_method[m][cloth] = th
                    tiles_photo.append((m, th))
                else:
                    p = OUT / "enhance_degraded" / deg / m / f"{cloth}.jpg"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(p), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), JPG)
            if deg != "clean":
                p = OUT / "enhance_degraded" / deg / "input" / f"{cloth}.jpg"
                p.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(p), cv2.cvtColor(np.where(mask[..., None], src, 0), cv2.COLOR_RGB2BGR), JPG)
            # chains
            for name, steps in CHAINS.items():
                t0 = time.perf_counter()
                out = ce.apply_chain(src, steps, mask)
                ms = (time.perf_counter() - t0) * 1000
                out = np.where(mask[..., None], out, 0).astype(np.uint8)
                de, sd = delta_e_fabric(out, case)
                dc = design_contrast(out, case)
                rows.append(dict(cloth=cloth, degradation=deg, kind="chain", method=name,
                                 de2000=round(de, 4), std_L=round(sd, 4),
                                 design_std_L=round(dc, 4) if dc == dc else "", time_ms=round(ms, 1)))
                if deg == "clean":
                    p = OUT / "enhance_chains" / name / f"{cloth}.jpg"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(p), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), JPG)
        # per photo gallery of single methods (clean)
        n = len(tiles_photo)
        cols = 7
        nr = (n + cols - 1) // cols
        G = np.full((nr * (THUMB + 16), cols * THUMB, 3), 255, np.uint8)
        for i, (nm, th) in enumerate(tiles_photo):
            r, c = divmod(i, cols)
            G[r * (THUMB + 16) + 16: r * (THUMB + 16) + 16 + THUMB, c * THUMB:(c + 1) * THUMB] = th
            cv2.putText(G, nm, (c * THUMB + 2, r * (THUMB + 16) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.imwrite(str(OUT / "enhance" / f"gallery_{cloth}.jpg"), G, JPG)
        print(cloth, "done", flush=True)
    # per method gallery: originals over enhanced
    orig = {c: thumb(cases[c]["rgb"], cases[c]["mask"], boxes[c]) for c in CLOTHS}
    for m in SINGLES:
        top = np.hstack([orig[c] for c in CLOTHS])
        bot = np.hstack([gal_method[m][c] for c in CLOTHS])
        G = np.vstack([np.full((16, top.shape[1], 3), 255, np.uint8), top, bot])
        cv2.putText(G, f"{m}  (top: original, bottom: enhanced)", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.imwrite(str(OUT / "enhance" / m / "gallery.jpg"), G, JPG)
    with open(OUT / "enhance_scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote enhance_scores.csv", len(rows))


# ------------------------------------------------------------------ VITON-HD flatness
def run_viton(n):
    import glob
    import pyarrow.parquet as pq
    files = sorted(glob.glob(str(OUT.parent.parent / "data" / "vitonhd_test" / "data" / "*.parquet")))
    methods = {m: [m] for m in ["grey_world", "denoise_median5", "denoise_bilateral9", "denoise_nlm",
                                  "hist_eq_L", "clahe_L_2", "gamma_auto", "retinex_ssr", "retinex_msr",
                                  "shading_divide", "shading_divide_regions", "shading_homomorphic"]}
    methods["bil9+shdiv"] = ["denoise_bilateral9", "shading_divide"]
    methods["bil9+shreg"] = ["denoise_bilateral9", "shading_divide_regions"]
    methods["bil9+homo"] = ["denoise_bilateral9", "shading_homomorphic"]
    methods["gw+bil9+shdiv"] = ["grey_world", "denoise_bilateral9", "shading_divide"]
    methods["gw+bil9+shdiv+clahe"] = ["grey_world", "denoise_bilateral9", "shading_divide", "clahe_L_2"]
    rows, done = [], 0
    pf = pq.ParquetFile(files[0])
    for batch in pf.iter_batches(batch_size=8, columns=["cloth", "cloth_mask"]):
        for rec in batch.to_pylist():
            if done >= n:
                break
            img = cv2.imdecode(np.frombuffer(rec["cloth"]["bytes"], np.uint8), cv2.IMREAD_COLOR)
            msk = cv2.imdecode(np.frombuffer(rec["cloth_mask"]["bytes"], np.uint8), cv2.IMREAD_GRAYSCALE)
            h, w = img.shape[:2]
            s = min(1.0, 768 / max(h, w))
            if s < 1:
                img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
                msk = cv2.resize(msk, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mask = msk > 127
            band = max(3, int(round(0.03 * max(mask.shape))))
            inner = cv2.erode(mask.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band + 1,) * 2)) > 0
            lab_in = lab_pixels(rgb, inner)
            med_ab = np.median(lab_in[:, 1:], axis=0)
            fab = np.zeros(mask.shape, bool)
            fab[inner] = np.hypot(lab_in[:, 1] - med_ab[0], lab_in[:, 2] - med_ab[1]) < 12   # same hue as the main fabric
            if fab.sum() < 2000:
                done += 1
                continue

            def stats(im):
                lab = lab_pixels(im, fab)
                return float(lab[:, 0].std()), np.median(lab, axis=0)

            s0, m0 = stats(rgb)
            rows.append(dict(img=done, method="none", std_L=round(s0, 4), ratio=1.0, de_shift=0.0, time_ms=0))
            from skimage.color import deltaE_ciede2000
            for name, steps in methods.items():
                t0 = time.perf_counter()
                out = ce.apply_chain(rgb, steps, mask)
                ms = (time.perf_counter() - t0) * 1000
                s1, m1 = stats(out)
                de = float(deltaE_ciede2000(m0[None], m1[None])[0])
                rows.append(dict(img=done, method=name, std_L=round(s1, 4), ratio=round(s1 / max(s0, 1e-6), 4),
                                 de_shift=round(de, 4), time_ms=round(ms, 1)))
            done += 1
            print("viton", done, flush=True)
        if done >= n:
            break
    with open(OUT / "viton_flatness.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote viton_flatness.csv", len(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--viton", type=int, default=0)
    ap.add_argument("--skip-mirra", action="store_true")
    a = ap.parse_args()
    if not a.skip_mirra:
        run_mirra()
    if a.viton:
        run_viton(a.viton)
