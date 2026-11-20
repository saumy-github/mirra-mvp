"""P07: semi-supervised pseudo-labelling (self-training) on cached features, grouped 5-fold CV on Fashionpedia val.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_semisup.py --backbone concat

Inside each training fold only a fraction of the crops keeps its label (the rest is treated as unlabelled);
self-training adds confident pseudo-labels for 3 rounds. Compared with: labelled-only, and all labels (upper bound).
"""
import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from p07_common import *  # noqa

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ap.add_argument("--backbone", default="concat")
ap.add_argument("--groups", nargs="+", default=["pattern", "sleeve3", "sleeve", "neckline"])
ap.add_argument("--out", default="try_01_valcv")
ap.add_argument("--thr", type=float, default=0.8)
a = ap.parse_args()
FEAT = OUT / "feats"
RES = OUT / a.out
RES.mkdir(parents=True, exist_ok=True)


def load(group, bb):
    df = pd.read_csv(OUT / "manifest_val.csv")
    mg = {"sleeve3": "sleeve"}.get(group, group)
    df = df[df.group == mg].reset_index(drop=True)
    tag = {"pattern": "pattern_mask"}.get(group, "sleeve" if group == "sleeve3" else group)
    names = ["siglip2", "fashion_siglip"] if bb == "concat" else [bb]
    X = np.concatenate([np.load(FEAT / f"{b}__val__{tag}.npy").astype(np.float32) for b in names], axis=1)
    lab = df.label.map(SLEEVE_MERGE3) if group == "sleeve3" else df.label
    cls = GROUP_CLASSES[group]
    keep = lab.isin(cls).values
    return X[keep], lab[keep].map({c: i for i, c in enumerate(cls)}).values, df[keep].image_id.values, len(cls)


def fit_lr(X, y):
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=0.05, class_weight="balanced", max_iter=400).fit(sc.transform(X), y)
    return lambda Z: m.predict_proba(sc.transform(Z)), m.classes_


def mf1(y, pred, K):
    present = [c for c in range(K) if (y == c).any()]
    return f1_score(y, pred, labels=present, average="macro", zero_division=0)


rows = []
rng = np.random.RandomState(0)
for group in a.groups:
    X, y, g, K = load(group, a.backbone)
    for frac in [0.05, 0.10, 0.25]:
        pr = {"labelled_only": np.zeros(len(y), int), "self_training": np.zeros(len(y), int), "all_labels": np.zeros(len(y), int)}
        for tr, te in GroupKFold(5).split(X, y, g):
            # choose labelled subset: at least 2 per class when available
            lab_idx = []
            for c in np.unique(y[tr]):
                ii = tr[y[tr] == c]
                k = max(2, int(round(frac * len(ii))))
                lab_idx += list(rng.choice(ii, min(k, len(ii)), replace=False))
            lab_idx = np.array(lab_idx)
            unl = np.setdiff1d(tr, lab_idx)
            f, cl = fit_lr(X[lab_idx], y[lab_idx])
            pr["labelled_only"][te] = cl[f(X[te]).argmax(1)]
            Xl, yl, pool = X[lab_idx], y[lab_idx], unl.copy()
            for _ in range(3):
                f, cl = fit_lr(Xl, yl)
                if not len(pool):
                    break
                p = f(X[pool])
                ok = p.max(1) >= a.thr
                if not ok.any():
                    break
                Xl = np.concatenate([X[lab_idx], X[pool[ok]]])
                yl = np.concatenate([y[lab_idx], cl[p[ok].argmax(1)]])
            f, cl = fit_lr(Xl, yl)
            pr["self_training"][te] = cl[f(X[te]).argmax(1)]
            f, cl = fit_lr(X[tr], y[tr])
            pr["all_labels"][te] = cl[f(X[te]).argmax(1)]
        for k, v in pr.items():
            rows.append(dict(group=group, backbone=a.backbone, labelled_frac=frac, method=k,
                             macro_f1=mf1(y, v, K), acc=float((v == y).mean()), n=len(y)))
            print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(RES / f"semisup_{a.backbone}.csv", index=False)
