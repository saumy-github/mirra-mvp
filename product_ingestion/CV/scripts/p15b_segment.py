"""P15b step 1: re-segment the 5 Mirra photos with the pipeline default (v1) and v1_all, save the masks.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15b_segment.py

Writes out/p15b_design/masks/<maskset>/<cloth>/mask.png (0/255, size of the photo); maskset = v1 | v1_all.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import cv2

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "product_ingestion"))
from gpu_lock import gpu_lock  # noqa: E402
import step_02_0_segmentation as seg  # noqa: E402
import torch  # noqa: E402

OUT = CV / "out/p15b_design/masks"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


def main():
    labels = json.loads((CV / "out/p00_baseline/reference/labels.json").read_text(encoding="utf-8"))["cloths"]
    info = {}
    for ms, method in (("v1", None), ("v1_all", "v1_all")):
        with gpu_lock("p15b"):
            for c in CLOTHS:
                p = labels[c]["image"]
                t = time.perf_counter()
                res, ok = seg.run_segmentation(p, method=method)
                dt = time.perf_counter() - t
                d = OUT / ms / c
                d.mkdir(parents=True, exist_ok=True)
                h, w = cv2.imread(p).shape[:2]
                m = res.mask
                if m.shape[:2] != (h, w):
                    print("size mismatch", c, m.shape, (h, w))
                cv2.imwrite(str(d / "mask.png"), m)
                info[f"{ms}/{c}"] = {"method": res.method, "valid": res.is_valid, "quality": res.quality_score, "s": round(dt, 1)}
                print(ms, c, res.method, res.is_valid, round(dt, 1), flush=True)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    (OUT / "info.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
