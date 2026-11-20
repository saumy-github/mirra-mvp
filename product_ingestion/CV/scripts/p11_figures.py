"""P11: paper figures.

1. images/fig_before_after_scores.png: v0 pipeline vs new pipeline, per area (from results/mirra_before_after.csv).
2. images/fig_outline_public_iou.png: public macro IoU of the main segmentation methods (from results/public/p01_*).
3. Copies of the key qualitative figures from each plan into images/ (names prefixed by plan).

Palette: categorical slots 1-2 of the dataviz reference palette (#2a78d6, #eb6834), validated
(CVD ΔE 24.7, normal-vision ΔE 33.6, contrast >= 3:1 on #fcfcfb).

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p11_figures.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RES, OUT, IMG = ROOT / "results", ROOT / "out", ROOT / "images"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2 = "#2a78d6", "#eb6834"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.facecolor": SURFACE, "figure.facecolor": SURFACE})


S3 = "#1baf7a"   # categorical slot 3 (aqua); validated with slots 1-2 (CVD ΔE 9.2); every bar is value-labelled


def before_after() -> None:
    t = pd.read_csv(RES / "mirra_before_after.csv")
    t = t[(t.area == "pipeline (end to end)") & t["summary.pipeline_score"].notna()]
    series = [("before", "v0 pipeline", S2), ("after (first pass)", "first new pipeline", S3),
              ("after (final)", "final pipeline", S1)]
    series = [(t[t.role == r].iloc[0], name, col) for r, name, col in series if (t.role == r).any()]
    areas = [("Outline", "summary.outline_score"), ("Colour", "summary.colour_score"),
             ("Design", "summary.design_score"), ("View", "summary.view_score"),
             ("Pipeline", "summary.pipeline_score")]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    n = len(series)
    w = 0.78 / n
    for i, (_, key) in enumerate(areas):
        for j, (row, _, col) in enumerate(series):
            xpos = i + (j - (n - 1) / 2) * (w + 0.015)
            v = float(row[key])
            ax.bar(xpos, v, width=w, color=col, edgecolor=SURFACE, linewidth=1.0, zorder=3)
            ax.text(xpos, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7 if n > 2 else 8, color=INK)
    ax.set_xticks(range(len(areas)), [a for a, _ in areas], color=INK)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score (0 to 1, higher is better)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in series],
              labels=[nm for _, nm, _ in series], frameon=False, loc="upper left", ncol=n, fontsize=9)
    ax.set_title("End-to-end scores on the 5 Mirra photos", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(IMG / "fig_before_after_scores.png")
    plt.close(fig)


def outline_public() -> None:
    p = RES / "public" / "p01_segmentation_public_scores.csv"
    df = pd.read_csv(p)
    want = {"v0_current": "v0: SAM 2 centre point (old)", "sam2_box_segtop_pt": "v1: parser box + point -> SAM 2 (first default)",
            "comb_box_seglc_pt_minus_skin": "v1_all: + skirt class, minus skin",
            "sam2_box_gdino": "Grounding DINO box -> SAM 2", "segformer_top": "SegFormer parser alone",
            "comb_majority3_top": "majority vote of 3", "comb_vote3": "vote of SAM 2 + parser + YOLOE",
            "yoloe_multi": "YOLOE (text prompts)", "rmbg_salient": "RMBG salient object",
            "grabcut_rect": "GrabCut (classical)", "meanshift_centre": "mean-shift (classical)",
            "kmeans_centre": "K-means (classical)", "region_growing": "region growing (classical)"}
    sets = ["viton_cloth", "viton_person", "fashionpedia"]
    classical = {"grabcut_rect", "meanshift_centre", "kmeans_centre", "region_growing"}
    fam_col = {"classical": S2, "zero-shot": S1, "trained": S3}
    rows = []
    for m, name in want.items():
        sub = df[(df.method == m) & (df.set.isin(sets))]
        if len(sub) == 3:
            rows.append((name, float(sub.iou.mean()), "classical" if m in classical else "zero-shot"))
    # final default v1_auto (P15a; same P01 test sets) and our fine-tuned YOLO (P17; same sets and scoring)
    p15 = OUT / "p15a_seg_autoselect" / "rules_final_dev.csv"
    if p15.exists():
        r = pd.read_csv(p15).set_index("rule")
        if "v1_auto" in r.index:
            rows.append(("v1_auto: final default (head rule)", float(r.loc["v1_auto", "public_macro"]), "zero-shot"))
    p17 = OUT / "p17_yolo_seg" / "public_scores.csv"
    if p17.exists():
        d17 = pd.read_csv(p17)
        for m, name in (("p17_yolo_seg_finetuned:largest", "YOLO26s-seg fine-tuned here (P17)"),
                        ("p17_yolo_seg_finetuned:yolo_box_pt_sam2", "fine-tuned YOLO box + point -> SAM 2")):
            sub = d17[(d17.method == m) & (d17.set.isin(sets))]
            if len(sub) == 3:
                rows.append((name, float(sub.iou.mean()), "trained"))
    if not rows:
        print("no public rows found"); return
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=200)
    ys = range(len(rows))
    ax.barh(list(ys), [v for _, v, _ in rows], color=[fam_col[f] for _, _, f in rows], height=0.6,
            edgecolor=SURFACE, zorder=3)
    for y, (_, v, _) in zip(ys, rows):
        ax.text(v + 0.01, y, f"{v:.3f}", va="center", fontsize=8, color=INK)
    ax.set_yticks(list(ys), [n for n, _, _ in rows], color=INK, fontsize=8.5)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=fam_col[f]) for f in ("classical", "zero-shot", "trained")],
              labels=["classical (syllabus)", "pretrained models, zero-shot", "trained in this project"],
              frameon=False, loc="upper center", bbox_to_anchor=(0.32, -0.2), ncol=3, fontsize=8.5)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Mean IoU over 3 public test sets\n(VITON-HD product, VITON-HD person, Fashionpedia street)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle("Garment outline methods on public data (exact masks)", x=0.02, ha="left", color=INK, fontsize=10.5)
    fig.tight_layout()
    fig.savefig(IMG / "fig_outline_public_iou.png", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


COPIES = {
    "p00_sam2_candidates_c_004.jpg": OUT / "p00_baseline/reference_candidates/c_004/candidates_sheet.jpg",
    "p00_sam2_candidates_c_002.jpg": OUT / "p00_baseline/reference_candidates/c_002/candidates_sheet.jpg",
    "p00_reference_design_regions_c_003.jpg": OUT / "p00_baseline/reference/c_003/design_regions_overlay.jpg",
    "p01_contact_sheet_selected.jpg": OUT / "p01_segmentation/contact_sheet_selected.jpg",
    "p03_fig1_smoothing_filters.png": OUT / "p03_filters/figures/fig1_smoothing_filters.png",
    "p03_fig2_edge_detectors.png": OUT / "p03_filters/figures/fig2_edge_detectors.png",
    "p03_fig3_enhancement_shading.png": OUT / "p03_filters/figures/fig3_enhancement_shading.png",
    "p03_fig4_f1_vs_false_edges.png": OUT / "p03_filters/figures/fig4_f1_vs_false_edges.png",
    "p03_edge_gallery_c_004.png": OUT / "p03_filters/edges/gallery_c_004.png",
    "p04_swatches_oracle.png": OUT / "p04_colour/figures_v2/swatches_oracle.png",
    "p04_region_maps_oracle.png": OUT / "p04_colour/figures_v2/region_maps_oracle.png",
    "p05_contact_sheet_oracle_masks.jpg": OUT / "p05_design/contact_sheet_oracle_masks.jpg",
    "p06_landmarks_mirra.jpg": OUT / "p06_shape/overlays/mirra_all.jpg",
    "p06_corners_c_004.jpg": OUT / "p06_shape/corners/c_004_corners.jpg",
    "p06_ratio_hist.png": OUT / "p06_shape/stats/ratio_hist.png",
    "p07_confusion_sleeve3.png": OUT / "p07_attributes/figs/confusion_sleeve3.png",
    "p07_confusion_pattern.png": OUT / "p07_attributes/figs/confusion_pattern.png",
    "p07_mirra_predictions.png": OUT / "p07_attributes/figs/mirra_predictions.png",
    "p16_confusion_view.png": OUT / "p16_multiview/cm_view_chosen_siglip2_lr.png",
    "p16_examples_testsets.png": OUT / "p16_multiview/examples_testsets.png",
    "p16_mirra_mixed_grid.png": OUT / "p16_multiview/mirra_mixed_grid.png",
    "p19_panel_maps_c_003.jpg": OUT / "p19_panel_maps/fig_c_003.jpg",
    "p19_panel_maps_c_001.jpg": OUT / "p19_panel_maps/fig_c_001.jpg",
}


def main() -> None:
    IMG.mkdir(exist_ok=True)
    before_after()
    outline_public()
    missing = []
    for name, src in COPIES.items():
        if src.exists():
            shutil.copy2(src, IMG / name)
        else:
            missing.append(str(src))
    print("figures written; copied", len(COPIES) - len(missing), "of", len(COPIES))
    for m in missing:
        print("missing:", m)


if __name__ == "__main__":
    main()
