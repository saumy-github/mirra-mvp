"""P15a: replay the shipped decision function cv_segment.auto_skirt_decision on the cached SegFormer labels of every image
(dev + held-out + Mirra) and score v1_auto with the same IoUs / bootstrap as p15a_rules.py. Output: out/p15a_seg_autoselect/final_v1_auto*.csv

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_final_table.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p15a_common import *  # noqa
import cv_segment as cs
import pandas as pd
import p15a_rules as pr

dfs, dec = [], []
for split, f in (("dev", "features.csv"), ("held", "features_heldout.csv")):
    df = pd.read_csv(P15 / f)
    use = []
    for s, i in zip(df.set, df.id):
        lab = load(split, s, str(i).zfill(5) if s.startswith("viton") else str(i), "segformer")["labels"]
        use.append(cs.auto_skirt_decision(lab)[0])
    df["use_all"] = use
    dfs.append(df)
    rule = pr.base_rules(df)["head<0.01"]
    print(split, "decision function == feature rule on", int((df.use_all.values == rule).sum()), "of", len(df))
    res, bs = pr.run(df, {"v1": np.zeros(len(df), bool), "v1_all": np.ones(len(df), bool), "v1_auto": df.use_all.values}, f"final_{split}")
    print(pr.fmt(res, bs))
al = pd.concat(dfs, ignore_index=True)
res, bs = pr.run(al, {"v1": np.zeros(len(al), bool), "v1_all": np.ones(len(al), bool), "v1_auto": al.use_all.values}, "final_pooled")
print(pr.fmt(res, bs))
al[al.use_all][["split", "set", "id", "iou_v1", "iou_v1a", "skirt_frac", "face_frac", "hair_frac"]].to_csv(P15 / "final_v1_auto_fired.csv", index=False)
print(al[al.use_all][["split", "set", "id", "iou_v1", "iou_v1a"]].to_string())
