"""P03: threshold sensitivity of a few filter + detector choices (step factor 0.2 / 0.33 / 0.5 x median grey).
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p03_sensitivity.py  -> out/p03_filters/edge_sensitivity.csv
"""
import csv
import numpy as np
from p03_common import CLOTHS, OUT, ce, edge_metrics, load_case

COMBOS = [("gaussian", 5, "canny"), ("none", 0, "canny"), ("bilateral", 9, "canny"), ("bilateral", 9, "laplacian"),
          ("gaussian", 3, "laplacian"), ("bilateral", 9, "dog"), ("bilateral", 9, "scharr"), ("bilateral", 9, "canny_pyr_and")]
rows = []
for cloth in CLOTHS:
    case = load_case(cloth)
    gray0 = ce.to_gray(ce.fill_outside(case["rgb"], case["mask"]))
    for kind, k, det in COMBOS:
        g = ce.smooth_gray(gray0, kind, k)
        for sg in (0.2, 0.33, 0.5):
            e = ce.detect_edges(g, det, case["mask"], sigma=sg)
            m = edge_metrics(np.where(case["inner"], e, 0), case)
            rows.append(dict(cloth=cloth, filter=kind, k=k, detector=det, step_factor=sg, **{a: round(b, 5) for a, b in m.items()}))
with open(OUT / "edge_sensitivity.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
import pandas as pd
d = pd.DataFrame(rows)
des = d[d.cloth != "c_002"].groupby(["filter", "k", "detector", "step_factor"])[["recall", "precision", "f1"]].mean()
des["fer_5photos"] = d.groupby(["filter", "k", "detector", "step_factor"])["fer_pct"].mean()
des["fer_c002"] = d[d.cloth == "c_002"].set_index(["filter", "k", "detector", "step_factor"])["fer_pct"]
print(des.round(3).to_string())
