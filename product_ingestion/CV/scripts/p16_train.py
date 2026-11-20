"""P16: train and compare view and presentation classifiers on cached frozen features.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_train.py
Needs features from p16_extract_features.py. CPU only, seeds fixed.
Outputs (out/p16_multiview/):
  results_view.csv            validation (held-out train items) and test metrics for every backbone x preproc x classifier
  results_presentation.csv    same for the flat vs person classifier
  cm_view_<name>.png          confusion matrices (best models and all zero-shot)
  best.json                   the chosen configurations
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import json
import sys
import time
import warnings
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p16_common import loadf, FEAT, MIRRA_TRUTH, OUT, PRES_PROMPTS, VIEW_CLASSES, VIEW_PROMPTS

warnings.filterwarnings("ignore")
SEED = 0
BACKS = ["siglip2", "marqo"]  # CLIP ViT-L/14 dropped (orchestrator: memory/disk)


def load_meta(name):
    return json.loads((FEAT / f"meta_{name}.json").read_text())


def oversample(X, y, groups=None, seed=SEED):
    """Random oversampling of minority classes up to the majority count."""
    rng = np.random.RandomState(seed)
    classes, counts = np.unique(y, return_counts=True)
    m = min(counts.max(), 2500)          # balanced resampling: every class gets <= 2500 rows
    idx = []
    for c in classes:
        ci = np.where(y == c)[0]
        idx.append(rng.choice(ci, m, replace=len(ci) < m))
    idx = np.concatenate(idx)
    return X[idx], y[idx]


def make_clf(name, n_classes):
    if name == "nb":
        return GaussianNB()
    if name == "knn":
        return KNeighborsClassifier(n_neighbors=15, weights="distance", metric="cosine")
    if name == "lr":
        return LogisticRegression(C=2.0, max_iter=2000, class_weight="balanced", random_state=SEED)
    if name == "mlp":
        return MLPClassifier(hidden_layer_sizes=(128,), alpha=1e-3, max_iter=60, early_stopping=True,
                             n_iter_no_change=8, random_state=SEED)
    raise ValueError(name)


def make_pre(name, n_classes, dim):
    if name == "none":
        return []
    if name == "pca":
        return [("pca", PCA(n_components=64, random_state=SEED, whiten=False))]
    if name == "lda":
        return [("lda", LinearDiscriminantAnalysis(n_components=min(n_classes - 1, dim)))]
    if name == "pca+lda":
        return [("pca", PCA(n_components=64, random_state=SEED)), ("lda", LinearDiscriminantAnalysis(n_components=n_classes - 1))]
    raise ValueError(name)


def build(pre, clf, n_classes, dim):
    return Pipeline(make_pre(pre, n_classes, dim) + [("clf", make_clf(clf, n_classes))])


def fit_model(model, X, y, balanced=True, clf_name=None):
    # logistic regression uses class_weight; MLP and KNN/NB use random oversampling
    if balanced and clf_name in ("mlp", "knn", "nb"):
        X, y = oversample(X, y)
    model.fit(X, y)
    return model


def metrics(y, p, classes):
    return {"acc": accuracy_score(y, p), "macro_f1": f1_score(y, p, average="macro", labels=classes),
            **{f"recall_{c}": recall_score(y, p, labels=[c], average="macro", zero_division=0) for c in classes}}


def plot_cm(y, p, classes, title, path):
    cm = confusion_matrix(y, p, labels=classes)
    cmn = cm / np.maximum(cm.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(classes)), classes, rotation=30)
    ax.set_yticks(range(len(classes)), classes)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", color="white" if cmn[i, j] > .5 else "black", fontsize=8)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def zero_shot_scores(F, txt, prefix, classes):
    """Mean-of-prompts text embedding per class -> cosine logits."""
    T = np.stack([txt[f"{prefix}_{c}"].mean(0) for c in classes])
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    return F @ T.T


def main():
    t_all = time.time()
    mtr, mte = load_meta("inshop_train"), load_meta("inshop_test")
    ytr = np.array([m["view"] for m in mtr])
    yte = np.array([m["view"] for m in mte])
    itr = np.array([m["item"] for m in mtr])
    print("item overlap train/test:", len(set(itr) & {m["item"] for m in mte}))
    gss = GroupShuffleSplit(1, test_size=0.15, random_state=SEED)
    tr_i, va_i = next(gss.split(np.zeros(len(ytr)), ytr, itr))
    mir = load_meta("mirra")
    mir_truth = [MIRRA_TRUTH[m["cloth"]]["view"] for m in mir]
    classes = VIEW_CLASSES
    tr_items = set(itr.tolist())
    disj = np.array([m['item'] not in tr_items for m in mte])
    print('test photos in items not seen in train:', int(disj.sum()), 'of', len(disj))
    rows, zs_rows = [], []
    best = {}
    cm_dir = OUT
    for bb in BACKS:
        if not (FEAT / f"{bb}_inshop_test.npy").exists():
            print("missing", bb)
            continue
        Xtr = loadf(FEAT / f"{bb}_inshop_train.npy")
        Xte = loadf(FEAT / f"{bb}_inshop_test.npy")
        Xm = loadf(FEAT / f"{bb}_mirra.npy")
        txt = np.load(FEAT / f"{bb}_text.npz")
        # --- zero-shot (4 classes, 'additional' = close-up prompts) ---
        for tag, cls4 in (("zs4", classes), ):
            S = zero_shot_scores(Xte, txt, "view", cls4)
            p = np.array(cls4)[S.argmax(1)]
            r = {"backbone": bb, "method": "zero-shot", **metrics(yte, p, classes)}
            Sm = zero_shot_scores(Xm, txt, "view", cls4 + ["other"])
            pm = np.array(cls4 + ["other"])[Sm.argmax(1)]
            r["mirra_acc"] = float(np.mean(pm == np.array(mir_truth)))
            r["mirra_pred"] = ",".join(pm)
            zs_rows.append(r)
            plot_cm(yte, p, classes, f"zero-shot {bb} (test)", cm_dir / f"cm_view_zeroshot_{bb}.png")
        # --- trained ---
        for pre in ("none", "pca", "lda", "pca+lda"):
            for clf in ("nb", "knn", "lr", "mlp"):
                t0 = time.time()
                m = build(pre, clf, len(classes), Xtr.shape[1])
                fit_model(m, Xtr[tr_i], ytr[tr_i], clf_name=clf)
                pv = m.predict(Xtr[va_i])
                mv = metrics(ytr[va_i], pv, classes)
                # refit on all train, evaluate on test
                m2 = build(pre, clf, len(classes), Xtr.shape[1])
                fit_model(m2, Xtr, ytr, clf_name=clf)
                pt = m2.predict(Xte)
                mt = metrics(yte, pt, classes)
                md = metrics(yte[disj], pt[disj], classes)
                pm = m2.predict(Xm)
                r = {"backbone": bb, "pre": pre, "clf": clf, "val_acc": mv["acc"], "val_macro_f1": mv["macro_f1"],
                     **{f"test_{k}": v for k, v in mt.items()},
                     "unseen_acc": md["acc"], "unseen_macro_f1": md["macro_f1"],
                     "mirra_acc": float(np.mean(pm == np.array(mir_truth))), "mirra_pred": ",".join(pm),
                     "fit_s": round(time.time() - t0, 1)}
                rows.append(r)
                print(bb, pre, clf, "val_f1=%.3f test_acc=%.3f test_f1=%.3f" % (mv["macro_f1"], mt["acc"], mt["macro_f1"]), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "results_view.csv", index=False)
    pd.DataFrame(zs_rows).to_csv(OUT / "results_view_zeroshot.csv", index=False)
    # choose by validation macro-F1 (not by test)
    b = df.sort_values("val_macro_f1", ascending=False).iloc[0]
    print("BEST by val macro-F1:", b[["backbone", "pre", "clf", "val_macro_f1", "test_acc", "test_macro_f1"]].to_dict())
    best["view"] = {k: (v if isinstance(v, str) else float(v)) for k, v in b.items() if k in ("backbone", "pre", "clf", "val_macro_f1", "test_acc", "test_macro_f1")}
    # confusion matrix for the best model and for best of each backbone
    for bbn, g in df.groupby("backbone"):
        bb_best = g.sort_values("val_macro_f1", ascending=False).iloc[0]
        Xtr = loadf(FEAT / f"{bbn}_inshop_train.npy")
        Xte = loadf(FEAT / f"{bbn}_inshop_test.npy")
        m2 = build(bb_best.pre, bb_best.clf, len(classes), Xtr.shape[1])
        fit_model(m2, Xtr, ytr, clf_name=bb_best.clf)
        plot_cm(yte, m2.predict(Xte), classes, f"{bbn} {bb_best.pre}+{bb_best.clf} (test)", cm_dir / f"cm_view_{bbn}_{bb_best.pre}_{bb_best.clf}.png")
        best.setdefault("view_by_backbone", {})[bbn] = {"pre": bb_best.pre, "clf": bb_best.clf,
                                                       "val_macro_f1": float(bb_best.val_macro_f1), "test_macro_f1": float(bb_best.test_macro_f1)}
    (OUT / "best.json").write_text(json.dumps(best, indent=1))
    print("done", round(time.time() - t_all), "s")


if __name__ == "__main__":
    main()
