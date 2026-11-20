"""P03 part B: smoothing filter x edge detector study on the 5 Mirra photos.

Run from the repo root:
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p03_edge_study.py [--pre none|clahe_L_2|shading_divide|shading_homomorphic|grey_world|...] [--tag NAME]

For every (smoothing filter, kernel) x (edge detector) it saves the edge map of every photo to
out/p03_filters/<edges_dir>/<filter>_<k>__<detector>/<cloth>.png (white edges on black, inside the
garment mask), one gallery per photo (rows = filters, columns = detectors) and appends scores to
out/p03_filters/<edge_scores>.csv.
--pre applies one enhancement from cv_enhance.ENHANCERS to the colour photo before greying/smoothing
(outputs go to edges_pre/<pre>/ and edge_scores_pre.csv).
"""
from __future__ import annotations

import argparse
import csv
import time

import cv2
import numpy as np

from p03_common import (CLOTHS, OUT, ce, crop_box, edge_metrics, label_tile, load_case)

THUMB = 150


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre", default="none")
    args = ap.parse_args()
    pre = args.pre
    if pre == "none":
        edges_dir, csv_path = OUT / "edges", OUT / "edge_scores.csv"
    else:
        edges_dir, csv_path = OUT / "edges_pre" / pre, OUT / "edge_scores_pre.csv"
    edges_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    combos = [(k, kk, d) for (k, kk) in ce.SMOOTHERS for d in ce.EDGE_DETECTORS]
    for cloth in CLOTHS:
        case = load_case(cloth)
        mask, rgb = case["mask"], case["rgb"]
        base = ce.apply_chain(rgb, [pre], mask) if pre != "none" else rgb
        gray0 = ce.to_gray(ce.fill_outside(base, mask))
        y0, y1, x0, x1 = crop_box(mask)
        tiles = {}
        for kind, k, det in combos:
            name = f"{kind}_{k}__{det}" if kind != "none" else f"none_0__{det}"
            t0 = time.perf_counter()
            g = ce.smooth_gray(gray0, kind, k)
            e = ce.detect_edges(g, det, mask)
            ms = (time.perf_counter() - t0) * 1000
            e_save = np.where(mask, e, 0).astype(np.uint8)
            p = edges_dir / name / f"{cloth}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(p), e_save)
            m = edge_metrics(np.where(case["inner"], e, 0), case)
            rows.append({"pre": pre, "cloth": cloth, "filter": kind, "k": k, "detector": det,
                         "time_ms": round(ms, 2), "edge_px_garment": int((e_save > 0).sum()),
                         **{a: (round(b, 5) if b == b else "") for a, b in m.items()}})
            crop = 255 - e_save[y0:y1, x0:x1]
            s = THUMB / max(crop.shape)
            th = cv2.resize(crop, (max(1, int(crop.shape[1] * s)), max(1, int(crop.shape[0] * s))),
                            interpolation=cv2.INTER_AREA)
            canvas = np.full((THUMB, THUMB), 255, np.uint8)
            canvas[:th.shape[0], :th.shape[1]] = th
            tiles[(kind, k, det)] = canvas
        # gallery
        flt = ce.SMOOTHERS
        lab_w = 110
        head = 16
        G = np.full((head + len(flt) * (THUMB + 1), lab_w + len(ce.EDGE_DETECTORS) * (THUMB + 1), 3), 255, np.uint8)
        for j, det in enumerate(ce.EDGE_DETECTORS):
            cv2.putText(G, det, (lab_w + j * (THUMB + 1) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        for i, (kind, k) in enumerate(flt):
            cv2.putText(G, f"{kind} {k}" if kind != "none" else "none", (3, head + i * (THUMB + 1) + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            for j, det in enumerate(ce.EDGE_DETECTORS):
                t = cv2.cvtColor(tiles[(kind, k, det)], cv2.COLOR_GRAY2BGR)
                cv2.rectangle(t, (0, 0), (THUMB - 1, THUMB - 1), (200, 200, 200), 1)
                G[head + i * (THUMB + 1): head + i * (THUMB + 1) + THUMB,
                  lab_w + j * (THUMB + 1): lab_w + j * (THUMB + 1) + THUMB] = t
        cv2.imwrite(str(edges_dir / f"gallery_{cloth}.jpg"), G, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(cloth, "done", flush=True)
    new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(rows)
    print("wrote", csv_path, len(rows), "rows")


if __name__ == "__main__":
    main()
