"""P11: gather the paper's numbers into results/.

1. results/mirra_summary_by_method.csv: one row per scored method (latest row per label) with
   the four area scores and the key metrics, from results/mirra_scores.csv.
2. results/mirra_before_after.csv: the chosen "before" (v0) and "after" rows per area.
3. results/public/*.csv|json: copies of each plan's public-dataset result files, under clear names.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p11_build_results.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RES = ROOT / "results"
OUT = ROOT / "out"

KEY = ["summary.pipeline_score", "summary.outline_score", "summary.colour_score", "summary.design_score",
       "summary.view_score", "mask.iou", "mask.boundary_f@1.0%", "mask.leakage", "colour.palette_de",
       "colour.base_colour_de", "colour.all_fabric_colours_found_de", "design.f1@0.3", "design.pixel_iou",
       "design.type_accuracy_matched", "design.false_positive_on_plain", "design.colour_block_found",
       "view.correct", "view.presentation_correct"]

# (area, label, role, mask set used) — "before" = v0, "after" = the accepted default(s)
BEFORE_AFTER = [
    ("pipeline (end to end)", "v0_current_pipeline_final_scoring", "before", "v0 pipeline"),
    ("pipeline (end to end)", "p10_final_pipeline", "after (first pass)", "first new pipeline (P10)"),
    ("pipeline (end to end)", "p10_final_pipeline_v2", "after (final)", "final pipeline (P10 after P15a, P15b)"),
    ("outline", "p01_pipeline_v0", "before", "-"),
    ("outline", "p01_pipeline_v1", "after (first default v1)", "-"),
    ("outline", "p01_pipeline_v1_all", "after (variant v1_all)", "-"),
    ("outline", "p15a_v1", "after (v1, live run)", "-"),
    ("outline", "p15a_default", "after (final default v1_auto, live run)", "-"),
    ("colour", "p04_oracle__v0", "before", "reference masks"),
    ("colour", "p04_oracle__v1_default_v2", "after", "reference masks"),
    ("colour", "p04_v0__v0", "before", "v0 masks"),
    ("colour", "p04_v0__v1_default_v2", "after", "v0 masks"),
    ("design", "p05_try_02_v0_oracle", "before", "reference masks"),
    ("design", "p05_try_03_v3_combo_oracle", "after (P05 default v3_combo)", "reference masks"),
    ("design", "p15b_v4_relabel_oracle", "after (final default v4_relabel)", "reference masks"),
    ("design", "p15b_v0_v1", "before", "P01 v1 masks"),
    ("design", "p15b_v3_combo_v1", "after (P05 default v3_combo)", "P01 v1 masks"),
    ("design", "p15b_v4_relabel_v1", "after (final default v4_relabel)", "P01 v1 masks"),
]

PUBLIC = {
    "p01_segmentation_public_scores.csv": OUT / "p01_segmentation" / "public_scores.csv",
    "p01_segmentation_paired_bootstrap_iou.csv": OUT / "p01_segmentation" / "paired_bootstrap_iou.csv",
    "p03_edge_scores_summary.csv": OUT / "p03_filters" / "summary_edges.csv",
    "p03_enhance_scores_summary.csv": OUT / "p03_filters" / "summary_enhance.csv",
    "p03_viton_flatness_summary.csv": OUT / "p03_filters" / "summary_viton.csv",
    "p04_fashion_product_run_02_summary.csv": OUT / "p04_colour" / "fpi_eval" / "run_02" / "summary.csv",
    "p04_fashion_product_run_04_summary.csv": OUT / "p04_colour" / "fpi_eval" / "run_04" / "summary.csv",
    "p05_fashionpedia_summary.json": OUT / "p05_design" / "try_02" / "fashionpedia" / "summary.json",
    "p05_fashionpedia_auc.json": OUT / "p05_design" / "try_02" / "fashionpedia" / "auc.json",
    "p06_viton_ratio_summary.csv": OUT / "p06_shape" / "stats" / "viton_ratio_summary.csv",
    "p06_viton_vs_clo_ratios.csv": OUT / "p06_shape" / "stats" / "viton_clo_compare.csv",
    "p06_corner_detector_summary.csv": OUT / "p06_shape" / "stats" / "corner_detector_summary.csv",
    "p06_sleeve_eval.json": OUT / "p06_shape" / "stats" / "sleeve_eval.json",
    "p07_attributes_valcv_results.csv": OUT / "p07_attributes" / "try_01_valcv" / "results_valcv.csv",
    "p07_attributes_holdout_chosen.csv": OUT / "p07_attributes" / "try_01_valcv" / "holdout_chosen.csv",
    "p07_attributes_per_class_recall.csv": OUT / "p07_attributes" / "try_01_valcv" / "per_class_recall_chosen.csv",
    "p16_view_classifiers_inshop.csv": OUT / "p16_multiview" / "results_view.csv",
    "p16_view_zeroshot_inshop.csv": OUT / "p16_multiview" / "results_view_zeroshot.csv",
    "p16_sets_end_to_end.csv": OUT / "p16_multiview" / "sets_end_to_end.csv",
    "p16_sets_end_to_end_summary.json": OUT / "p16_multiview" / "sets_end_to_end_summary.json",
    "p16_same_garment.csv": OUT / "p16_multiview" / "results_same_garment.csv",
    "p19_panel_maps_metrics.csv": OUT / "p19_panel_maps" / "metrics.csv",
    "p15a_autoselect_rules_dev.csv": OUT / "p15a_seg_autoselect" / "rules_dev.csv",
    "p15a_autoselect_final_heldout.csv": OUT / "p15a_seg_autoselect" / "rules_final_held.csv",
    "p15a_autoselect_final_pooled.csv": OUT / "p15a_seg_autoselect" / "rules_final_pooled.csv",
    "p15a_autoselect_final_pooled_bootstrap.csv": OUT / "p15a_seg_autoselect" / "rules_final_pooled_bootstrap.csv",
    "p15a_autoselect_fired.csv": OUT / "p15a_seg_autoselect" / "final_v1_auto_fired.csv",
    "p17_yolo_seg_public_scores.csv": OUT / "p17_yolo_seg" / "public_scores.csv",
    "p17_yolo_seg_eval_summary.json": OUT / "p17_yolo_seg" / "eval_summary.json",
    "p17_yolo_seg_training_curves.csv": OUT / "p17_yolo_seg" / "runs" / "run2-2" / "results.csv",
}


def main() -> None:
    df = pd.read_csv(RES / "mirra_scores.csv")
    df = df[df.cloth == "mean"].sort_values("timestamp")
    latest = df.groupby(["label", "metric"]).tail(1)
    wide = latest.pivot_table(index="label", columns="metric", values="value", aggfunc="last")
    cols = [c for c in KEY if c in wide.columns]
    wide[cols].round(4).to_csv(RES / "mirra_summary_by_method.csv")
    rows = []
    for area, label, role, masks in BEFORE_AFTER:
        if label not in wide.index:
            rows.append({"area": area, "role": role, "label": label, "masks": masks, "note": "not scored yet"})
            continue
        r = {"area": area, "role": role, "label": label, "masks": masks}
        r.update({c: round(float(wide.loc[label, c]), 4) for c in cols if pd.notna(wide.loc[label, c])})
        rows.append(r)
    pd.DataFrame(rows).to_csv(RES / "mirra_before_after.csv", index=False)
    pub = RES / "public"
    pub.mkdir(exist_ok=True)
    copied = []
    for name, src in PUBLIC.items():
        if src.exists():
            shutil.copy2(src, pub / name)
            copied.append(name)
        else:
            print("missing:", src)
    print(f"methods: {len(wide)}; before/after rows: {len(rows)}; public files copied: {len(copied)}")


if __name__ == "__main__":
    main()
