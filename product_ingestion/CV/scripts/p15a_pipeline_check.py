"""P15a: run the real entry point run_segmentation() on the 5 Mirra photos for the given methods (GPU under gpu_lock) and score with evaluate.py.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_pipeline_check.py [v1_auto v1 v1_all]   (default: v1_auto only; method None = the module default)
Masks -> out/p15a_seg_autoselect/pipeline_<method>/<cloth>/mask.png ; scores -> results/mirra_scores.csv (label p15a_<method>) and pipeline_check.json.
"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p15a_common import *  # noqa
from gpu_lock import gpu_lock
import evaluate as ev
import step_02_0_segmentation as seg

methods = sys.argv[1:] or ["default"]
res = {}
with gpu_lock("p15a"):
    for m in methods:
        res[m] = {}
        for c in CLOTHS:
            p = sorted((INPUT / c).glob("*"))[0]
            r, ok = seg.run_segmentation(p, None if m == "default" else m)
            d = P15 / f"pipeline_{m}" / c
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / "mask.png"), r.mask)
            gt = ev.load_mask(ROOT / "out" / "p00_baseline" / "reference" / c / "garment_mask.png", r.mask.shape)
            res[m][c] = {"iou": ev.mask_metrics(r.mask > 0, gt)["iou"], "method": r.method, "auto": (r.details or {}).get("auto"),
                         "area_percent": r.area_percent, "quality_score": r.quality_score}
            print(m, c, res[m][c], flush=True)
(P15 / "pipeline_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for m in methods:
    subprocess.run([sys.executable, str(HERE / "evaluate.py"), "--pred", str(P15 / f"pipeline_{m}"), "--label", f"p15a_{m}", "--plan", "p15a"], capture_output=True)
