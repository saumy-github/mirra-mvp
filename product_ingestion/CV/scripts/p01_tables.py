"""P01: Mirra table (from results/mirra_scores.csv, latest rows per label) -> out/p01_segmentation/mirra_scores.csv and markdown."""
import pandas as pd, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
df = pd.read_csv(R / "results" / "mirra_scores.csv")
df = df[(df.label.str.startswith("p01_")) | (df.label == "v0_current_pipeline")]
df = df.sort_values("timestamp").drop_duplicates(["label", "cloth", "metric"], keep="last")
keys = ["mask.iou", "mask.boundary_f@1.0%", "mask.hd95_pct_diag", "mask.leakage", "mask.miss", "summary.outline_score"]
mean = df[(df.cloth == "mean") & df.metric.isin(keys)].pivot(index="label", columns="metric", values="value")
iou = df[(df.cloth != "mean") & (df.metric == "mask.iou")].pivot(index="label", columns="cloth", values="value")
out = mean.join(iou).sort_values("summary.outline_score", ascending=False)
out.to_csv(R / "out" / "p01_segmentation" / "mirra_scores.csv")
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
print(out.round(3).to_string())
