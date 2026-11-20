"""P05: AUC / threshold sweep for plain-vs-design on the Fashionpedia results.csv (run p05_fashionpedia.py first).
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_fp_analysis.py [try_01]"""
import csv, json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
CV = Path(__file__).resolve().parents[1]
d = CV / "out/p05_design" / (sys.argv[1] if len(sys.argv) > 1 else "try_01") / "fashionpedia"
R = list(csv.DictReader(open(d / "results.csv")))
y = np.array([r["cls"] == "design" for r in R])
out = {"n_plain": int((~y).sum()), "n_design": int(y.sum()), "auc": {}, "dev_cov_sweep": []}
for k in ["dev_cov", "per_ratio", "old_fft_ratio", "periodic_new", "new_has", "v0_has"]:
    x = np.array([float(r[k]) for r in R])
    out["auc"][k] = round(float(roc_auc_score(y, x)), 3)
x = np.array([float(r["dev_cov"]) for r in R])
for t in [0.005, 0.02, 0.06, 0.1, 0.15, 0.2, 0.3]:
    p = x > t
    out["dev_cov_sweep"].append({"thr": t, "fp_on_plain": round(float(p[~y].mean()), 3), "tpr_on_design": round(float(p[y].mean()), 3)})
(d / "auc.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
