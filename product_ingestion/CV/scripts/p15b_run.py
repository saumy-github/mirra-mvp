"""P15b step 3: run v0 / v3_combo / v3_fix / v4_nofix / v4_relabel on the 5 photos for each mask set, save predictions.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15b_run.py [--sets oracle,v1,v1_all] [--methods ...] [--out try_01]

EasyOCR / Grounding DINO boxes come from the pickles made by p15b_cache.py (same results, no model reload);
the SigLIP 2 relabelling runs live inside gpu_lock("p15b") and is freed at the end.
Writes out/p15b_design/<out>/<maskset>/<method>/<cloth>/{design_regions.json, mask.png} and overlays/<maskset>/<method>/<cloth>.jpg
"""
from __future__ import annotations
import argparse, json, time
from p15b_common import *  # noqa
from gpu_lock import gpu_lock
import cv_design_regions as cvd
import step_04_0_design_extraction as s4

ap = argparse.ArgumentParser()
ap.add_argument("--sets", default="oracle,v1,v1_all")
ap.add_argument("--methods", default="v0,v3_combo,v3_fix,v4_nofix,v4_relabel")
ap.add_argument("--out", default="try_01")
ap.add_argument("--cpu", action="store_true", help="run the SigLIP 2 relabelling on the CPU (no gpu_lock)")
args = ap.parse_args()
root = OUT / args.out
methods = args.methods.split(",")
need_gpu = any(m.startswith("v4") for m in methods) and not args.cpu
if args.cpu:
    cvd.RELABEL_DEVICE = "cpu"
timing = {}


def run_all():
    for ms in args.sets.split(","):
        data = load_inputs(ms)
        for m in methods:
            t0 = time.time()
            for c in CLOTHS:
                d = data[c]
                if m == "v0":
                    rgba = np.dstack([d["rgb"], d["mask"].astype(np.uint8) * 255])
                    regs = s4.extract_design(rgba, method="v0").regions
                else:
                    regs = cvd.detect_regions(d["rgb"], d["mask"], method=m, cache=load_cache(ms, c))
                regs = [{"box": [round(float(v), 1) for v in r["box"]], "type": r["type"],
                         "confidence": round(float(r.get("confidence", 0)), 3), "source": r.get("source", "")} for r in regs]
                base = root / ms / m / c
                base.mkdir(parents=True, exist_ok=True)
                (base / "design_regions.json").write_text(json.dumps(regs, indent=1), encoding="utf-8")
                cv2.imwrite(str(base / "mask.png"), d["mask"].astype(np.uint8) * 255)
                od = root / "overlays" / ms / m
                od.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(od / f"{c}.jpg"), draw_overlay(d["rgb"], d["mask"], regs, f"{m} ({ms})"), [cv2.IMWRITE_JPEG_QUALITY, 80])
            timing[f"{ms}/{m}"] = round(time.time() - t0, 1)
            print(ms, m, f"{timing[f'{ms}/{m}']}s", flush=True)


if need_gpu:
    with gpu_lock("p15b"):
        run_all()
        cvd.release_labeller()
else:
    run_all()
(root / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")
