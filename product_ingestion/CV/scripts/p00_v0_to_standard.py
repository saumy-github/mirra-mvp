"""P00: convert the existing v0 pipeline outputs (product_ingestion/output/<cloth>/s_001/001)
into the standard prediction format of scripts/evaluate.py.

- mask.png: alpha channel of image_info/base_garment.png (alpha > 10, as the v0 colour and design steps use)
- palette.json / base_colour.json: from image_info/colors.json
- design_regions.json: the v0 design crop (graphic_diffuse.png) located in the photo by exact template
  matching, with the v0 design type; [] when v0 found no design
- view.json: v0 never classified the view (CLIP failed to load: "clip_unavailable_fallback_first_image"),
  so view is "unknown"

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p00_v0_to_standard.py
Out:  out/p00_baseline/v0_standard/<cloth>/
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = HERE.parents[2]
OUT = ROOT / "out" / "p00_baseline" / "v0_standard"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


def main() -> None:
    for c in CLOTHS:
        run = REPO / "product_ingestion" / "output" / c / "s_001" / "001" / "image_info"
        d = OUT / c
        d.mkdir(parents=True, exist_ok=True)
        rgba = cv2.imread(str(run / "base_garment.png"), cv2.IMREAD_UNCHANGED)
        alpha = rgba[..., 3]
        cv2.imwrite(str(d / "mask.png"), ((alpha > 10) * 255).astype(np.uint8))
        colors = json.loads((run / "colors.json").read_text(encoding="utf-8"))
        pal = [{"hex": p["hex"], "share": p["percentage"] / 100.0, "role": "cluster"} for p in colors["palette"]]
        (d / "palette.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
        (d / "base_colour.json").write_text(json.dumps({"hex": colors["base_colour_hex"]}), encoding="utf-8")
        meta = json.loads((run / "extraction_metadata.json").read_text(encoding="utf-8"))
        design = meta.get("design", {})
        regions = []
        if design.get("has_design"):
            crop = cv2.imread(str(run / "graphic_diffuse.png"), cv2.IMREAD_UNCHANGED)
            if crop is not None and crop.shape[0] > 1 and crop.shape[1] > 1:
                res = cv2.matchTemplate(rgba[..., :3], crop[..., :3], cv2.TM_SQDIFF)
                _, _, loc, _ = cv2.minMaxLoc(res)
                x, y = loc
                regions.append({"box": [x, y, x + crop.shape[1], y + crop.shape[0]],
                                "type": design.get("design_type") or "logo"})
        (d / "design_regions.json").write_text(json.dumps(regions, indent=1), encoding="utf-8")
        (d / "view.json").write_text(json.dumps({"view": "unknown", "presentation": None,
                                                 "note": meta["view_selection"]["selection_reason"]}), encoding="utf-8")
        print(c, "regions", regions)


if __name__ == "__main__":
    main()
