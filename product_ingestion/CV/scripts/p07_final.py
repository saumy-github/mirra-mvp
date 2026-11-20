"""P07 step 4: extra variants, honest re-check of the chosen configs, confusion matrices, final model files.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_final.py
Needs cached features (p07_extract.py) and out/p07_attributes/try_01_valcv/results_valcv.csv + preds_valcv.pkl
(p07_train.py --protocol valcv --out try_01_valcv). CPU only.
"""
import json
import pickle
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from p07_common import *  # noqa

warnings.filterwarnings("ignore")
FEAT = OUT / "feats"
RES = OUT / "try_01_valcv"
FIG = OUT / "figs"
FIG.mkdir(exist_ok=True)
MODELS = REPO / "product_ingestion" / "models" / "attributes"
MODELS.mkdir(parents=True, exist_ok=True)
BB = {"siglip2": ["siglip2"], "fashion_siglip": ["fashion_siglip"], "concat": ["siglip2", "fashion_siglip"]}
COARSE = {"text": "print", "graphic": "print"}      # merge text + cartoon graphic into one class "print"


def load(group, bb, variant=None):
    df = pd.read_csv(OUT / "manifest_val.csv")
    mg = {"sleeve3": "sleeve", "pattern_coarse": "pattern", "pattern_both": "pattern"}.get(group, group)
    df = df[df.group == mg].reset_index(drop=True)
    parts = []
    for b in BB[bb]:
        if group in ("pattern", "pattern_coarse"):
            tags = ["pattern_mask"]
        elif group == "pattern_both":
            tags = ["pattern_mask", "pattern_raw"]
        else:
            tags = ["sleeve" if group == "sleeve3" else group]
        for t in tags:
            parts.append(np.load(FEAT / f"{b}__val__{t}.npy").astype(np.float32))
    X = np.concatenate(parts, 1)
    lab = df.label
    if group == "sleeve3":
        lab = lab.map(SLEEVE_MERGE3)
    cls = list(GROUP_CLASSES["pattern" if group.startswith("pattern") else group])
    if group == "pattern_coarse":
        lab = lab.map(lambda v: COARSE.get(v, v))
        cls = [c for c in cls if c not in COARSE] + ["print"]
    keep = lab.isin(cls).values
    y = lab[keep].map({c: i for i, c in enumerate(cls)}).values
    return X[keep], y, df[keep].image_id.values, cls


def build(cfg):
    base = cfg.replace("+zs", "")
    if base.startswith("lr"):
        C = float(base.split("@")[1]) if "@" in base else 0.05
        return Pipeline([("sc", StandardScaler()), ("lr", LogisticRegression(C=C, class_weight="balanced", max_iter=500))])
    if base == "ldaclf":
        return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")        # priors set by caller
    if base == "lda+knn":
        return Pipeline([("lda", LinearDiscriminantAnalysis(solver="eigen", shrinkage=0.1)),
                         ("knn", KNeighborsClassifier(n_neighbors=15, weights="distance"))])
    raise ValueError(cfg)


def fit_proba(cfg, Xtr, ytr, Xte, K, zs_text=None, Xzs_te=None):
    m = build(cfg)
    if cfg.startswith("ldaclf"):
        m.set_params(priors=np.ones(len(np.unique(ytr))) / len(np.unique(ytr)))
    m.fit(Xtr, ytr)
    p = np.zeros((len(Xte), K))
    p[:, m.classes_] = m.predict_proba(Xte)
    if cfg.endswith("+zs"):
        s = Xzs_te @ zs_text.T
        e = np.exp((s - s.max(1, keepdims=True)) * 100)
        e /= e.sum(1, keepdims=True)
        p = np.exp(np.log(p + 1e-6) + 0.5 * np.log(e + 1e-6))
        p /= p.sum(1, keepdims=True)
    return p, m


def text_for(group, bb):
    gname = {"pattern_coarse": "pattern", "pattern_both": "pattern"}.get(group, group)
    return np.load(FEAT / f"{BB[bb][0]}__text__{gname}.npy")


def coarse_text(group, T, cls):
    return T


def mf1(y, pred, K):
    present = [c for c in range(K) if (y == c).any()]
    return f1_score(y, pred, labels=present, average="macro", zero_division=0)


# ---------------------------------------------------- A. extra pattern variants (5-fold grouped CV)
extra = []
SKIP_A = (RES / "results_extra_pattern.csv").exists()
for group in ([] if SKIP_A else ["pattern_both", "pattern_coarse"]):
    for bb in ["siglip2", "fashion_siglip", "concat"]:
        X, y, g, cls = load(group, bb)
        K = len(cls)
        for cfg in ["lr", "lr@0.005", "ldaclf", "lda+knn"] + (["lr+zs", "ldaclf+zs"] if group == "pattern_coarse" and bb != "concat" else []):
            ps = np.zeros((len(y), K))
            for tr, te in GroupKFold(5).split(X, y, g):
                zt = None
                if cfg.endswith("+zs"):
                    T = text_for(group, bb)
                    # coarse: average the text embeddings of text + graphic
                    ncls = GROUP_CLASSES["pattern"]
                    Tm = np.stack([T[ncls.index(c)] for c in cls if c != "print"] + [(T[ncls.index("text")] + T[ncls.index("graphic")]) / 2])
                    zt = Tm / np.linalg.norm(Tm, axis=1, keepdims=True)
                ps[te], _ = fit_proba(cfg, X[tr], y[tr], X[te], K, zt, X[te])
            pred = ps.argmax(1)
            extra.append(dict(group=group, backbone=bb, clf=cfg, acc=accuracy_score(y, pred), bal_acc=balanced_accuracy_score(y, pred),
                              macro_f1=mf1(y, pred, K), n=len(y)))
            print(extra[-1], flush=True)
