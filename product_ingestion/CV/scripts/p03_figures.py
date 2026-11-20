"""P03 comparison figures for the paper -> out/p03_filters/figures/*.png

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p03_figures.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from p03_common import OUT, ce, load_case

FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def crop_pct(arr, box):
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = box
    return arr[int(y0 / 100 * h): int(y1 / 100 * h), int(x0 / 100 * w): int(x1 / 100 * w)]


def edges_for(case, kind, k, det):
    g = ce.smooth_gray(ce.to_gray(ce.fill_outside(case["rgb"], case["mask"])), kind, k)
    e = ce.detect_edges(g, det, case["mask"])
    return g, np.where(case["inner"], e, 0)


def fig_smoothing():
    """Same crops of c_002 (folds, seams) and c_004 (print) under each smoothing filter + auto-Canny."""
    c2, c4 = load_case("c_002"), load_case("c_004")
    box2, box4 = (0, 0, 55, 55), (25, 10, 80, 68)
    rows = [("none", 0), ("mean", 5), ("median", 5), ("gaussian", 5), ("bilateral", 5), ("bilateral", 9)]
    fig, ax = plt.subplots(len(rows), 4, figsize=(9.5, 2.35 * len(rows)))
    for i, (kind, k) in enumerate(rows):
        for j, (case, box) in enumerate(((c2, box2), (c4, box4))):
            g, e = edges_for(case, kind, k, "canny")
            ax[i, 2 * j].imshow(crop_pct(g, box), cmap="gray", vmin=0, vmax=255)
            ax[i, 2 * j + 1].imshow(255 - crop_pct(e, box), cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            if i == 0:
                ax[i, 2 * j].set_title(f"{case['cloth']} smoothed", fontsize=9)
                ax[i, 2 * j + 1].set_title(f"{case['cloth']} auto-Canny", fontsize=9)
        ax[i, 0].set_ylabel("none" if kind == "none" else f"{kind} {k}", fontsize=9)
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Smoothing before auto-Canny: folds and seams (c_002, left) vs print (c_004, right)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_smoothing_filters.png", dpi=130)
    plt.close(fig)


def fig_detectors():
    """Canny vs LoG vs DoG (and gradient detectors) after Gaussian 5, on c_003, c_004 and c_002."""
    cases = [(load_case("c_003"), (10, 12, 80, 50)), (load_case("c_004"), (25, 10, 80, 68)), (load_case("c_002"), (0, 0, 55, 55))]
    dets = ["sobel", "prewitt", "scharr", "laplacian", "log", "dog", "canny", "canny_pyr_and", "canny_pyr_or"]
    fig, ax = plt.subplots(len(cases), len(dets) + 1, figsize=(2.0 * (len(dets) + 1), 2.3 * len(cases)))
    for i, (case, box) in enumerate(cases):
        ax[i, 0].imshow(crop_pct(case["rgb"], box))
        ax[i, 0].set_ylabel(case["cloth"], fontsize=9)
        for j, d in enumerate(dets):
            _, e = edges_for(case, "gaussian", 5, d)
            ax[i, j + 1].imshow(255 - crop_pct(e, box), cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            if i == 0:
                ax[i, j + 1].set_title(d, fontsize=8)
    ax[0, 0].set_title("photo", fontsize=8)
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Edge detectors after Gaussian 5x5 (same step-size threshold rule for all)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_edge_detectors.png", dpi=130)
    plt.close(fig)


def fig_pareto():
    d = pd.read_csv(OUT / "summary_edges.csv")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    cols = dict(zip(sorted(d.detector.unique()), plt.cm.tab10(np.arange(10))))
    for det, g in d.groupby("detector"):
        ax.scatter(g.fer_pct_5photos, g.f1, s=22, color=cols[det], label=det, alpha=0.85)
    for name, mk in (("gaussian 5 + canny", "*"), ("bilateral 9 + laplacian", "D")):
        r = d[d.combo == name].iloc[0]
        ax.scatter(r.fer_pct_5photos, r.f1, s=140, marker=mk, facecolor="none", edgecolor="k", linewidths=1.5)
        ax.annotate(name, (r.fer_pct_5photos, r.f1), textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xscale("symlog", linthresh=0.5)
    ax.set_xlabel("fold false-edge rate, % of plain-fabric pixels (mean of 5 photos, symlog)")
    ax.set_ylabel("design-edge F1 (mean of c_001, c_003, c_004, c_005)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_f1_vs_false_edges.png", dpi=130)
    plt.close(fig)


def fig_enhance():
    """Shading removal on c_002 (plain) and c_003 (colour blocks), clean and under uneven lighting."""
    from p03_enhance_study import degrade
    names = ["input", "shading_divide", "shading_divide_regions", "shading_homomorphic", "clahe_L_2", "hist_eq_L"]
    fig, ax = plt.subplots(4, len(names), figsize=(2.3 * len(names), 2.4 * 4))
    r = 0
    for cloth in ("c_002", "c_003"):
        case = load_case(cloth)
        for deg in ("clean", "shade"):
            src = degrade(case["rgb"], deg, case["mask"])
            for j, n in enumerate(names):
                im = src if n == "input" else ce.ENHANCERS[n](src, case["mask"])
                ax[r, j].imshow(np.where(case["mask"][..., None], im, 255))
                if r == 0:
                    ax[r, j].set_title(n, fontsize=8)
            ax[r, 0].set_ylabel(f"{cloth} {deg}", fontsize=9)
            r += 1
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Shading removal and contrast methods; 'shade' = synthetic uneven lighting", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_enhancement_shading.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    fig_smoothing()
    fig_detectors()
    fig_pareto()
    fig_enhance()
    print("figures ok")
