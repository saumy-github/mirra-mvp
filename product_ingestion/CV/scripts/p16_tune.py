"""P16: set-level decision tuning and feature-level set evaluation.

1. Models are trained on the 85% of train items (same split as p16_train.py); validation sets are built from
   the other 15% of train items.  Grid search over back_threshold, usability_weight on those sets.
2. With the chosen parameters, the models trained on all train data are evaluated on test sets built from the
   In-shop test items (>= 2 photos), for: zero-shot probabilities and trained probabilities, independent argmax
   versus joint choice.
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_tune.py <backbone> [pre clf]
Outputs: out/p16_multiview/tuning_<backbone>.csv, sets_feature_level_<backbone>.csv, tuned_params_<backbone>.json
"""
from __future__ import annotations

import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '4')
import itertools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p16_common import loadf, FEAT, OUT, VIEW_CLASSES
from p16_sets import build_sets, run_feature_level, summarise
from p16_train import build, fit_model, load_meta, zero_shot_scores
from p16_train_aux import pair_data
from multi_view import pair_features

warnings.filterwarnings("ignore")
SEED = 0


def aligned_probs(model, X):
    pr = model.predict_proba(X)
    order = list(model.classes_)
    return pr[:, [order.index(c) for c in VIEW_CLASSES]]


def cues_dict(split):
    z = np.load(FEAT / f"cues_{split}.npz")
    return {k: z[k] for k in z.files}


def main(bb, pre=None, clf=None):
    if pre is None:
        b = json.loads((OUT / "best.json").read_text())["view_by_backbone"][bb]
        pre, clf = b["pre"], b["clf"]
    mtr, mte = load_meta("inshop_train"), load_meta("inshop_test")
    Xtr, Xte = loadf(FEAT / f"{bb}_inshop_train.npy"), loadf(FEAT / f"{bb}_inshop_test.npy")
    ytr = np.array([m["view"] for m in mtr])
    itr = np.array([m["item"] for m in mtr])
    ctr, cte = cues_dict("train"), cues_dict("test")
    tr_i, va_i = next(GroupShuffleSplit(1, test_size=0.15, random_state=SEED).split(Xtr, ytr, itr))
    # ---- models trained on tr_i only (for tuning) ----
    m_tune = build(pre, clf, 4, Xtr.shape[1])
    fit_model(m_tune, Xtr[tr_i], ytr[tr_i], clf_name=clf)
    Xp, yp = pair_data("train", bb, ctr["colour"], mtr, np.random.RandomState(SEED), cap_pos=6000, subset=tr_i)
    same_tune = LogisticRegression(C=10, max_iter=2000, class_weight="balanced").fit(Xp, yp)

    def pair_fn_factory(F, same, colour):
        cache = {}

        def fn(i, j):
            k = (min(i, j), max(i, j))
            if k not in cache:
                x = pair_features(F[i], F[j], colour[i], colour[j])
                cache[k] = float(same.predict_proba(x[None])[0, 1])
            return cache[k]
        return fn

    vsets = build_sets(mtr, va_i, seed=SEED)
    print("val sets", len(vsets), flush=True)
    vp = np.zeros((len(Xtr), 4))
    vp[va_i] = aligned_probs(m_tune, Xtr[va_i])
    pf = pair_fn_factory(Xtr, same_tune, ctr["colour"])
    rows = []
    for bt, uw in itertools.product([0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0.0, 0.3, 1.0]):
        prm = {"back_threshold": bt, "usability_weight": uw, "other_threshold": 2.0}
        res = summarise(run_feature_level(mtr, vsets, vp, pf, ctr, prm))
        rows.append({"back_threshold": bt, "usability_weight": uw, **res})
    dfv = pd.DataFrame(rows)
    dfv.to_csv(OUT / f"tuning_{bb}_{pre}_{clf}.csv", index=False)
    # choose on validation: joint pair accuracy, tie -> foreign_found
    best = dfv.sort_values(["pair_ok", "foreign_found"], ascending=False).iloc[0]
    params = {"back_threshold": float(best.back_threshold), "usability_weight": float(best.usability_weight),
              "other_threshold": 0.6}
    print("tuned", params, "val pair_ok", best.pair_ok, flush=True)
    (OUT / f"tuned_params_{bb}_{pre}_{clf}.json").write_text(json.dumps(params))

    # ---- test sets (models trained on all train) ----
    m_full = build(pre, clf, 4, Xtr.shape[1])
    fit_model(m_full, Xtr, ytr, clf_name=clf)
    Xp, yp = pair_data("train", bb, ctr["colour"], mtr, np.random.RandomState(SEED), cap_pos=6000)
    same_full = LogisticRegression(C=10, max_iter=2000, class_weight="balanced").fit(Xp, yp)
    tsets = build_sets(mte, range(len(mte)), seed=SEED)
    print("test sets", len(tsets), flush=True)
    pft = pair_fn_factory(Xte, same_full, cte["colour"])
    txt = np.load(FEAT / f"{bb}_text.npz")
    S = zero_shot_scores(Xte, txt, "view", VIEW_CLASSES)
    z = 100.0 * S
    z -= z.max(1, keepdims=True)
    zs = np.exp(z)
    zs /= zs.sum(1, keepdims=True)
    tp = aligned_probs(m_full, Xte)
    out = []
    for name, probs, prm in (
        ("zero-shot, joint", zs, params),
        ("trained, joint (tuned)", tp, params),
        ("trained, joint (default 0.5/0.3)", tp, {"back_threshold": 0.5, "usability_weight": 0.3, "other_threshold": 2.0}),
        ("trained, joint, no usability", tp, {**params, "usability_weight": 0.0}),
    ):
        res = summarise(run_feature_level(mte, tsets, probs, pft, cte, {**prm, "other_threshold": 2.0}))
        out.append({"method": name, **res})
    # no same-garment check (all photos kept)
    res = summarise(run_feature_level(mte, tsets, tp, lambda i, j: 1.0, cte, {**params, "other_threshold": 2.0}))
    out.append({"method": "trained, joint, no same-garment check", **res})
    # first photo = front baseline (shuffled order), chance level
    from p16_sets import truth_for
    first = [(s["indices"][0] in truth_for(mte, s)["front"]) for s in tsets if truth_for(mte, s)["front"]]
    out.append({"method": "baseline: first photo is front", "front_ok": float(np.mean(first)), "front_ok_n": len(first)})
    dft = pd.DataFrame(out)
    dft.insert(0, "backbone", bb)
    dft.to_csv(OUT / f"sets_feature_level_{bb}_{pre}_{clf}.csv", index=False)
    print(dft.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
