"""P00 meta-evaluation, step 1: damage tests for the candidate metrics.

Take a correct answer (the reference), damage it in a controlled way, and check which
metrics get worse, and by how much. A good primary metric must (1) get worse for every
kind of damage we care about, (2) get worse more for bigger damage (monotonic), and
(3) not over-react to tiny, harmless changes.

Damages:
  outline: border shift (dilate/erode by 0.5/1/2 % of the diagonal), leakage blob at the side
           (simulates arms or background, 5/10/20 % of the garment area), a missing chunk
           (5/10/20 %), jagged border noise.
  colour:  shift every fabric colour by ΔE 2/5/10/20; drop one fabric colour (c_003 block);
           add a spurious 10 % colour; drop the print colour.
  design:  drop one region; add one false region; shift boxes by 10/25/50 % of their width;
           wrong type on all regions.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p00_metric_sanity.py
Out:  results/metric_sanity.csv
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from skimage.color import lab2rgb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import (CLOTHS, RESULTS, design_scores, fabric_colour_scores, load_mask,  # noqa: E402
                      load_reference, mask_metrics, palette_distance)

rng = np.random.default_rng(0)


def lab_hex(lab):
    rgb = np.clip(lab2rgb(np.array(lab, float)[None, None, :])[0, 0] * 255, 0, 255).round().astype(int)
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def outline_damages(ref: np.ndarray):
    h, w = ref.shape
    diag = np.hypot(h, w)
    m = ref.astype(np.uint8)
    yield "identity", ref
    for pct in (0.5, 1.0, 2.0):
        k = max(1, int(round(pct / 100 * diag)))
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        yield f"dilate_{pct}%", cv2.dilate(m, ker) > 0
        yield f"erode_{pct}%", cv2.erode(m, ker) > 0
    ys, xs = np.nonzero(ref)
    area = ref.sum()
    cx = int(xs.max())
    cy = int(np.median(ys))
    for frac in (0.05, 0.10, 0.20):
        r = int(np.sqrt(frac * area / np.pi))
        blob = np.zeros_like(m)
        cv2.circle(blob, (min(w - 1, cx), cy), r, 1, -1)
        yield f"leak_blob_{int(frac * 100)}%", (m | blob) > 0
        hole = np.zeros_like(m)
        cv2.circle(hole, (int(np.median(xs)), int(np.percentile(ys, 75))), r, 1, -1)
        yield f"missing_chunk_{int(frac * 100)}%", (m & (1 - hole)) > 0
    noise = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), max(1.0, diag / 300))
    border = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((9, 9), np.uint8)) > 0
    jag = ref.copy()
    jag[border & (noise > 0.15)] = True
    jag[border & (noise < -0.15)] = False
    yield "jagged_border", jag


def colour_damages(pal):
    yield "identity", pal
    for d in (2, 5, 10, 20):
        new = []
        for e in pal:
            lab = np.array(e["lab"], float)
            if e["role"].startswith("fabric"):
                lab = lab + np.array([0, d / np.sqrt(2), d / np.sqrt(2)])  # roughly ΔE d (CIE76)
            new.append({**e, "lab": lab.tolist(), "hex": lab_hex(lab)})
        yield f"shift_fabric_~{d}", new
    fabrics = [e for e in pal if e["role"].startswith("fabric")]
    if len(fabrics) > 1:
        drop = min(fabrics, key=lambda e: e["share"])
        rest = [e for e in pal if e is not drop]
        s = sum(e["share"] for e in rest)
        yield "drop_one_fabric_block", [{**e, "share": e["share"] / s} for e in rest]
    spur = [{**e, "share": e["share"] * 0.9} for e in pal] + [{"role": "spurious", "lab": [60, 60, -60], "hex": lab_hex([60, 60, -60]), "share": 0.1}]
    yield "add_spurious_10%", spur
    prints = [e for e in pal if e["role"] == "print"]
    if prints:
        rest = [e for e in pal if e["role"] != "print"]
        s = sum(e["share"] for e in rest)
        yield "drop_print_colour", [{**e, "share": e["share"] / s} for e in rest]


def design_damages(regs, w, h):
    yield "identity", regs
    real = [r for r in regs if r["type"] != "colour_block"]
    if real:
        yield "drop_one_region", [r for r in regs if r is not real[0]]
    fake = {"box": [0.05 * w, 0.75 * h, 0.25 * w, 0.85 * h], "type": "logo"}
    yield "add_false_region", regs + [fake]
    for f in (0.1, 0.25, 0.5):
        out = []
        for r in regs:
            x0, y0, x1, y1 = r["box"]
            dx = f * (x1 - x0)
            out.append({**r, "box": [x0 + dx, y0, x1 + dx, y1]})
        yield f"shift_boxes_{int(f * 100)}%", out
    yield "wrong_types", [{**r, "type": "pattern" if r["type"] != "pattern" else "text"} for r in regs]


def main():
    refs = load_reference()
    rows = []
    for c in CLOTHS:
        ref = refs[c]
        w, h = ref["size_wh"]
        g = load_mask(Path(ref["garment_mask"]), (h, w))
        for name, dm in outline_damages(g):
            for k, v in mask_metrics(dm, g).items():
                rows.append({"area": "outline", "cloth": c, "damage": name, "metric": k, "value": v})
        for name, pal in colour_damages(ref["palette"]):
            base = max((e for e in pal if e["role"].startswith("fabric")), key=lambda e: e["share"])["hex"]
            for k, v in {**palette_distance(pal, ref["palette"]), **fabric_colour_scores(pal, ref["palette"], base)}.items():
                rows.append({"area": "colour", "cloth": c, "damage": name, "metric": k, "value": v})
        regs = [{"box": d["box_px"], "type": d["type"]} for d in ref["designs"]]
        for name, pr in design_damages(regs, w, h):
            for k, v in design_scores(pr, regs, g, 0.3).items():
                if k in ("n_ref", "n_pred"):
                    continue
                rows.append({"area": "design", "cloth": c, "damage": name, "metric": k, "value": v})
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "metric_sanity.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["area", "cloth", "damage", "metric", "value"])
        wr.writeheader()
        wr.writerows(rows)
    # summary: mean over cloths per damage and metric
    import pandas as pd
    df = pd.DataFrame(rows)
    for area in ("outline", "colour", "design"):
        t = df[df.area == area].pivot_table(index="damage", columns="metric", values="value", aggfunc="mean")
        keep = {"outline": ["iou", "boundary_f@0.5%", "boundary_f@1.0%", "boundary_f@2.0%", "hd95_pct_diag", "leakage", "miss"],
                "colour": ["palette_de", "ref_share_matched", "base_colour_de", "all_fabric_colours_found_de"],
                "design": ["f1", "pixel_iou", "precision", "recall", "type_accuracy_matched", "colour_block_found"]}[area]
        t = t[[k for k in keep if k in t.columns]]
        print(f"\n== {area} (mean over cloths)")
        print(t.round(3).to_string())
        t.round(4).to_csv(RESULTS / f"metric_sanity_{area}_summary.csv")


if __name__ == "__main__":
    main()
