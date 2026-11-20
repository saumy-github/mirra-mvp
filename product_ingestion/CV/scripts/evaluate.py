"""Shared scoring for the CV project (owned by the orchestrator).

Every plan writes its predictions for the 5 Mirra photos in this STANDARD FORMAT,
then runs this script, so all methods are scored the same way:

    <pred_root>/<cloth>/            cloth = c_001 ... c_005
        mask.png              garment mask, 0/255, same size as the input photo
        palette.json          [{"hex": "#rrggbb", "share": 0.0-1.0, "role": "fabric|print|..."}]  (shares sum to 1)
        base_colour.json      {"hex": "#rrggbb"}   optional (else: the largest palette entry)
        design_regions.json   [{"box": [x0, y0, x1, y1] in PIXELS, "type": "text|graphic|logo|stripes|colour_block|pattern"}]
                              ([] means "no design found")
        view.json             {"view": "front|back|side|detail|other", "presentation": "flat|on_person|mannequin"}

Any subset of files may be present; missing files simply skip that area.

Usage:
    .venv/Scripts/python.exe product_ingestion/CV/scripts/evaluate.py --pred <pred_root> --label <method name> [--plan p01]

Prints a table and appends rows to results/mirra_scores.csv (label, plan, cloth, metric, value).
The metric functions (mask_metrics, palette_distance, design_scores) can also be imported
for public-dataset evaluation.

Reference labels are APPROXIMATE (out/p00_baseline/reference/labels.json); public datasets
give exact references and should be preferred for headline numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.color import deltaE_ciede2000, rgb2lab

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REF_DIR = ROOT / "out" / "p00_baseline" / "reference"
RESULTS = ROOT / "results"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


# ───────────────────────────── helpers ─────────────────────────────

def hex_to_lab(h: str) -> np.ndarray:
    h = h.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0
    return rgb2lab(rgb[None, None, :])[0, 0]


def entry_lab(e: dict) -> np.ndarray:
    if "lab" in e and e["lab"] is not None:
        return np.array(e["lab"], float)
    return hex_to_lab(e["hex"])


def de2000(a: np.ndarray, b: np.ndarray) -> float:
    return float(deltaE_ciede2000(np.asarray(a, float)[None, :], np.asarray(b, float)[None, :])[0])


def load_mask(path: Path, shape: tuple[int, int] | None = None) -> np.ndarray:
    m = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if m is None:
        raise FileNotFoundError(path)
    if m.ndim == 3:
        m = m[..., 3] if m.shape[2] == 4 else cv2.cvtColor(m, cv2.COLOR_BGR2GRAY)
    if shape is not None and m.shape[:2] != shape:
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return m > 127 if m.max() > 1 else m > 0


# ───────────────────────────── outline ─────────────────────────────

def _boundary(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8)
    er = cv2.erode(m, np.ones((3, 3), np.uint8))
    return (m - er) > 0


def mask_metrics(pred: np.ndarray, ref: np.ndarray) -> dict:
    """Region and boundary metrics. Distances are reported in % of the image diagonal."""
    pred = pred.astype(bool)
    ref = ref.astype(bool)
    h, w = ref.shape
    diag = float(np.hypot(h, w))
    inter = np.logical_and(pred, ref).sum()
    union = np.logical_or(pred, ref).sum()
    out = {
        "iou": inter / union if union else 1.0,
        "precision": inter / pred.sum() if pred.sum() else 0.0,
        "recall": inter / ref.sum() if ref.sum() else 1.0,
    }
    out["leakage"] = 1 - out["precision"]
    out["miss"] = 1 - out["recall"]
    bp, br = _boundary(pred), _boundary(ref)
    if bp.any() and br.any():
        dt_ref = distance_transform_edt(~br)
        dt_pred = distance_transform_edt(~bp)
        d_p2r = dt_ref[bp]
        d_r2p = dt_pred[br]
        for tol_pct in (0.5, 1.0, 2.0):
            tol = tol_pct / 100 * diag
            p = float((d_p2r <= tol).mean())
            r = float((d_r2p <= tol).mean())
            out[f"boundary_f@{tol_pct}%"] = 2 * p * r / (p + r) if (p + r) else 0.0
        out["hd95_pct_diag"] = float(np.percentile(np.concatenate([d_p2r, d_r2p]), 95) / diag * 100)
    else:
        for tol_pct in (0.5, 1.0, 2.0):
            out[f"boundary_f@{tol_pct}%"] = 0.0
        out["hd95_pct_diag"] = 100.0
    return {k: float(v) for k, v in out.items()}


# ───────────────────────────── colour ─────────────────────────────

def palette_distance(pred: list[dict], ref: list[dict], match_de: float = 10.0) -> dict:
    """Symmetric share-weighted ΔE2000 between two palettes.

    ref_to_pred: for each reference colour, ΔE to the closest predicted colour, weighted by its share.
    pred_to_ref: the same the other way round (penalises invented colours).
    palette_de:  mean of the two (lower is better).
    ref_share_matched: share of the reference palette with a predicted colour within match_de.
    """
    if not pred or not ref:
        return {"palette_de": 100.0, "ref_to_pred_de": 100.0, "pred_to_ref_de": 100.0, "ref_share_matched": 0.0}
    P = [(entry_lab(e), float(e.get("share", 0))) for e in pred]
    R = [(entry_lab(e), float(e.get("share", 0))) for e in ref]
    ps = sum(s for _, s in P) or 1.0
    rs = sum(s for _, s in R) or 1.0
    r2p = sum(s / rs * min(de2000(l, pl) for pl, _ in P) for l, s in R)
    p2r = sum(s / ps * min(de2000(l, rl) for rl, _ in R) for l, s in P)
    matched = sum(s / rs for l, s in R if min(de2000(l, pl) for pl, _ in P) <= match_de)
    return {"palette_de": (r2p + p2r) / 2, "ref_to_pred_de": r2p, "pred_to_ref_de": p2r, "ref_share_matched": matched}


def fabric_colour_scores(pred_palette: list[dict], ref_palette: list[dict], base_hex: str | None) -> dict:
    """ΔE of the predicted base colour to the main reference fabric, and whether every
    reference fabric colour (e.g. both blocks of a colour-block shirt) is present."""
    fabrics = [e for e in ref_palette if e.get("role", "").startswith("fabric")]
    main = max(fabrics, key=lambda e: e["share"])
    out = {}
    if base_hex:
        out["base_colour_de"] = de2000(hex_to_lab(base_hex), entry_lab(main))
    if pred_palette:
        worst = max(min(de2000(entry_lab(f), entry_lab(p)) for p in pred_palette) for f in fabrics)
        out["all_fabric_colours_found_de"] = worst  # max over fabric colours of the closest predicted colour
    return out


# ───────────────────────────── design ─────────────────────────────

def _box_iou(a, b) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def design_scores(pred: list[dict], ref: list[dict], garment: np.ndarray, iou_thr: float = 0.3) -> dict:
    """Detection-style scores for design regions (boxes in pixels).

    Colour-block regions are scored separately ("colour_block_found"), because they are
    a colour property rather than a printed design.
    """
    h, w = garment.shape
    ref_d = [r for r in ref if r["type"] != "colour_block"]
    pred_d = [p for p in pred if p.get("type") != "colour_block"]
    out = {"n_ref": len(ref_d), "n_pred": len(pred_d)}
    pairs = sorted(((_box_iou(p["box"], r["box"]), i, j) for i, p in enumerate(pred_d) for j, r in enumerate(ref_d)),
                   reverse=True)
    used_p, used_r, matches = set(), set(), []
    for iou, i, j in pairs:
        if iou < iou_thr or i in used_p or j in used_r:
            continue
        used_p.add(i); used_r.add(j); matches.append((i, j, iou))
    tp = len(matches)
    out["precision"] = tp / len(pred_d) if pred_d else (1.0 if not ref_d else 0.0)
    out["recall"] = tp / len(ref_d) if ref_d else 1.0
    out["f1"] = (2 * out["precision"] * out["recall"] / (out["precision"] + out["recall"])
                 if (out["precision"] + out["recall"]) else 0.0)
    out["type_accuracy_matched"] = (float(np.mean([pred_d[i]["type"] == ref_d[j]["type"] for i, j, _ in matches]))
                                    if matches else float("nan"))
    # pixel-level: union of design boxes inside the garment
    pm = np.zeros((h, w), bool)
    rm = np.zeros((h, w), bool)
    for p in pred_d:
        x0, y0, x1, y1 = [int(round(v)) for v in p["box"]]
        pm[max(0, y0):y1, max(0, x0):x1] = True
    for r in ref_d:
        x0, y0, x1, y1 = [int(round(v)) for v in r["box"]]
        rm[max(0, y0):y1, max(0, x0):x1] = True
    pm &= garment
    rm &= garment
    union = (pm | rm).sum()
    out["pixel_iou"] = float((pm & rm).sum() / union) if union else 1.0
    out["false_positive_on_plain"] = float(len(pred_d)) if not ref_d else float("nan")
    ref_cb = [r for r in ref if r["type"] == "colour_block"]
    if ref_cb:
        out["colour_block_found"] = float(any(p.get("type") == "colour_block" for p in pred))
    return out


# ───────────────────────────── loading references ─────────────────────────────

def load_reference() -> dict:
    labels = json.loads((REF_DIR / "labels.json").read_text(encoding="utf-8"))["cloths"]
    for c, e in labels.items():
        w, h = e["size_wh"]
        for d in e["designs"]:
            x0, y0, x1, y1 = d["box"]
            d["box_px"] = [x0 / 100 * w, y0 / 100 * h, x1 / 100 * w, y1 / 100 * h]
    return labels


def evaluate_cloth(pred_dir: Path, ref: dict) -> dict:
    w, h = ref["size_wh"]
    garment = load_mask(Path(ref["garment_mask"]), (h, w))
    res = {}
    if (pred_dir / "mask.png").exists():
        pm = load_mask(pred_dir / "mask.png", (h, w))
        res.update({f"mask.{k}": v for k, v in mask_metrics(pm, garment).items()})
    pal = None
    if (pred_dir / "palette.json").exists():
        pal = json.loads((pred_dir / "palette.json").read_text(encoding="utf-8"))
        res.update({f"colour.{k}": v for k, v in palette_distance(pal, ref["palette"]).items()})
        res["colour.n_colours"] = float(len(pal))
    base = None
    if (pred_dir / "base_colour.json").exists():
        base = json.loads((pred_dir / "base_colour.json").read_text(encoding="utf-8")).get("hex")
    elif pal:
        base = max(pal, key=lambda e: e.get("share", 0)).get("hex")
    if base or pal:
        res.update({f"colour.{k}": v for k, v in fabric_colour_scores(pal or [], ref["palette"], base).items()})
    if (pred_dir / "design_regions.json").exists():
        pred_d = json.loads((pred_dir / "design_regions.json").read_text(encoding="utf-8"))
        ref_d = [{"box": d["box_px"], "type": d["type"]} for d in ref["designs"]]
        for thr in (0.3, 0.5):
            for k, v in design_scores(pred_d, ref_d, garment, thr).items():
                if thr == 0.5 and k not in ("precision", "recall", "f1"):
                    continue
                res[f"design.{k}@{thr}" if k in ("precision", "recall", "f1") else f"design.{k}"] = v
    if (pred_dir / "view.json").exists():
        v = json.loads((pred_dir / "view.json").read_text(encoding="utf-8"))
        res["view.correct"] = float(v.get("view") == ref["view"])
        if v.get("presentation"):
            res["view.presentation_correct"] = float(v.get("presentation") == ref["presentation"])
    return res


# Summary scores in [0, 1] (higher is better). Primary metrics chosen in P00 from the
# damage tests (results/metric_sanity_*_summary.csv; plans/01_baseline_and_scoring.md):
#  - outline: IoU alone barely moves for border errors (1 % border shift -> 0.93) and boundary F
#    alone ignores area errors; their mean catches both. HD95 was rejected (not monotonic).
#  - colour: palette ΔE2000 is monotonic in colour shift and catches a dropped colour block;
#    the base-colour ΔE misses dropped blocks (0.40 when a whole block is lost), so it is only
#    a compatibility check.
#  - design: box F1 ignores wrong types and box shifts up to 50 %; pixel IoU catches shifts and
#    drops; type accuracy catches wrong labels. The score is their mean.
def summary_scores(mean: dict) -> dict:
    s = {}
    if "mask.boundary_f@1.0%" in mean:
        s["outline_score"] = 0.5 * mean["mask.iou"] + 0.5 * mean["mask.boundary_f@1.0%"]
    if "colour.palette_de" in mean:
        s["colour_score"] = max(0.0, 1 - mean["colour.palette_de"] / 30.0)
    if "design.f1@0.3" in mean:
        parts = [mean["design.f1@0.3"], mean.get("design.pixel_iou", 0.0),
                 mean.get("design.type_accuracy_matched", 0.0)]
        s["design_score"] = float(np.mean([0.0 if (p is None or np.isnan(p)) else p for p in parts]))
    if "view.correct" in mean:
        s["view_score"] = mean["view.correct"]
    present = [s[k] for k in ("outline_score", "colour_score", "design_score", "view_score") if k in s]
    if len(present) == 4:
        s["pipeline_score"] = float(np.mean(present))  # equal weights: the four areas matter equally to the user
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="prediction root with <cloth>/ subfolders")
    ap.add_argument("--label", required=True, help="method name for the results table")
    ap.add_argument("--plan", default="", help="plan id, e.g. p01")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()
    refs = load_reference()
    pred_root = Path(args.pred)
    rows, per = [], {}
    for c in CLOTHS:
        d = pred_root / c
        if not d.exists():
            continue
        r = evaluate_cloth(d, refs[c])
        per[c] = r
        for k, v in r.items():
            rows.append({"label": args.label, "plan": args.plan, "cloth": c, "metric": k, "value": v})
    keys = sorted({k for r in per.values() for k in r})
    mean = {k: float(np.nanmean([per[c][k] for c in per if k in per[c] and not np.isnan(per[c][k])]))
            for k in keys if any(k in per[c] and not np.isnan(per[c][k]) for c in per)}
    for k, v in mean.items():
        rows.append({"label": args.label, "plan": args.plan, "cloth": "mean", "metric": k, "value": v})
    for k, v in summary_scores(mean).items():
        rows.append({"label": args.label, "plan": args.plan, "cloth": "mean", "metric": f"summary.{k}", "value": v})
        mean[f"summary.{k}"] = v
    print(f"== {args.label}  ({pred_root})")
    width = max(len(k) for k in keys + list(mean)) if keys else 10
    print(f"{'metric':{width}s} " + " ".join(f"{c:>8s}" for c in per) + f" {'mean':>8s}")
    for k in sorted(mean):
        vals = " ".join(f"{per[c].get(k, float('nan')):8.3f}" for c in per)
        print(f"{k:{width}s} {vals} {mean[k]:8.3f}")
    if not args.no_save:
        RESULTS.mkdir(parents=True, exist_ok=True)
        path = RESULTS / "mirra_scores.csv"
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=["timestamp", "label", "plan", "cloth", "metric", "value"])
            if new:
                wr.writeheader()
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            for r in rows:
                wr.writerow({"timestamp": ts, **r})


if __name__ == "__main__":
    main()
