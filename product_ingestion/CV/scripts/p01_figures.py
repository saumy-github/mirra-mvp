"""P01 figures and outline.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_figures.py --best <method> [--sheet-methods m1 m2 ...]

  * contact_sheet_all.jpg      rows = every method, columns = the 5 Mirra photos (overlay of the mask)
  * contact_sheet_selected.jpg the selected methods only
  * outline/<method>/<cloth>/outline.png, outline_overlay.jpg, polygon.json   clean outline of the best mask
    (Gaussian-smoothed contour, Douglas-Peucker simplified polygon) - replaces "colour the background and edge-detect"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p01_common import *  # noqa: F401,F403
import cv_segment as cs


def thumb(img, h=170):
    s = h / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), h), interpolation=cv2.INTER_AREA)


def sheet(methods, path, cell=(150, 170)):
    rows = []
    lab_w = 230
    for m in methods:
        tiles = []
        for c in CLOTHS:
            p = METHODS_DIR / m / c / "overlay.jpg"
            im = cv2.imread(str(p)) if p.exists() else np.full((cell[1], cell[0], 3), 40, np.uint8)
            t = thumb(im, cell[1])
            canvas = np.full((cell[1], cell[0], 3), 255, np.uint8)
            t = t[:, :cell[0]]
            canvas[:, :t.shape[1]] = t
            tiles.append(canvas)
        lab = np.full((cell[1], lab_w, 3), 255, np.uint8)
        cv2.putText(lab, m, (4, cell[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 0, 0), 1, cv2.LINE_AA)
        rows.append(np.hstack([lab] + tiles))
    head = np.full((24, rows[0].shape[1], 3), 255, np.uint8)
    for k, c in enumerate(CLOTHS):
        cv2.putText(head, c, (lab_w + k * cell[0] + 40, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), np.vstack([head] + rows), [cv2.IMWRITE_JPEG_QUALITY, 88])


def outlines(best):
    for c in CLOTHS:
        bgr = read_bgr(sorted((INPUT / c).glob("*"))[0])
        m = cv2.imread(str(METHODS_DIR / best / c / "mask.png"), 0)
        poly, dense = cs.mask_to_outline(m)
        d = OUT / "outline" / best / c
        d.mkdir(parents=True, exist_ok=True)
        blank = np.full(bgr.shape, 255, np.uint8)
        cv2.imwrite(str(d / "outline.png"), cs.draw_outline(blank, poly, (0, 0, 0), 2, dots=False))
        cv2.imwrite(str(d / "outline_overlay.jpg"), cs.draw_outline(bgr, poly), [cv2.IMWRITE_JPEG_QUALITY, 90])
        (d / "polygon.json").write_text(json.dumps({
            "method": best, "image_wh": [bgr.shape[1], bgr.shape[0]],
            "n_points_dense": int(len(dense)), "n_points_polygon": int(len(poly)),
            "polygon": poly.tolist()}), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--best", required=True)
    ap.add_argument("--sheet-methods", nargs="*", default=None)
    a = ap.parse_args()
    allm = sorted(p.name for p in METHODS_DIR.iterdir() if p.is_dir())
    sheet(allm, OUT / "contact_sheet_all.jpg")
    if a.sheet_methods:
        sheet([m for m in a.sheet_methods if m in allm], OUT / "contact_sheet_selected.jpg")
    outlines(a.best)
    print("done", len(allm), "methods")
