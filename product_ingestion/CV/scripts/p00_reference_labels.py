"""P00: approximate reference labels for the 5 Mirra photos.

Hand-made by looking at each photo with a 10 % grid (reference/<cloth>/grid.jpg).
Boxes are [x0, y0, x1, y1] in percent of image width/height. All labels are
APPROXIMATE (one annotator, by eye).

The reference colour palette is computed from the reference garment mask:
  - fabric colours: garment pixels outside all design boxes (c_003 is split into its
    two colour blocks at the block boundary);
  - print colours: pixels inside design boxes that differ from the fabric by ΔE2000 > 15.
Each colour is the median CIELAB of its pixels; its share is its pixel fraction of the garment.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p00_reference_labels.py
Out:  out/p00_baseline/reference/labels.json and reference/<cloth>/design_regions_overlay.jpg
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, lab2rgb, rgb2lab

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "out" / "p00_baseline" / "reference"

LABELS = {
    "c_001": {"view": "front", "presentation": "on_person", "garment": "t-shirt", "sleeve": "elbow",
              "fit": "oversized", "neckline": "crew",
              "designs": [{"name": "BOSTON", "type": "text", "box": [19, 18, 74, 35]},
                          {"name": "Leotude", "type": "text", "box": [41, 30.5, 53, 34.5]}]},
    "c_002": {"view": "back", "presentation": "flat", "garment": "t-shirt", "sleeve": "short",
              "fit": "regular", "neckline": "crew", "designs": []},
    "c_003": {"view": "front", "presentation": "on_person", "garment": "t-shirt", "sleeve": "short",
              "fit": "slim", "neckline": "crew", "colour_block_split_y": 47.5,
              "designs": [{"name": "whatever", "type": "text", "box": [19, 16, 73, 26]},
                          {"name": "stripe band", "type": "stripes", "box": [14, 27, 75, 47.5]},
                          {"name": "white block", "type": "colour_block", "box": [3, 0, 96, 47.5]},
                          {"name": "teal block", "type": "colour_block", "box": [15, 47.5, 80, 100]}]},
    "c_004": {"view": "front", "presentation": "flat", "garment": "t-shirt", "sleeve": "short",
              "fit": "regular", "neckline": "crew",
              "designs": [{"name": "square graphic", "type": "graphic", "box": [37, 28, 75, 58]},
                          # corrected 2026-11-20 14:49: the first box [28, 57, 72, 66] sat ~20 px below the
                          # text (checked by eye after P15b flagged it); see plans/01 "Corrections".
                          {"name": "Different yet SAME", "type": "text", "box": [30, 53.5, 70, 60]},
                          {"name": "RESPECT", "type": "text", "box": [30, 27, 40, 30.5]},
                          {"name": "neck logo", "type": "logo", "box": [46, 13, 54, 17]}]},
    "c_005": {"view": "front", "presentation": "on_person", "garment": "t-shirt", "sleeve": "short",
              "fit": "regular", "neckline": "crew",
              "designs": [{"name": "CALIFORNIA", "type": "text", "box": [28, 45, 74, 62]},
                          {"name": "small text", "type": "text", "box": [38, 61, 64, 68]}]},
}


def box_px(box, w, h):
    x0, y0, x1, y1 = box
    return int(round(x0 / 100 * w)), int(round(y0 / 100 * h)), int(round(x1 / 100 * w)), int(round(y1 / 100 * h))


def lab_to_hex(lab) -> str:
    rgb = np.clip(lab2rgb(np.array(lab, float)[None, None, :])[0, 0] * 255, 0, 255).round().astype(int)
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def main() -> None:
    meta = json.loads((REF / "reference_masks_meta.json").read_text(encoding="utf-8"))
    out = {"note": "APPROXIMATE hand-made labels (one annotator, by eye). Boxes in percent [x0,y0,x1,y1].",
           "cloths": {}}
    for cloth, lab_info in LABELS.items():
        rgb = cv2.cvtColor(cv2.imread(meta[cloth]["image"]), cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        garment = cv2.imread(str(REF / cloth / "garment_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
        lab = rgb2lab(rgb)
        design_box = np.zeros((h, w), bool)
        for d in lab_info["designs"]:
            if d["type"] == "colour_block":
                continue
            x0, y0, x1, y1 = box_px(d["box"], w, h)
            design_box[y0:y1, x0:x1] = True
        fabric = garment & ~design_box
        palette = []
        if "colour_block_split_y" in lab_info:
            split = int(lab_info["colour_block_split_y"] / 100 * h)
            rows = np.arange(h)[:, None]
            parts = {"fabric (upper block)": fabric & (rows < split), "fabric (lower block)": fabric & (rows >= split)}
        else:
            parts = {"fabric": fabric}
        total = garment.sum()
        fabric_labs = []
        for name, m in parts.items():
            if m.sum() == 0:
                continue
            med = np.median(lab[m], axis=0)
            fabric_labs.append(med)
            palette.append({"role": name, "lab": [round(float(v), 2) for v in med], "hex": lab_to_hex(med),
                            "share": round(float(m.sum() / total), 4)})
        # print colours: pixels in design boxes that differ from every fabric colour
        inside = garment & design_box
        if inside.any():
            de = np.min(np.stack([deltaE_ciede2000(lab, np.broadcast_to(f, lab.shape)) for f in fabric_labs]), axis=0)
            prt = inside & (de > 15)
            if prt.sum() > 0.002 * total:
                med = np.median(lab[prt], axis=0)
                palette.append({"role": "print", "lab": [round(float(v), 2) for v in med], "hex": lab_to_hex(med),
                                "share": round(float(prt.sum() / total), 4)})
            # the rest of the design boxes is fabric showing through; add it to the closest fabric colour share
        s = sum(p["share"] for p in palette)
        for p in palette:
            p["share"] = round(p["share"] / s, 4)
        entry = dict(lab_info)
        entry["image"] = meta[cloth]["image"]
        entry["size_wh"] = [w, h]
        entry["garment_mask"] = str(REF / cloth / "garment_mask.png")
        entry["palette"] = palette
        entry["main_fabric_hex"] = max((p for p in palette if p["role"].startswith("fabric")), key=lambda p: p["share"])["hex"]
        out["cloths"][cloth] = entry
        ov = rgb.copy()
        for d in lab_info["designs"]:
            x0, y0, x1, y1 = box_px(d["box"], w, h)
            col = {"text": (255, 0, 0), "graphic": (0, 0, 255), "logo": (255, 0, 255),
                   "stripes": (255, 160, 0), "colour_block": (0, 200, 0)}[d["type"]]
            cv2.rectangle(ov, (x0, y0), (x1 - 1, y1 - 1), col, max(1, w // 300))
            cv2.putText(ov, d["type"], (x0 + 2, y0 + max(10, h // 40)), cv2.FONT_HERSHEY_SIMPLEX, max(0.3, w / 1800), col, 1)
        cv2.imwrite(str(REF / cloth / "design_regions_overlay.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))
    (REF / "labels.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for c, e in out["cloths"].items():
        print(c, e["view"], e["presentation"], [(p["role"], p["hex"], p["share"]) for p in e["palette"]])


if __name__ == "__main__":
    main()
