"""P01: aggregate out/p01_segmentation/public_scores_per_image*.csv -> public_scores.csv (+ markdown tables)."""
import sys
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parents[1] / "out" / "p01_segmentation"
files = sorted(OUT.glob("public_scores_per_image*.csv"))
df = pd.concat([pd.read_csv(f) for f in files]).drop_duplicates(["set", "method", "id"], keep="last")
df["empty_or_fail"] = (df["iou"] < 0.1).astype(float)
cols = ["iou", "boundary_f@0.5%", "boundary_f@1.0%", "boundary_f@2.0%", "hd95_pct_diag", "leakage", "miss", "empty_or_fail", "time_s"]
g = df.groupby(["set", "method"])[cols].mean()
g["n"] = df.groupby(["set", "method"]).size()
g = g.reset_index()
ov = df.groupby("method")[cols].mean().reset_index()
ov["set"] = "all_3_sets_equal_image_weight"; ov["n"] = df.groupby("method").size().values
# macro mean over the three sets (each set weighted equally)
mac = g.groupby("method")[cols].mean().reset_index(); mac["set"] = "macro_mean_of_sets"; mac["n"] = g.groupby("method")["n"].sum().values
out = pd.concat([g, mac]).sort_values(["set", "iou"], ascending=[True, False])
out.to_csv(OUT / "public_scores.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
for s in out["set"].unique():
    print("###", s); print(out[out["set"] == s].drop(columns="set").round(3).to_string(index=False))
