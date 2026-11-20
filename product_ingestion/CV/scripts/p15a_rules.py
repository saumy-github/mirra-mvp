"""P15a stage 2: evaluate selection rules between v1 and v1_all offline on the features of p15a_features.py.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_rules.py [--features features.csv] [--tag base]

A rule maps an image's feature row to True (use the v1_all mask) or False (use the v1 mask). The IoU of the chosen
mask is read from the per-image IoUs of both masks (computed once, same scoring as P01). Reports public macro IoU,
per-set IoU, failure rate (IoU < 0.1 over the 400 public images), paired bootstrap 95 % CI of (rule - v1) and
(rule - v1_all) per set and for the macro mean (2000 resamples within each set, seed 0), and Mirra per-photo IoU.
Outputs: out/p15a_seg_autoselect/rules_<tag>.csv (summary), rules_<tag>_bootstrap.csv, rules_<tag>_mirra.csv.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P15 = ROOT / "out" / "p15a_seg_autoselect"
PUB = ["viton_cloth", "viton_person", "fashionpedia"]


def choose_iou(df, use_all):
    return np.where(use_all, df.iou_v1a.values, df.iou_v1.values)


def summarize(df, ious, name):
    r = {"rule": name}
    m = []
    for s in PUB:
        v = ious[(df.set == s).values].mean()
        r[s] = v
        m.append(v)
    r["public_macro"] = float(np.mean(m))
    pub = (df.set != "mirra").values
    r["fail_rate"] = float((ious[pub] < 0.1).mean())
    mi = ious[(df.set == "mirra").values]
    r["mirra_mean"] = float(mi.mean()) if len(mi) else float("nan")
    for c, v in zip(df[df.set == "mirra"].id, mi):
        r[c] = float(v)
    return r


def boot(df, a, b, n_boot=2000, seed=0):
    """paired bootstrap of mean(a - b): per set and macro. a, b arrays aligned with df rows."""
    rng = np.random.default_rng(seed)
    d = a - b
    out = {}
    per = {}
    for s in PUB:
        x = d[(df.set == s).values]
        idx = rng.integers(0, len(x), size=(n_boot, len(x)))
        per[s] = x[idx].mean(1)
        out[s] = (float(x.mean()), *np.percentile(per[s], [2.5, 97.5]))
    mac = np.mean([per[s] for s in PUB], axis=0)
    out["macro"] = (float(np.mean([out[s][0] for s in PUB])), *np.percentile(mac, [2.5, 97.5]))
    return out


def run(df, rules, tag):
    base_v1 = choose_iou(df, np.zeros(len(df), bool))
    base_all = choose_iou(df, np.ones(len(df), bool))
    rows, brows = [], []
    pub = (df.set != "mirra").values
    for name, use in rules.items():
        use = np.asarray(use, bool)
        ious = choose_iou(df, use)
        r = summarize(df, ious, name)
        r["n_all_public"] = int(use[pub].sum())
        rows.append(r)
        for ref, refv in (("v1", base_v1), ("v1_all", base_all)):
            b = boot(df, ious, refv)
            for k, (m, lo, hi) in b.items():
                brows.append({"rule": name, "vs": ref, "set": k, "mean_diff": m, "ci_lo": lo, "ci_hi": hi})
    res = pd.DataFrame(rows)
    bs = pd.DataFrame(brows)
    res.to_csv(P15 / f"rules_{tag}.csv", index=False)
    bs.to_csv(P15 / f"rules_{tag}_bootstrap.csv", index=False)
    return res, bs


def fmt(res, bs):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.max_rows", 300)
    t = res.copy()
    for vs in ("v1", "v1_all"):
        b = bs[(bs.vs == vs) & (bs.set == "macro")].set_index("rule")
        t[f"macro_vs_{vs}"] = [f"{b.loc[x, 'mean_diff']:+.4f} ({b.loc[x, 'ci_lo']:+.4f},{b.loc[x, 'ci_hi']:+.4f})" for x in t.rule]
    cols = [c for c in ["rule", "viton_cloth", "viton_person", "fashionpedia", "public_macro", "fail_rate", "mirra_mean", "c_003",
            "n_all_public", "macro_vs_v1", "macro_vs_v1_all"] if c in t.columns]
    return t[cols].round(4).to_string(index=False)


def base_rules(df):
    n = len(df)
    skirt = (df.skirt_frac >= 0.01).values
    head = (df.face_frac + df.hair_frac).values
    low = df.lower_frac.values
    contact = df.contact_ratio.values
    R = {"v1": np.zeros(n, bool), "v1_all": np.ones(n, bool)}
    R["oracle"] = (df.iou_v1a > df.iou_v1).values
    # idea 2: choose by SAM 2 predicted IoU
    R["sam_higher"] = (df.sam_v1a > df.sam_v1).values
    R["sam_higher_m0.02"] = (df.sam_v1a > df.sam_v1 + 0.02).values
    R["edge_higher"] = (df.edge_v1a > df.edge_v1).values
    # idea 1: geometry only (skirt directly under the top, reaches the image bottom, no lower body, no waist)
    geo = skirt & (contact >= 0.5) & (df.skirt_bottom_gap.values < 0.02) & (low < 0.03) & (df.narrow_ratio.values >= 0.9)
    R["geo_only"] = geo
    # head visibility
    for t in (0.005, 0.01, 0.02):
        R[f"head<{t}"] = skirt & (head < t)
        R[f"head<{t}&nolower"] = skirt & (head < t) & (low < 0.03)
    R["head<0.01&geo"] = geo & (head < 0.01)
    # SegFormer's own ambiguity: share of top probability inside the Skirt region
    if "pS_top_share" in df:
        amb = df.pS_top_share.fillna(0).values
        for t in (0.3, 0.33):
            R[f"ambig>{t}"] = skirt & (amb > t)
            R[f"head<0.01|ambig>{t}"] = skirt & ((head < 0.01) | (amb > t))
    # SAM 2 with a prompt on the Skirt region only: does its mask spill into the top?
    if "sk_in_T" in df:
        sp = df.sk_in_T.fillna(0).values
        R["skirtSAM_spill>0.05"] = skirt & (sp > 0.05)
        R["head<0.01|skirtSAM_spill>0.05"] = skirt & ((head < 0.01) | (sp > 0.05))
        # SAM 2: TOP box + negative point in the Skirt: does SAM still keep (almost) all of the v1 mask?
        R["skirt_sk_iou<0.95"] = skirt & (df.sk_iou_S.fillna(1).values < 0.95)
    # SAM 2 predicted IoU gap, restricted to no-head photos / all photos
    R["head<0.01&sam_higher"] = skirt & (head < 0.01) & (df.sam_v1a > df.sam_v1).values
    R["skirt&sam_higher_m0.02"] = skirt & (df.sam_v1a > df.sam_v1 + 0.02).values
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", default=["features.csv"])
    ap.add_argument("--tag", default="base")
    a = ap.parse_args()
    df = pd.concat([pd.read_csv(P15 / f) for f in a.features], ignore_index=True)
    res, bs = run(df, base_rules(df), a.tag)
    print(fmt(res, bs))
