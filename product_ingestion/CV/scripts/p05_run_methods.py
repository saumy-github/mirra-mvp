"""P05: run every design-region method on the 5 Mirra photos and save predictions + overlays.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_run_methods.py [--methods a,b] [--masks oracle,v0mask] [--out try_name]

Writes  out/p05_design/<out>/methods[_v0mask]/<method>/<cloth>/design_regions.json  (+ mask.png)
and      .../overlays/<method>/<cloth>.jpg   (level 1 = garment outline, level 2 = labelled regions)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "product_ingestion"))
import cv_design_regions as cvd  # noqa: E402
from gpu_lock import gpu_lock  # noqa: E402
import step_04_0_design_extraction as s4  # noqa: E402

cvd.GPU_CTX = lambda: gpu_lock("p05")
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
COL = {"text": (255, 60, 60), "graphic": (60, 120, 255), "logo": (255, 0, 255), "stripes": (255, 160, 0),
       "colour_block": (0, 200, 0), "pattern": (0, 200, 200)}


def load_inputs():
    labels = json.loads((CV / "out/p00_baseline/reference/labels.json").read_text(encoding="utf-8"))["cloths"]
    data = {}
    for c in CLOTHS:
        e = labels[c]
        bgr = cv2.imread(e["image"], cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        mo = cv2.imread(e["garment_mask"], cv2.IMREAD_UNCHANGED)
        mo = mo[..., -1] if mo.ndim == 3 else mo
        mo = cv2.resize(mo, (w, h), interpolation=cv2.INTER_NEAREST) > 127
        v0p = REPO / "product_ingestion/output" / c / "s_001/001/image_info/base_garment.png"
        mv = cv2.imread(str(v0p), cv2.IMREAD_UNCHANGED)
        mv = cv2.resize(mv[..., 3], (w, h), interpolation=cv2.INTER_NEAREST) > 10
        data[c] = {"rgb": rgb, "oracle": mo, "v0mask": mv}
    return data


def draw_overlay(rgb, mask, regions, title=""):
    img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, (0, 255, 255), max(1, round(max(img.shape[:2]) / 400)))   # level 1 (yellow)
    t = max(1, round(max(img.shape[:2]) / 350))
    fs = max(0.35, max(img.shape[:2]) / 1100)
    for r in regions:
        x0, y0, x1, y1 = [int(round(v)) for v in r["box"]]
        col = COL.get(r["type"], (255, 255, 255))[::-1]
        cv2.rectangle(img, (x0, y0), (x1, y1), col, t)
        cv2.putText(img, r["type"], (x0 + 2, max(10, y0 + int(14 * fs * 2))), cv2.FONT_HERSHEY_SIMPLEX, fs, col, max(1, t - 1), cv2.LINE_AA)
    if title:
        cv2.putText(img, title, (4, int(18 * fs * 1.5)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), t + 2, cv2.LINE_AA)
        cv2.putText(img, title, (4, int(18 * fs * 1.5)), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), t, cv2.LINE_AA)
    return img


def run_method(method, rgb, mask, cache):
    if method == "v0":
        rgba = np.dstack([rgb, mask.astype(np.uint8) * 255])
        r = s4.extract_design(rgba, method="v0")
        return [{k: v for k, v in x.items()} for x in r.regions]
    regs = cvd.detect_regions(rgb, mask, method=method, cache=cache)
    return regs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="v0,b_classical,c_colour,d_texture,d_stripes,e_text,f_sam2,h_combo,v2_combo")
    ap.add_argument("--masks", default="oracle,v0mask")
    ap.add_argument("--out", default="try_01")
    args = ap.parse_args()
    root = CV / "out/p05_design" / args.out
    data = load_inputs()
    timing = {}
    for mk in args.masks.split(","):
        caches = {c: {} for c in CLOTHS}
        # sam2 first when needed so h_combo can reuse it
        methods = args.methods.split(",")
        if "f_sam2" in methods:
            methods = ["f_sam2"] + [m for m in methods if m != "f_sam2"]
        for m in methods:
            t0 = time.time()
            for c in CLOTHS:
                d = data[c]
                regs = run_method(m, d["rgb"], d[mk], caches[c])
                regs = [{"box": [round(float(v), 1) for v in r["box"]], "type": r["type"],
                         "confidence": round(float(r.get("confidence", 0)), 3), "source": r.get("source", "")} for r in regs]
                base = root / ("methods" if mk == "oracle" else "methods_v0mask") / m
                (base / c).mkdir(parents=True, exist_ok=True)
                (base / c / "design_regions.json").write_text(json.dumps(regs, indent=1), encoding="utf-8")
                cv2.imwrite(str(base / c / "mask.png"), d[mk].astype(np.uint8) * 255)
                ov = draw_overlay(d["rgb"], d[mk], regs, f"{m} ({mk})")
                od = root / ("overlays" if mk == "oracle" else "overlays_v0mask") / m
                od.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(od / f"{c}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 80])
            timing[f"{m}/{mk}"] = round(time.time() - t0, 1)
            print(m, mk, f"{timing[f'{m}/{mk}']}s", flush=True)
    (root / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
