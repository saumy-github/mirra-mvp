"""P00: build the approximate reference garment masks for the 5 Mirra photos.

The reference for each photo is the SAM 2 candidate that a person judged to be the
shirt only (chosen by eye from reference_candidates/<cloth>/candidates_sheet.jpg),
cleaned up: largest connected component, holes filled with a padded flood fill
(so a mask touching the image border is not flooded), small specks removed.

These references are APPROXIMATE (one person, by eye). Exact references for
large-scale numbers come from the public datasets.

Also writes grid overlays (10 % grid) and a "differs from the main fabric colour"
map, used to mark the design regions by hand.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p00_make_reference_masks.py
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "out" / "p00_baseline"
CAND = BASE / "reference_candidates"
REF = BASE / "reference"

# Chosen by eye (see candidates_sheet.jpg of each cloth). Note: for c_004 the
# highest-IoU SAM 2 candidate (cand0, 0.756) is only the print; the whole shirt is cand1 (0.191).
CHOSEN = {"c_001": "sam2_cand2", "c_002": "sam2_cand2", "c_003": "sam2_cand2",
          "c_004": "sam2_cand1", "c_005": "sam2_cand2"}


def fill_holes_padded(mask: np.ndarray) -> np.ndarray:
    m = (mask > 0).astype(np.uint8) * 255
    padded = cv2.copyMakeBorder(m, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inv = cv2.bitwise_not(padded)
    ff = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
    cv2.floodFill(inv, ff, (0, 0), 0)
    return cv2.bitwise_or(padded, inv)[1:-1, 1:-1]


def largest_component(mask: np.ndarray) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == k).astype(np.uint8) * 255


def grid_overlay(rgb: np.ndarray) -> np.ndarray:
    out = rgb.copy()
    h, w = out.shape[:2]
    for i in range(1, 10):
        x, y = int(w * i / 10), int(h * i / 10)
        cv2.line(out, (x, 0), (x, h - 1), (0, 255, 255), 1)
        cv2.line(out, (0, y), (w - 1, y), (0, 255, 255), 1)
        fs = max(0.3, min(w, h) / 900)
        cv2.putText(out, f"{i * 10}", (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 0, 255), 1)
        cv2.putText(out, f"{i * 10}", (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 0, 255), 1)
    return out


def main() -> None:
    meta = json.loads((CAND / "candidates_meta.json").read_text(encoding="utf-8"))
    summary = {}
    for cloth, cand in CHOSEN.items():
        img_path = Path(meta[cloth]["image"])
        bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        raw = cv2.imread(str(CAND / cloth / f"{cand}.png"), cv2.IMREAD_GRAYSCALE)
        m = largest_component(raw)
        m = fill_holes_padded(m)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        m = largest_component(m)
        d = REF / cloth
        d.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / "garment_mask.png"), m)
        ov = rgb.copy()
        cnts, _ = cv2.findContours((m > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cnts, -1, (0, 255, 0), max(1, rgb.shape[1] // 400))
        cv2.imwrite(str(d / "garment_mask_overlay.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(d / "grid.jpg"), cv2.cvtColor(grid_overlay(rgb), cv2.COLOR_RGB2BGR))
        # pixels that differ from the main fabric colour (helper for marking designs by hand)
        lab = rgb2lab(rgb)
        fab = np.median(lab[m > 0], axis=0)
        de = deltaE_ciede2000(lab, np.broadcast_to(fab, lab.shape))
        diff = ((de > 15) & (m > 0)).astype(np.uint8) * 255
        cv2.imwrite(str(d / "differs_from_main_fabric.png"), diff)
        summary[cloth] = {"image": str(img_path), "chosen_candidate": cand,
                          "mask_area_percent": round(float((m > 0).mean() * 100), 2),
                          "main_fabric_lab": [round(float(v), 1) for v in fab]}
    (REF / "reference_masks_meta.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
