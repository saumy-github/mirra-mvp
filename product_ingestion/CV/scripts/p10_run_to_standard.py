"""P10: convert real pipeline run outputs into the standard prediction format of evaluate.py,
so the end-to-end pipeline (all stages together, as a user would run it) is scored exactly
like the v0 baseline (p00_v0_to_standard.py).

For each cloth it takes the LATEST run folder under <runs_root>/<cloth>/s_001/<NNN>/:
- mask.png            alpha of image_info/base_garment.png (> 10, as the colour and design steps use it)
- palette.json        colors.json palette (hex, percentage -> share, role)
- base_colour.json    colors.json base_colour_hex
- design_regions.json extraction_metadata.json design.regions (box + type); [] when no design;
                      for v0-style output without regions, the single graphic box is located as in p00
- view.json           view_assignment.json view of the main photo + presentation

Usage:
  .venv/Scripts/python.exe product_ingestion/CV/scripts/p10_run_to_standard.py --runs <runs_root> --out <pred_root>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


def latest_run(root: Path, cloth: str) -> Path | None:
    d = root / cloth / "s_001"
    if not d.exists():
        return None
    runs = sorted(p for p in d.iterdir() if p.is_dir() and p.name.isdigit())
    return runs[-1] if runs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root, out = Path(a.runs), Path(a.out)
    for c in CLOTHS:
        run = latest_run(root, c)
        if run is None:
            print(c, "no run"); continue
        info = run / "image_info"
        d = out / c
        d.mkdir(parents=True, exist_ok=True)
        rgba = cv2.imread(str(info / "base_garment.png"), cv2.IMREAD_UNCHANGED)
        cv2.imwrite(str(d / "mask.png"), ((rgba[..., 3] > 10) * 255).astype(np.uint8))
        colors = json.loads((info / "colors.json").read_text(encoding="utf-8"))
        pal = [{"hex": p["hex"], "share": p["percentage"] / 100.0, "role": p.get("role", "cluster")}
               for p in colors["palette"]]
        s = sum(p["share"] for p in pal) or 1.0
        for p in pal:
            p["share"] /= s
        (d / "palette.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
        (d / "base_colour.json").write_text(json.dumps({"hex": colors["base_colour_hex"]}), encoding="utf-8")
        meta = json.loads((info / "extraction_metadata.json").read_text(encoding="utf-8"))
        design = meta.get("design") or {}
        regions = []
        for r in design.get("regions") or []:
            box = r.get("box") or r.get("bbox")
            if box:
                regions.append({"box": [float(v) for v in box[:4]], "type": r.get("type", "logo")})
        (d / "design_regions.json").write_text(json.dumps(regions, indent=1), encoding="utf-8")
        view = {"view": "unknown", "presentation": None}
        va_path = info / "view_assignment.json"
        if va_path.exists():
            va = json.loads(va_path.read_text(encoding="utf-8"))
            front = va.get("front")
            ph = next((p for p in va.get("photos", []) if p.get("path") == front), None)
            if ph:
                pres = ph.get("presentation")
                pres = {"person": "on_person"}.get(pres, pres)   # reference labels use "on_person"
                view = {"view": ph.get("view"), "presentation": pres}
        (d / "view.json").write_text(json.dumps(view), encoding="utf-8")
        print(c, run.name, "regions", len(regions), "view", view)


if __name__ == "__main__":
    main()
