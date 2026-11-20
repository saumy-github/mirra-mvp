"""P04 figures: palette swatches per method and photo, region maps, score tables (PNG/JPEG, small).

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_make_figures.py
Reads  out/p04_colour/methods/<mask>__<method>/<cloth>/{palette.json,region_map.png}, results/mirra_scores.csv,
       out/p04_colour/fpi_eval/<tag>/summary.csv
Writes out/p04_colour/figures/*.png
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import cv2, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "p04_colour"
TAG = "methods"
SUFFIX = ""
FIG = OUT / "figures"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
REF = json.loads((ROOT / "out" / "p00_baseline" / "reference" / "labels.json").read_text(encoding="utf-8"))["cloths"]


def bar(ax, pal):
    x = 0.0
    for e in pal:
        s = float(e["share"])
        ax.add_patch(plt.Rectangle((x, 0), s, 1, color=e["hex"], lw=0))
        x += s
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linewidth(0.4)


def swatches(mask, methods, name):
    fig, axes = plt.subplots(len(methods) + 1, len(CLOTHS), figsize=(2.0 * len(CLOTHS), 0.42 * (len(methods) + 1) + 0.5))
    for j, c in enumerate(CLOTHS):
        bar(axes[0, j], REF[c]["palette"]); axes[0, j].set_title(c, fontsize=8)
    axes[0, 0].set_ylabel("reference", rotation=0, ha="right", va="center", fontsize=7)
    for i, m in enumerate(methods, 1):
        for j, c in enumerate(CLOTHS):
            p = OUT / TAG / f"{mask}__{m}" / c / "palette.json"
            if p.exists():
                bar(axes[i, j], json.loads(p.read_text()))
            else:
                axes[i, j].axis("off")
        axes[i, 0].set_ylabel(m, rotation=0, ha="right", va="center", fontsize=7)
    fig.suptitle(f"Palettes ({mask} masks): bar width = share", fontsize=9)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=130); plt.close(fig)


def region_grid(mask, methods, name):
    cols = ["photo"] + methods
    fig, axes = plt.subplots(len(CLOTHS), len(cols), figsize=(2.1 * len(cols), 2.5 * len(CLOTHS)))
    for i, c in enumerate(CLOTHS):
        im = cv2.cvtColor(cv2.imread(REF[c]["image"]), cv2.COLOR_BGR2RGB)
        axes[i, 0].imshow(im); axes[i, 0].set_title(c if i else f"photo\n{c}", fontsize=7)
        for j, m in enumerate(methods, 1):
            p = OUT / TAG / f"{mask}__{m}" / c / "region_map.png"
            if p.exists():
                axes[i, j].imshow(cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB))
            if i == 0:
                axes[i, j].set_title(m, fontsize=7)
    for a in axes.ravel():
        a.axis("off")
    fig.suptitle(f"Colour region maps ({mask} masks); grey = not garment", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / name, dpi=110); plt.close(fig)


def table_png(df, title, name, fmt="{:.2f}"):
    fig, ax = plt.subplots(figsize=(1.2 * (df.shape[1] + 1.5), 0.3 * (len(df) + 2)))
    ax.axis("off")
    cells = [[fmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in r] for r in df.values]
    t = ax.table(cellText=cells, rowLabels=list(df.index), colLabels=list(df.columns), loc="center", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(7); t.scale(1, 1.2)
    ax.set_title(title, fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / name, dpi=130); plt.close(fig)


def mirra_table(mask):
    pre = f"p04_{mask}__"
    d = pd.read_csv(ROOT / "results" / "mirra_scores.csv")
    d = d[d.label.str.startswith(pre) & d.label.str.endswith(SUFFIX) & (d.cloth == "mean")]
    if not SUFFIX:
        d = d[~d.label.str.contains("_v2")]
    keep = ["colour.palette_de", "colour.ref_share_matched", "colour.base_colour_de", "colour.all_fabric_colours_found_de", "colour.n_colours"]
    t = d[d.metric.isin(keep)].pivot_table(index="label", columns="metric", values="value", aggfunc="last")[keep]
    t.index = [i.replace(pre, "") for i in t.index]
    t.columns = ["palette_de", "ref_share_matched", "base_colour_de", "all_fabric_found_de", "n_colours"]
    return t


def main():
    global TAG, SUFFIX, FIG
    ap = argparse.ArgumentParser(); ap.add_argument("--fpi_tag", default="run_01"); ap.add_argument("--tag", default="methods")
    ap.add_argument("--suffix", default=""); ap.add_argument("--methods", nargs="*", default=None); ap.add_argument("--region_methods", nargs="*", default=None); ap.add_argument("--fig_dir", default="figures"); a = ap.parse_args()
    TAG, SUFFIX, FIG = a.tag, a.suffix, OUT / a.fig_dir
    allm = ["v0", "k_noskin", "k_hsv", "k_ycrcb", "k_auto", "k_parser", "kmedoids_auto", "gmm_auto", "meanshift_auto",
            "kmeans_nomerge", "gmm_nomerge", "gmm_shade20", "gmm_greyworld", "gmm_clahe", "gmm_parser"]
    allm = a.methods or allm
    for mask in ("oracle", "v0"):
        FIG.mkdir(parents=True, exist_ok=True)
        swatches(mask, allm, f"swatches_{mask}.png")
        region_grid(mask, (a.region_methods or ["k_auto", "kmedoids_auto", "gmm_auto", "meanshift_auto", "gmm_shade20"]), f"region_maps_{mask}.png")
        t = mirra_table(mask)
        t.to_csv(FIG / f"mirra_table_{mask}.csv")
        table_png(t, f"Mirra photos, {mask} masks (mean over 5 photos)", f"table_mirra_{mask}.png")
    s = OUT / "fpi_eval" / a.fpi_tag / "summary.csv"
    if s.exists():
        df = pd.read_csv(s, index_col=0)[["n", "failed", "top1", "top1_family", "any", "any_family", "n_colours", "time_s"]]
        table_png(df, "Fashion Product subset: colour-name accuracy", "table_fpi.png", "{:.3f}")


if __name__ == "__main__":
    main()
