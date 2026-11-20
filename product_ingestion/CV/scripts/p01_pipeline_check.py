"""P01: run the REAL pipeline entry point run_segmentation() on the 5 Mirra photos with method v0 and v1.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_pipeline_check.py

Writes out/p01_segmentation/methods/pipeline_v0|pipeline_v1/<cloth>/{mask.png, overlay.jpg, quality.json, outline.json}
and out/p01_segmentation/pipeline_check.json (time per image, quality metrics). Score them afterwards with evaluate.py.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p01_common import *  # noqa: F401,F403
from gpu_lock import gpu_lock
import cv_segment as cs
import step_02_0_segmentation as seg
import torch


def main():
    summary = {}
    for method in ("v0", "v1", "v1_all"):
        with gpu_lock("p01"):
            for c in CLOTHS:
                p = sorted((INPUT / c).glob("*"))[0]
                t = time.perf_counter()
                res, ok = seg.run_segmentation(p, method=method)
                dt = time.perf_counter() - t
                d = METHODS_DIR / f"pipeline_{method}" / c
                d.mkdir(parents=True, exist_ok=True)
                bgr = read_bgr(p)
                if res.mask is not None:
                    cv2.imwrite(str(d / "mask.png"), res.mask)
                    cv2.imwrite(str(d / "overlay.jpg"), cs.overlay(bgr, res.mask))
                (d / "quality.json").write_text(json.dumps(
                    {"method": res.method, "valid": res.is_valid, "quality_score": res.quality_score,
                     "quality_metrics": res.quality_metrics, "details": res.details, "time_s_incl_model_load": dt},
                    indent=2, default=str), encoding="utf-8")
                if res.outline_polygon:
                    (d / "outline.json").write_text(json.dumps(res.outline_polygon), encoding="utf-8")
                summary[f"{method}/{c}"] = {"method": res.method, "valid": res.is_valid, "quality": res.quality_metrics,
                                           "time_s_incl_model_load": round(dt, 2)}
            torch.cuda.empty_cache()
    (OUT / "pipeline_check.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
