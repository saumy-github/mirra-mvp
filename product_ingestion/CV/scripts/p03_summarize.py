"""P03: summarise the score CSVs into tables (printed as markdown and saved as CSV).

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p03_summarize.py > out/p03_filters/summary_tables.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from p03_common import OUT

DESIGNED = ["c_001", "c_003", "c_004", "c_005"]


def md(df, floatfmt=3):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(f"{v:.{floatfmt}f}" if isinstance(v, (float, np.floating)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def edge_table(d):
    d = d.copy()
    d["combo"] = np.where(d["filter"] == "none", "none", d["filter"] + " " + d["k"].astype(str)) + " + " + d["detector"]
    d["prec_px"] = d["design_edge_density_pct"] / (d["design_edge_density_pct"] + d["fer_pct"])
    d["f1_px"] = 2 * d["prec_px"] * d["recall"] / (d["prec_px"] + d["recall"])
    des = d[d.cloth.isin(DESIGNED)]
    g = des.groupby("combo")[["recall", "precision", "f1", "f1_px", "design_edge_density_pct"]].mean()
    g["fer_pct_4photos"] = des.groupby("combo")["fer_pct"].mean()
    g["fer_pct_c002"] = d[d.cloth == "c_002"].set_index("combo")["fer_pct"]
    g["fer_pct_5photos"] = d.groupby("combo")["fer_pct"].mean()
    g["time_ms"] = d.groupby("combo")["time_ms"].mean()
    g["filter"] = d.drop_duplicates("combo").set_index("combo")["filter"]
    g["detector"] = d.drop_duplicates("combo").set_index("combo")["detector"]
    return g.reset_index()


def main():
    d = pd.read_csv(OUT / "edge_scores.csv")
    g = edge_table(d)
    g.to_csv(OUT / "summary_edges.csv", index=False)
    cols = ["combo", "recall", "precision", "f1", "f1_px", "fer_pct_5photos", "fer_pct_c002", "time_ms"]
    print("## Edge study: top 15 by F1 (mean over c_001, c_003, c_004, c_005)\n")
    print(md(g.sort_values("f1", ascending=False).head(15)[cols]))
    safe = g[(g.fer_pct_c002 <= 0.15) & (g.fer_pct_5photos <= 1.0)]
    print(f"\n## Edge study: top 15 by F1 among fold-safe combinations (c_002 false-edge rate <= 0.15 %, mean over 5 photos <= 1.0 %); {len(safe)} of {len(g)} combinations qualify\n")
    print(md(safe.sort_values("f1", ascending=False).head(15)[cols]))
    print("\n## Edge study: top 10 by F1 using pixel-density precision (f1_px)\n")
    print(md(g.sort_values("f1_px", ascending=False).head(10)[cols]))
    print("\n## Best smoothing filter for each detector (by F1)\n")
    print(md(g.loc[g.groupby("detector")["f1"].idxmax()].sort_values("f1", ascending=False)[cols]))
    print("\n## Best detector for each smoothing filter (by F1)\n")
    print(md(g.loc[g.groupby("filter")["f1"].idxmax()].sort_values("f1", ascending=False)[cols]))
    print("\n## Baseline (current pipeline: Gaussian 5 + auto-Canny) and unsmoothed Canny\n")
    print(md(g[g.combo.isin(["gaussian 5 + canny", "none + canny"])][cols]))
    print("\n## Per-photo scores, baseline vs best fold-safe combination\n")
    best = safe.sort_values("f1", ascending=False).iloc[0]["combo"]
    d["combo"] = np.where(d["filter"] == "none", "none", d["filter"] + " " + d["k"].astype(str)) + " + " + d["detector"]
    pp = d[d.combo.isin(["gaussian 5 + canny", best])][["combo", "cloth", "recall", "precision", "f1", "fer_pct", "time_ms"]]
    print(md(pp.sort_values(["combo", "cloth"])))

    # preprocessing before edges
    try:
        p = pd.read_csv(OUT / "edge_scores_pre.csv")
        allp = pd.concat([d.assign(pre="none"), p])
        print("\n## Edge study with a pre-processing step (first column = pre-processing)\n")
        rows = []
        for pre, dd in allp.groupby("pre"):
            gg = edge_table(dd)
            for cname in ["gaussian 5 + canny", best]:
                r = gg[gg.combo == cname].iloc[0]
                rows.append(dict(pre=pre, combo=cname, f1=r.f1, recall=r.recall, precision=r.precision,
                                 fer_5photos=r.fer_pct_5photos, fer_c002=r.fer_pct_c002))
            sfe = gg[(gg.fer_pct_c002 <= 0.15) & (gg.fer_pct_5photos <= 1.0)].sort_values("f1", ascending=False)
            if len(sfe):
                r = sfe.iloc[0]
                rows.append(dict(pre=pre, combo="best fold-safe: " + r.combo, f1=r.f1, recall=r.recall, precision=r.precision,
                                 fer_5photos=r.fer_pct_5photos, fer_c002=r.fer_pct_c002))
        print(md(pd.DataFrame(rows)))
    except FileNotFoundError:
        pass

    # enhancement
    e = pd.read_csv(OUT / "enhance_scores.csv")
    base = e[e.method == "none"].set_index(["cloth", "degradation"])
    e = e.join(base[["std_L", "design_std_L"]].rename(columns={"std_L": "b_std", "design_std_L": "b_dstd"}), on=["cloth", "degradation"])
    e["std_ratio"] = e["std_L"] / e["b_std"]
    e["design_ratio"] = pd.to_numeric(e["design_std_L"], errors="coerce") / pd.to_numeric(e["b_dstd"], errors="coerce")
    e.to_csv(OUT / "summary_enhance_rows.csv", index=False)
    agg = e.groupby(["kind", "method", "degradation"]).agg(de2000=("de2000", "mean"), std_L=("std_L", "mean"),
                                                         std_ratio=("std_ratio", "mean"), design_ratio=("design_ratio", "mean"),
                                                         time_ms=("time_ms", "mean")).reset_index()
    agg.to_csv(OUT / "summary_enhance.csv", index=False)
    for deg in ["clean", "cast", "dark", "noise", "shade"]:
        t = agg[(agg.kind == "single") & (agg.degradation == deg)].sort_values("de2000")
        print(f"\n## Enhancement, single methods, degradation = {deg} (mean over 5 photos)\n")
        print(md(t[["method", "de2000", "std_L", "std_ratio", "design_ratio", "time_ms"]]))
    # chains overall
    wide = agg[agg.kind == "chain"].pivot(index="method", columns="degradation", values="de2000")
    wide["mean_de2000_all"] = wide.mean(axis=1)
    sr = agg[agg.kind == "chain"].groupby("method").agg(std_ratio_mean=("std_ratio", "mean"), design_ratio_mean=("design_ratio", "mean"),
                                                     time_ms=("time_ms", "mean"))
    ch = wide.join(sr).reset_index().sort_values("mean_de2000_all")
    ch.to_csv(OUT / "summary_chains.csv", index=False)
    print("\n## Chains: top 12 by mean DeltaE2000 over the 5 conditions (clean, cast, dark, noise, shade)\n")
    print(md(ch.head(12)))
    print("\n## Chains: top 12 by flatness (lowest mean std ratio)\n")
    print(md(ch.sort_values("std_ratio_mean").head(12)))
    sing = agg[agg.kind == "single"].pivot(index="method", columns="degradation", values="de2000")
    sing["mean_de2000_all"] = sing.mean(axis=1)
    sr = agg[agg.kind == "single"].groupby("method").agg(std_ratio_mean=("std_ratio", "mean"), design_ratio_mean=("design_ratio", "mean"))
    print("\n## Single methods: DeltaE2000 per degradation, then mean; flatness and design retention (all conditions)\n")
    print(md(sing.join(sr).reset_index().sort_values("mean_de2000_all")))

    try:
        v = pd.read_csv(OUT / "viton_flatness.csv")
        vv = v.groupby("method").agg(images=("img", "nunique"), std_ratio_mean=("ratio", "mean"), std_ratio_median=("ratio", "median"),
                                     colour_shift_dE=("de_shift", "mean"), time_ms=("time_ms", "mean")).reset_index().sort_values("std_ratio_mean")
        vv.to_csv(OUT / "summary_viton.csv", index=False)
        print("\n## VITON-HD fabric flatness (ratio of std of L on same-hue fabric pixels; < 1 means flatter)\n")
        print(md(vv))
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
