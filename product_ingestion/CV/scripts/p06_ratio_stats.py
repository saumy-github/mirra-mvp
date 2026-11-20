"""P06: run cv_shape.analyze_shape on the 500 saved VITON-HD cloth masks; write per-garment CSV (stats/viton_shape.csv)
and sleeve-class summary + CLO-fixed-ratio comparison (stats/viton_ratio_summary.csv, stats/viton_clo_compare.csv)
and histograms (stats/ratio_hist.png). Run from repo root."""
import csv, json, time, numpy as np
from p06_common import *
def main():
    rows = []
    t0 = time.time()
    for i in range(500):
        r = cv_shape.analyze_shape(viton_mask(i), f"v{i:03d}")
        row = {"id": f"v{i:03d}", "ok": r["ok"], "flags": "|".join(r.get("flags", [])) if r["ok"] else r.get("error", "")}
        if r["ok"]:
            row.update({"armpit_method": r["methods"]["armpit"], "shoulder_method_L": r["methods"]["shoulder_left"],
                        "sleeve_class": r["sleeve"]["class"], "neck_shape": r["neckline"]["shape"],
                        "neck_depth_px": r["neckline"]["depth_px"], "dropped_shoulder": r["fit"]["dropped_shoulder"],
                        "shoulder_drop_frac": r["fit"]["shoulder_drop_frac"], "shoulder_slope_deg": r["fit"]["shoulder_slope_deg"]})
            row.update({k: v for k, v in r["ratios"].items()})
            row.update({"len_" + k: v for k, v in r["lengths_px"].items()})
        rows.append(row)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(OUT / "stats" / "viton_shape.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("done", time.time() - t0, "s; ok", sum(r["ok"] for r in rows))
main()
