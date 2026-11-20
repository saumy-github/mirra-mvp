"""P15b step 2: run the two heavy proposers (EasyOCR text boxes, Grounding DINO) once per photo and mask set
and pickle them, so the region logic can be re-run on CPU without loading models.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15b_cache.py [--sets oracle,v1,v1_all]

Writes out/p15b_design/cache/<maskset>/<cloth>.pkl   ({"ocr": [...], "gdino": [...]} in working-resolution pixels).
"""
from __future__ import annotations
import argparse, gc, pickle, time
from p15b_common import *  # noqa
from gpu_lock import gpu_lock
import cv_design_regions as cvd

ap = argparse.ArgumentParser()
ap.add_argument("--sets", default="oracle,v1,v1_all")
args = ap.parse_args()
for ms in args.sets.split(","):
    data = load_inputs(ms)
    with gpu_lock("p15b"):
        for c in CLOTHS:
            p = cache_path(ms, c)
            if p.exists():
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            d = data[c]
            P = cvd.prepare(d["rgb"], d["mask"])
            t = time.time()
            cache = {"ocr": cvd.propose_ocr(P), "gdino": cvd.propose_gdino(P)}
            p.write_bytes(pickle.dumps(cache))
            print(ms, c, "ocr", len(cache["ocr"]), "gdino", len(cache["gdino"]), f"{time.time()-t:.1f}s", flush=True)
            gc.collect()
