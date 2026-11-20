"""P16: presentation classifier (flat vs person) and same-garment pair classifier, on cached features.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_train_aux.py
Outputs (out/p16_multiview/): results_presentation.csv, results_same_garment.csv, cm_pres_<backbone>.png
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p16_common import loadf, FEAT, MIRRA_TRUTH, OUT
from p16_train import BACKS, build, fit_model, load_meta, plot_cm, zero_shot_scores
from multi_view import colour_overlap

warnings.filterwarnings("ignore")
SEED = 0
PRES = ["flat", "person"]


def pres_data(bb):
    Fv = loadf(FEAT / f"{bb}_viton.npy")
    n = len(Fv) // 2
    Ftr = loadf(FEAT / f"{bb}_inshop_train.npy")
    Fte = loadf(FEAT / f"{bb}_inshop_test.npy")
    rng = np.random.RandomState(SEED)
    ins_tr = rng.choice(len(Ftr), 800, replace=False)
    return Fv, n, Ftr[ins_tr], Fte


def run_presentation():
    rows = []
    mir = load_meta("mirra")
    mt = np.array([MIRRA_TRUTH[m["cloth"]]["pres"] for m in mir])
    for bb in BACKS:
        if not (FEAT / f"{bb}_mirra.npy").exists():
            continue
        Fv, n, Fins, Fte = pres_data(bb)
        Xm = loadf(FEAT / f"{bb}_mirra.npy")
        txt = np.load(FEAT / f"{bb}_text.npz")
        # rows 0..n-1 = cloth (flat) / rows n..2n-1 = person; the same index k is the same VITON row
        gss = GroupShuffleSplit(1, test_size=0.25, random_state=SEED)
        grp = np.concatenate([np.arange(n), np.arange(n)])
        y_v = np.array(["flat"] * n + ["person"] * n)
        tr, te = next(gss.split(Fv, y_v, grp))
        # In-shop person photos (800 train, test split) join the person class; 4/5 of the train rows train
        Xtr = np.concatenate([Fv[tr], Fins])
        ytr = np.concatenate([y_v[tr], ["person"] * len(Fins)])
        # zero-shot
        for pre in ("none", "pca"):
            for clf in ("nb", "knn", "lr", "mlp"):
                m = build(pre, clf, 2, Xtr.shape[1])
                fit_model(m, Xtr, ytr, clf_name=clf)
                pv = m.predict(Fv[te])
                pi = m.predict(Fte)
                pm = m.predict(Xm)
                rows.append({"backbone": bb, "pre": pre, "clf": clf, "viton_test_acc": accuracy_score(y_v[te], pv),
                             "viton_test_macro_f1": f1_score(y_v[te], pv, average="macro"),
                             "viton_flat_recall": float(np.mean(pv[y_v[te] == "flat"] == "flat")),
                             "inshop_test_person_recall": float(np.mean(pi == "person")),
                             "mirra_acc": float(np.mean(pm == mt)), "mirra_pred": ",".join(pm)})
        Sv = zero_shot_scores(Fv[te], txt, "pres", ["flat", "mannequin", "person"])
        names = np.array(["flat", "mannequin", "person"])
        pz = names[Sv.argmax(1)]
        pz2 = np.where(pz == "mannequin", "person", pz)  # no mannequin truth in the data
        Si = zero_shot_scores(Fte, txt, "pres", ["flat", "mannequin", "person"])
        Sm = zero_shot_scores(Xm, txt, "pres", ["flat", "mannequin", "person"])
        pmz = names[Sm.argmax(1)]
        rows.append({"backbone": bb, "pre": "-", "clf": "zero-shot(3 prompts)", "viton_test_acc": accuracy_score(y_v[te], pz2),
                     "viton_test_macro_f1": f1_score(y_v[te], pz2, average="macro"),
                     "viton_flat_recall": float(np.mean(pz2[y_v[te] == "flat"] == "flat")),
                     "inshop_test_person_recall": float(np.mean(names[Si.argmax(1)] != "flat")),
                     "mirra_acc": float(np.mean(np.where(pmz == "mannequin", "person", pmz) == mt)), "mirra_pred": ",".join(pmz)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "results_presentation.csv", index=False)
    print(df.sort_values("viton_test_macro_f1", ascending=False).head(12).to_string())
    return df


def pair_data(split, bb, colours, meta, rng, n_neg_per_pos=1, cap_pos=None, subset=None):
    F = loadf(FEAT / f"{bb}_inshop_{split}.npy")
    items = {}
    allowed = None if subset is None else set(int(i) for i in subset)
    for i, m in enumerate(meta):
        if allowed is None or i in allowed:
            items.setdefault(m["item"], []).append(i)
    cat = [m["relpath"].split("/")[1] for m in meta]
    multi = [v for v in items.values() if len(v) >= 2]
    pos, neg = [], []
    for v in multi:
        for a in range(len(v)):
            for b in range(a + 1, len(v)):
                pos.append((v[a], v[b]))
    if cap_pos and len(pos) > cap_pos:
        pos = [pos[k] for k in rng.choice(len(pos), cap_pos, replace=False)]
    by_cat = {}
    for i, c in enumerate(cat):
        if allowed is None or i in allowed:
            by_cat.setdefault(c, []).append(i)
    all_idx = sorted(allowed) if allowed is not None else list(range(len(meta)))
    for (a, b) in pos:
        for _ in range(n_neg_per_pos):
            # half hard negatives (same category folder), half random
            pool = by_cat[cat[a]] if rng.rand() < 0.5 else all_idx
            pool = list(pool)
            while True:
                j = int(pool[rng.randint(len(pool))])
                if meta[j]["item"] != meta[a]["item"]:
                    break
            neg.append((a, j))
    pairs = pos + neg
    y = np.array([1] * len(pos) + [0] * len(neg))

    def feats(a, b):
        ab, l = colour_overlap(colours[a], colours[b])
        return [float(F[a] @ F[b]), ab, l, ab * l]
    X = np.array([feats(a, b) for a, b in pairs], dtype=np.float32)
    return X, y


def run_same_garment():
    rows = []
    mtr, mte = load_meta("inshop_train"), load_meta("inshop_test")
    ctr = np.load(FEAT / "cues_train.npz")["colour"]
    cte = np.load(FEAT / "cues_test.npz")["colour"]
    for bb in BACKS:
        if not (FEAT / f"{bb}_inshop_test.npy").exists():
            continue
        rng = np.random.RandomState(SEED)
        Xtr, ytr = pair_data("train", bb, ctr, mtr, rng, cap_pos=6000)
        Xte, yte = pair_data("test", bb, cte, mte, np.random.RandomState(SEED + 1))
        for name, cols in (("feature cosine only", [0]), ("colour overlap only", [1, 2, 3]), ("cosine + colour", [0, 1, 2, 3])):
            lr = LogisticRegression(C=10, max_iter=2000, class_weight="balanced").fit(Xtr[:, cols], ytr)
            p = lr.predict_proba(Xte[:, cols])[:, 1]
            rows.append({"backbone": bb, "features": name, "auc": roc_auc_score(yte, p),
                         "acc@0.5": accuracy_score(yte, p > 0.5), "n_pos": int(yte.sum()), "n_neg": int((1 - yte).sum())})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "results_same_garment.csv", index=False)
    print(df.to_string())
    return df


if __name__ == "__main__":
    run_presentation()
    run_same_garment()
