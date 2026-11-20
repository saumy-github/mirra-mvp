"""Demo: read a garment from one or several photos, without MongoDB or CLO.

Runs the new photo-reading stages of the pipeline on a folder (or a single image):
  1. view assignment across the photos (front / back / side / other, flat or person)   [multi_view]
  2. garment outline (segmentation) and outline polygon                                [step_02_0]
  3. colour palette with fabric/print roles and a colour region map                     [step_03_0]
  4. design regions with types (two-level outlining)                                    [step_04_0]
  5. shape: landmarks, sleeve class, ratios                                             [cv_shape]
  6. trained attributes: pattern, sleeve length, neckline (optional)                    [cv_attributes]
and writes one JSON plus an overlay image per photo used.

Usage (from the repo root):
  .venv/Scripts/python.exe product_ingestion/CV/scripts/demo_read_garment.py <folder or image> [--out DIR] [--no-attributes]
Default output: product_ingestion/CV/out/demo/<name>/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
PI = HERE.parents[1]                     # product_ingestion/
sys.path.insert(0, str(PI))

from step_01_0_view_selection import list_cloth_images  # noqa: E402
from step_02_0_segmentation import run_segmentation  # noqa: E402
from step_03_0_colour_extraction import extract_colours  # noqa: E402
from step_04_0_design_extraction import extract_design  # noqa: E402

COLOURS = {"text": (255, 60, 60), "graphic": (60, 120, 255), "logo": (230, 60, 230), "stripes": (255, 160, 0),
           "colour_block": (0, 190, 0), "pattern": (0, 200, 200)}


def to_json(o):
    if isinstance(o, dict):
        return {str(k): to_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_json(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    return o


def overlay(rgb, mask, regions, polygon=None):
    out = rgb.copy()
    if mask is not None:
        dim = (out * 0.45).astype(np.uint8)
        out = np.where(mask[..., None] > 0, out, dim)
    th = max(2, rgb.shape[1] // 300)
    if polygon:
        cv2.polylines(out, [np.array(polygon, np.int32).reshape(-1, 1, 2)], True, (255, 255, 0), th)
    for r in regions or []:
        box = r.get("box") or r.get("bbox")
        if not box:
            continue
        x0, y0, x1, y1 = [int(v) for v in box[:4]]
        col = COLOURS.get(r.get("type"), (255, 255, 255))
        cv2.rectangle(out, (x0, y0), (x1, y1), col, th)
        cv2.putText(out, r.get("type", ""), (x0 + 3, max(12, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX,
                    max(0.4, rgb.shape[1] / 1600), col, max(1, th // 2))
    return out


def read_one(path: Path, args, out: Path, role: str) -> dict:
    seg, ok = run_segmentation(path)
    res = {"photo": str(path), "role": role, "segmentation": {"valid": seg.is_valid, "method": seg.method,
                                                               "area_percent": round(seg.area_percent, 2),
                                                               "quality": seg.quality_metrics}}
    if not (seg.is_valid and seg.rgba_image is not None):
        return res
    rgba = seg.rgba_image
    colour, _ = extract_colours(rgba)
    res["colour"] = {"base_colour_hex": colour.base_colour_hex,
                     "palette": [c.to_dict() for c in colour.palette]}
    if hasattr(colour, "extra_json"):
        res["colour"].update(colour.extra_json())
    design = extract_design(rgba)
    regions = getattr(design, "regions", None) or []
    res["design"] = {"has_design": design.has_design, "main_type": getattr(design, "main_type", design.design_type),
                     "regions": [{k: v for k, v in (r.items() if isinstance(r, dict) else vars(r).items())
                                  if k not in ("mask", "image", "crop")} for r in regions]}
    try:
        from cv_shape import garment_landmarks
        shape = garment_landmarks(seg.mask)
        res["shape"] = {k: shape.get(k) for k in ("ok", "sleeve_class", "ratios", "fit", "landmarks", "flags")}
    except Exception as e:  # noqa: BLE001
        res["shape"] = {"error": str(e)}
    if not args.no_attributes:
        try:
            from cv_attributes import predict_attributes, release_models
            cut = out / f"{role}_cutout.png"
            cv2.imwrite(str(cut), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
            attrs = predict_attributes(str(cut))
            res["attributes"] = {g: {"label": a.get("label"), "confidence": a.get("confidence")}
                                 for g, a in attrs.items() if isinstance(a, dict)}
            release_models()
        except Exception as e:  # noqa: BLE001
            res["attributes"] = {"error": str(e)}
    rgb = rgba[..., :3]
    ov = overlay(rgb, seg.mask, res["design"]["regions"], getattr(seg, "outline_polygon", None))
    cv2.imwrite(str(out / f"{role}_overlay.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))
    lm = res.get("shape", {}).get("landmarks") or {}
    if lm:
        lm_img = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
        for name, (x, y) in lm.items():
            cv2.circle(lm_img, (int(x), int(y)), max(3, rgb.shape[1] // 150), (0, 255, 255), -1)
        cv2.imwrite(str(out / f"{role}_landmarks.jpg"), lm_img)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="folder of photos of ONE garment, or a single image")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-attributes", action="store_true")
    args = ap.parse_args()
    src = Path(args.input)
    out = Path(args.out) if args.out else HERE.parent / "out" / "demo" / src.stem
    out.mkdir(parents=True, exist_ok=True)
    photos = list_cloth_images(src) if src.is_dir() else [src]
    report = {"input": str(src), "photos": [str(p) for p in photos]}
    front, back = photos[0], None
    try:
        from multi_view import assign_views
        va = assign_views([str(p) for p in photos])
        d = va.to_dict()
        report["views"] = d
        front = Path(va.front) if va.front else front
        back = Path(va.back) if va.back else None
    except Exception as e:  # noqa: BLE001
        report["views"] = {"error": str(e)}
    report["front"] = read_one(front, args, out, "front")
    if back is not None:
        report["back"] = read_one(back, args, out, "back")
    (out / "garment_reading.json").write_text(json.dumps(to_json(report), indent=2), encoding="utf-8")
    f = report["front"]
    print(f"front photo : {front}")
    print(f"back photo  : {back}")
    print(f"outline     : {f['segmentation']}")
    print(f"colours     : {[(c['hex'], round(c['percentage'], 1), c.get('role')) for c in f.get('colour', {}).get('palette', [])]}")
    print(f"designs     : {[(r.get('type'), [int(v) for v in (r.get('box') or [])[:4]]) for r in f.get('design', {}).get('regions', [])]}")
    print(f"shape       : sleeve={f.get('shape', {}).get('sleeve_class')}")
    print(f"attributes  : {f.get('attributes')}")
    print(f"written to  : {out}")


if __name__ == "__main__":
    main()
