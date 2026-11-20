"""P06: summary tables + figures from the CSVs written by p06_ratio_stats.py, p06_corners.py, p06_sleeve_eval.py.
Writes stats/corner_detector_summary.csv, stats/viton_ratio_summary.csv, stats/viton_clo_compare.csv, stats/ratio_hist.png."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from p06_common import *
S = OUT / "stats"
# ---- corner detectors
parts = []
for f, tag in (("mirra_corner_metrics.csv", "mirra5"), ("viton_photo_corner_metrics.csv", "viton24_photo"), ("viton_mask_corner_metrics.csv", "viton500_mask")):
    d = pd.read_csv(OUT / "corners" / f); d["set"] = tag; parts.append(d)
d = pd.concat(parts)
g = d.groupby(["set", "domain", "detector"])[["n_all", "n_kept", "recall_at_3pct", "precision_top40", "precision_all_kept", "on_outline_frac"]].mean().round(3).reset_index()
g.to_csv(S / "corner_detector_summary.csv", index=False)
print(g.to_string())
# ---- ratios
v = pd.read_csv(S / "viton_shape.csv")
v = v[v.ok]
v["clean"] = (v.armpit_method == "convexity_defect") & ~v["flags"].fillna("").str.contains("asymmetric|unequal|degenerate")
CLO_H, CLO_W = 0.930697, 0.783952
cols = ["hem_to_chest", "hem_to_chest_hough", "sleeve_to_body_length", "wrist_to_bicep", "wrist_to_bicep_band", "chest_to_length", "length_to_chest", "shoulder_to_chest", "neck_depth_to_length"]
rows = []
def stat(x, label, sub, col):
    x = x.dropna()
    if len(x) < 3: return
    rows.append(dict(subset=sub, sleeve_class=label, ratio=col, n=len(x), mean=x.mean(), std=x.std(), p5=x.quantile(.05), p25=x.quantile(.25), median=x.median(), p75=x.quantile(.75), p95=x.quantile(.95)))
for sub, dd in (("all", v), ("clean", v[v.clean])):
    for col in cols:
        stat(dd[col], "ALL", sub, col)
        for cl, gg in dd.groupby("sleeve_class"): stat(gg[col], cl, sub, col)
R = pd.DataFrame(rows).round(4); R.to_csv(S / "viton_ratio_summary.csv", index=False)
print(R[(R.subset == "clean") & (R.sleeve_class.isin(["ALL", "short"]))].to_string())
# CLO comparison
cmp = []
for sub, dd in (("all", v), ("clean", v[v.clean])):
    for name, col, fixed in (("HEM_TO_CHEST_RATIO", "hem_to_chest", CLO_H), ("WRIST_TO_BICEP_RATIO", "wrist_to_bicep", CLO_W), ("WRIST_TO_BICEP_RATIO(band)", "wrist_to_bicep_band", CLO_W)):
        for cl in ["ALL", "short", "elbow", "three_quarter", "long"]:
            x = (dd[col] if cl == "ALL" else dd[dd.sleeve_class == cl][col]).dropna()
            if len(x) < 5: continue
            cmp.append(dict(subset=sub, constant=name, sleeve_class=cl, clo_fixed=fixed, n=len(x), median=x.median(), mean=x.mean(), std=x.std(),
                            iqr=x.quantile(.75) - x.quantile(.25), clo_percentile=(x < fixed).mean() * 100,
                            frac_within_10pct_of_clo=(abs(x / fixed - 1) <= 0.10).mean(), cv=x.std() / x.mean()))
C = pd.DataFrame(cmp).round(4); C.to_csv(S / "viton_clo_compare.csv", index=False); print(C.to_string())
# Hough hem agreement
h = v[["hem_to_chest", "hem_to_chest_hough"]].dropna()
print("hem contour vs hough: n", len(h), "spearman", spearmanr(h.iloc[:, 0], h.iloc[:, 1])[0], "median abs diff", (h.iloc[:, 0] - h.iloc[:, 1]).abs().median())
# ---- histograms
fig, ax = plt.subplots(2, 3, figsize=(13, 7))
def hist(a, x, title, lo, hi, line=None, by=None):
    x = x.dropna().clip(lo, hi)
    a.hist(x, bins=40, range=(lo, hi), color="#4c72b0")
    if line: a.axvline(line, color="#c44e52", ls="--", label=f"CLO fixed {line:.3f}"); a.legend(fontsize=8)
    a.axvline(x.median(), color="k", lw=1, label="median"); a.set_title(f"{title}\nmedian {x.median():.3f}, n={len(x)}", fontsize=9)
vc = v[v.clean]
hist(ax[0, 0], vc.hem_to_chest, "hem / chest (clean subset)", 0.5, 1.8, CLO_H)
hist(ax[0, 1], vc[vc.sleeve_class.isin(["short", "elbow"])].wrist_to_bicep, "cuff / bicep (short+elbow sleeves)", 0, 1.5, CLO_W)
hist(ax[0, 2], v.sleeve_to_body_length, "sleeve length / garment length (all)", 0, 1.2)
for t, a in (("sleeveless", 0.10), ("short", 0.40), ("elbow", 0.56), ("three_quarter", 0.70)): ax[0, 2].axvline(a, color="g", lw=0.8)
hist(ax[1, 0], vc.chest_to_length, "chest width / garment length", 0.2, 1.0)
hist(ax[1, 1], vc.shoulder_to_chest, "shoulder width / chest width", 0.5, 1.8)
hist(ax[1, 2], v.neck_depth_to_length, "neck depth / garment length", 0, 0.3)
fig.suptitle("VITON-HD test, 500 cloth masks: shape ratios (cv_shape); dashed = fixed value in step_05_0", fontsize=10)
fig.tight_layout(); fig.savefig(S / "ratio_hist.png", dpi=110)
print(v.sleeve_class.value_counts().to_dict(), "clean", int(v.clean.sum()), "of", len(v))
# sleeve ratio vs fashionpedia order
f = pd.read_csv(S / "sleeve_eval_fashionpedia.csv")
order = {"sleeveless": 0, "short": 1, "elbow": 2, "three_quarter": 3, "long": 4}
print("fashionpedia spearman(ratio, true order)", spearmanr(f.ratio, f.true.map(order))[0], "n", len(f))

# ---- chance baseline: random points on the outline, same counts as the detectors (mask domain, every 5th VITON mask)
rng = np.random.RandomState(0)
base = []
for i in range(0, 500, 5):
    m = viton_mask(i); r = cv_shape.analyze_shape(m)
    if not r["ok"]: continue
    wm, c, sc, bb = cv_shape.clean_outline(m)
    L = np.array(list(r["landmarks"].values())) * sc
    tol = 0.03 * 480
    for n in (12, 47, 92, 126, 209):
        for _ in range(10):
            p = c[rng.randint(0, len(c), n)]
            D = np.sqrt(((p[:, None] - L[None]) ** 2).sum(2))
            base.append(dict(n=n, recall=(D.min(0) <= tol).mean(), precision=(D.min(1) <= tol).mean()))
B = pd.DataFrame(base).groupby("n").mean().round(3); B.to_csv(S / "chance_baseline_outline.csv"); print("CHANCE (random outline points)"); print(B)