if not SKIP_A:
    pd.DataFrame(extra).to_csv(RES / "results_extra_pattern.csv", index=False)

# ---------------------------------------------------- B. choose per group (CV macro-F1, saveable configs only)
res = pd.read_csv(RES / "results_valcv.csv")
res = res[res.clf.isin(["lr", "lr@0.005", "lr@0.5", "ldaclf", "lda+knn", "lr+zs", "ldaclf+zs"])]
chosen = {}
for g in ["pattern", "sleeve", "sleeve3", "neckline"]:
    s = res[res.group == g].sort_values("macro_f1", ascending=False)
    # prefer single-backbone configs when within 0.01 of the best (faster inference)
    best = s.iloc[0]
    for _, r in s.iterrows():
        if r.backbone != "concat" and best.macro_f1 - r.macro_f1 <= 0.01:
            best = r
            break
    chosen[g] = dict(backbone=best.backbone, clf=best.clf, cv_acc=float(best.acc), cv_bal_acc=float(best.bal_acc), cv_macro_f1=float(best.macro_f1))
    print("chosen", g, chosen[g])

# ---------------------------------------------------- C. repeated 80/20 grouped hold-out of the chosen config
hold = []
for g, c in chosen.items():
    X, y, grp, cls = load(g, c["backbone"])
    K = len(cls)
    T = text_for(g, c["backbone"]) if c["clf"].endswith("+zs") else None
    for seed in range(5):
        tr, te = next(GroupShuffleSplit(1, test_size=0.2, random_state=100 + seed).split(X, y, grp))
        p, _ = fit_proba(c["clf"], X[tr], y[tr], X[te], K, T, X[te])
        pred = p.argmax(1)
        hold.append(dict(group=g, seed=seed, acc=accuracy_score(y[te], pred), bal_acc=balanced_accuracy_score(y[te], pred),
                         macro_f1=mf1(y[te], pred, K), n_test=len(te), majority_acc=float((y[te] == np.bincount(y[te]).argmax()).mean())))
hd = pd.DataFrame(hold)
hd.to_csv(RES / "holdout_chosen.csv", index=False)
print(hd.groupby("group")[["acc", "bal_acc", "macro_f1", "majority_acc"]].agg(["mean", "std"]).round(3).to_string())

# ---------------------------------------------------- D. confusion matrices from the CV predictions
preds = pickle.load(open(RES / "preds_valcv.pkl", "rb"))
recall_rows = []
for g, c in chosen.items():
    y, p = preds[(g, c["backbone"], c["clf"])]
    cls = GROUP_CLASSES[g]
    cm = confusion_matrix(y, p.argmax(1), labels=range(len(cls)))
    rec = cm.diagonal() / np.maximum(cm.sum(1), 1)
    for i, k in enumerate(cls):
        recall_rows.append(dict(group=g, cls=k, n=int(cm[i].sum()), recall=float(rec[i]) if cm[i].sum() else np.nan))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    for a_, mat, ttl, fmt in [(ax[0], cm, "counts", "d"), (ax[1], cm / np.maximum(cm.sum(1, keepdims=True), 1), "row-normalised (recall)", ".2f")]:
        a_.imshow(mat, cmap="Blues")
        a_.set_xticks(range(len(cls)), cls, rotation=60, ha="right", fontsize=8)
        a_.set_yticks(range(len(cls)), cls, fontsize=8)
        for i in range(len(cls)):
            for j in range(len(cls)):
                a_.text(j, i, format(mat[i, j], fmt), ha="center", va="center", fontsize=7, color="white" if mat[i, j] > mat.max() * 0.6 else "black")
        a_.set_xlabel("predicted")
        a_.set_ylabel("true")
        a_.set_title(ttl)
    fig.suptitle(f"{g}: {c['backbone']} / {c['clf']}  (5-fold grouped CV on Fashionpedia val, macro-F1 {c['cv_macro_f1']:.3f})")
    fig.tight_layout()
    fig.savefig(FIG / f"confusion_{g}.png", dpi=110)
    plt.close(fig)
pd.DataFrame(recall_rows).to_csv(RES / "per_class_recall_chosen.csv", index=False)

# ---------------------------------------------------- E. fit on all labelled data and save
for g, c in chosen.items():
    X, y, grp, cls = load(g, c["backbone"])
    K = len(cls)
    _, m = fit_proba(c["clf"].replace("+zs", ""), X, y, X[:2], K)
    bundle = dict(group=g, classes=cls, backbones=BB[c['backbone']], sk_model=m, n_classes=K)
    T = np.load(FEAT / f"{BB[c['backbone']][0]}__text__{g}.npy")
    bundle["text_emb"] = {BB[c["backbone"]][0]: T}
    bundle["zs_weight"] = 0.5 if c["clf"].endswith("+zs") else 0.0
    bundle["config"] = c
    bundle["trained_on"] = f"Fashionpedia val, {len(y)} crops, grouped by photo"
    pickle.dump(bundle, open(MODELS / f"{g}.pkl", "wb"))
    json.dump({**c, "classes": cls, "n_train": int(len(y)), "class_counts": {cls[i]: int((y == i).sum()) for i in range(K)}},
              open(MODELS / f"{g}.json", "w"), indent=1)
    print("saved", g)
json.dump({"chosen": chosen}, open(RES / "chosen.json", "w"), indent=1)
