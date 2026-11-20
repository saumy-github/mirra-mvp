"""P07 step 3: train and compare classifiers on cached features.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_train.py --protocol train2val --out try_01
  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_train.py --protocol valcv --out try_01

protocol train2val : train on Fashionpedia TRAIN subset (grouped 3-fold CV on it selects the best config),
                     test on the full official VAL set (never used for fitting or selection).
protocol valcv     : grouped (by photo) 5-fold cross-validation inside VAL only (fallback / extra number).
CPU only (sklearn + a tiny torch MLP on CPU), so no GPU lock needed.
"""
import argparse
import json
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from p07_common import *  # noqa

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ap.add_argument("--protocol", choices=["train2val", "valcv"], required=True)
ap.add_argument("--out", default="try_01")
ap.add_argument("--backbones", nargs="+", default=["siglip2", "fashion_siglip", "concat"])
ap.add_argument("--groups", nargs="+", default=["pattern", "pattern_raw", "sleeve", "sleeve3", "neckline"])
ap.add_argument("--max_train_per_class", type=int, default=0)
a = ap.parse_args()
RES = OUT / a.out
RES.mkdir(parents=True, exist_ok=True)
FEAT = OUT / "feats"
SEED = 0


# ------------------------------------------------------------------ data
def feat_tag(group):
    return {"pattern": "pattern_mask", "pattern_raw": "pattern_raw", "sleeve3": "sleeve"}.get(group, group)


def man_group(group):
    return {"pattern_raw": "pattern", "sleeve3": "sleeve"}.get(group, group)


def classes_of(group):
    return GROUP_CLASSES["pattern" if group == "pattern_raw" else group]


def load(split, group, backbone):
    df = pd.read_csv(OUT / f"manifest_{split}.csv")
    df = df[df.group == man_group(group)].reset_index(drop=True)
    names = ["siglip2", "fashion_siglip"] if backbone == "concat" else [backbone]
    X = np.concatenate([np.load(FEAT / f"{b}__{split}__{feat_tag(group)}.npy").astype(np.float32) for b in names], axis=1)
    assert len(X) == len(df), (split, group, backbone, len(X), len(df))
    lab = df.label.copy()
    if group == "sleeve3":
        lab = lab.map(SLEEVE_MERGE3)
    cls = classes_of(group)
    keep = lab.isin(cls).values & (df.multi.values == 0 if group != "sleeve3" and group != "sleeve" else True)
    if group in ("sleeve", "sleeve3"):
        keep = lab.isin(cls).values       # sleeve multi = several lengths; label already the longest
    y = lab[keep].map({c: i for i, c in enumerate(cls)}).values
    return X[keep] / (np.linalg.norm(X[keep], axis=1, keepdims=True) / np.sqrt(len(names)) + 1e-9), y, df[keep].image_id.values, df[keep].reset_index(drop=True)


# ------------------------------------------------------------ classifiers
class TorchMLP:
    def __init__(self, hidden=512, epochs=60, lr=2e-3, wd=1e-3, drop=0.3, seed=SEED):
        self.h, self.ep, self.lr, self.wd, self.drop, self.seed = hidden, epochs, lr, wd, drop, seed

    def fit(self, X, y, K):
        import torch
        torch.manual_seed(self.seed)
        torch.set_num_threads(4)
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-6
        Xt = torch.tensor((X - self.mu) / self.sd, dtype=torch.float32)
        yt = torch.tensor(np.asarray(y), dtype=torch.long)
        cnt = np.bincount(y, minlength=K).astype(float)
        w = torch.tensor(np.where(cnt > 0, len(y) / (K * np.maximum(cnt, 1)), 0.0), dtype=torch.float32)
        self.net = torch.nn.Sequential(torch.nn.Dropout(0.1), torch.nn.Linear(X.shape[1], self.h), torch.nn.GELU(),
                                       torch.nn.Dropout(self.drop), torch.nn.Linear(self.h, K))
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=self.wd)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=self.lr, total_steps=self.ep * ((len(y) + 127) // 128))
        g = torch.Generator().manual_seed(self.seed)
        for _ in range(self.ep):
            self.net.train()
            perm = torch.randperm(len(y), generator=g)
            for i in range(0, len(y), 128):
                idx = perm[i:i + 128]
                loss = torch.nn.functional.cross_entropy(self.net(Xt[idx]), yt[idx], weight=w, label_smoothing=0.05)
                opt.zero_grad()
                loss.backward()
                opt.step()
                sched.step()
        return self

    def predict_proba(self, X):
        import torch
        self.net.eval()
        with torch.no_grad():
            return torch.softmax(self.net(torch.tensor((X - self.mu) / self.sd, dtype=torch.float32)), 1).numpy()


def full_proba(model, X, K, classes_seen):
    p = model.predict_proba(X)
    out = np.zeros((len(X), K))
    out[:, classes_seen] = p
    return out


def make(name, K, ncomp):
    """Return fit_predict(Xtr, ytr, Xte) -> proba (n, K). ncomp = PCA/LDA dims."""
    def fp(Xtr, ytr, Xte):
        seen = np.unique(ytr)
        Xa, Xb = Xtr, Xte
        pre = name.split("+")
        base = pre[-1]
        for step in pre[:-1]:
            if step == "pca":
                pc = PCA(n_components=min(ncomp, Xa.shape[1], len(Xa) - 1), whiten=True, random_state=SEED).fit(Xa)
                Xa, Xb = pc.transform(Xa), pc.transform(Xb)
            elif step == "lda":
                nc = min(len(seen) - 1, Xa.shape[1])
                ld = LinearDiscriminantAnalysis(n_components=nc, solver="eigen", shrinkage=0.1).fit(Xa, ytr)
                Xa, Xb = ld.transform(Xa), ld.transform(Xb)
        if base == "nb":
            m = GaussianNB(priors=np.ones(len(seen)) / len(seen), var_smoothing=1e-3).fit(Xa, ytr)
        elif base == "knn":
            m = KNeighborsClassifier(n_neighbors=15, weights="distance", metric="cosine" if not pre[:-1] else "euclidean").fit(Xa, ytr)
        elif base.startswith("lr"):
            Cv = float(base.split("@")[1]) if "@" in base else 0.05
            sc = StandardScaler().fit(Xa)
            m = _Wrap(LogisticRegression(C=Cv, class_weight="balanced", max_iter=400), sc).fit(Xa, ytr)
        elif base == "ldaclf":
            m = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=np.ones(len(seen)) / len(seen)).fit(Xa, ytr)
        elif base == "mlp":
            m = _MLPWrap(K).fit(Xa, ytr)
        else:
            raise ValueError(name)
        return full_proba(m, Xb, K, seen)
    return fp


class _Wrap:
    def __init__(self, clf, sc):
        self.clf, self.sc = clf, sc

    def fit(self, X, y):
        self.clf.fit(self.sc.transform(X), y)
        return self

    def predict_proba(self, X):
        return self.clf.predict_proba(self.sc.transform(X))


class _MLPWrap:
    def __init__(self, K):
        self.K = K

    def fit(self, X, y):
        self.seen = np.unique(y)
        remap = {c: i for i, c in enumerate(self.seen)}
        self.m = TorchMLP().fit(X, np.array([remap[v] for v in y]), len(self.seen))
        return self

    def predict_proba(self, X):
        return self.m.predict_proba(X)


CONFIGS = ["nb", "pca+nb", "knn", "pca+knn", "lda+knn", "lr", "lr@0.005", "lr@0.5", "pca+lr", "ldaclf", "mlp"]


def metrics(y, p, K):
    pred = p.argmax(1)
    labels = list(range(K))
    present = [c for c in labels if (y == c).any()]
    return dict(acc=accuracy_score(y, pred), bal_acc=balanced_accuracy_score(y, pred),
                macro_f1=f1_score(y, pred, labels=present, average="macro", zero_division=0),
                n=len(y))


def cv_macro_f1(fp, X, y, g, K, folds=3):
    ps = np.zeros((len(y), K))
    for tr, te in GroupKFold(folds).split(X, y, g):
        ps[te] = fp(X[tr], y[tr], X[te])
    return metrics(y, ps, K)["macro_f1"]


def zero_shot_proba(backbone, group, X):
    if backbone == "concat":
        return None
    gname = "pattern" if group == "pattern_raw" else group
    T = np.load(FEAT / f"{backbone}__text__{gname}.npy")
    s = X @ T.T
    e = np.exp((s - s.max(1, keepdims=True)) * 100)
    return e / e.sum(1, keepdims=True)


def subsample(y, g, cap, rng):
    if not cap:
        return np.arange(len(y))
    idx = []
    for c in np.unique(y):
        ii = np.where(y == c)[0]
        idx += list(rng.choice(ii, min(cap, len(ii)), replace=False))
    return np.array(sorted(idx))


# --------------------------------------------------------------------- run
rows, preds_store = [], {}
t0 = time.time()
for group in a.groups:
    cls = classes_of(group)
    K = len(cls)
    for bb in a.backbones:
        try:
            if a.protocol == "train2val":
                Xtr, ytr, gtr, _ = load("train", group, bb)
                Xte, yte, gte, dte = load("val", group, bb)
            else:
                Xte, yte, gte, dte = load("val", group, bb)
                Xtr = ytr = gtr = None
        except Exception as e:  # noqa: BLE001
            print("skip", group, bb, e)
            continue
        # zero-shot (no training data used)
        p = zero_shot_proba(bb, group, Xte if bb != "concat" else None) if bb != "concat" else None
        if p is not None:
            m = metrics(yte, p, K)
            rows.append(dict(protocol=a.protocol, group=group, backbone=bb, clf="zero_shot", cv_macro_f1=np.nan, **m))
            preds_store[(group, bb, "zero_shot")] = (yte, p)
        for cfg in CONFIGS:
            fp = make(cfg, K, 64)
            if a.protocol == "train2val":
                cvf = cv_macro_f1(fp, Xtr, ytr, gtr, K)
                p = fp(Xtr, ytr, Xte)
            else:
                ps = np.zeros((len(yte), K))
                for tr, te in GroupKFold(5).split(Xte, yte, gte):
                    ps[te] = fp(Xte[tr], yte[tr], Xte[te])
                p, cvf = ps, np.nan
            m = metrics(yte, p, K)
            rows.append(dict(protocol=a.protocol, group=group, backbone=bb, clf=cfg, cv_macro_f1=cvf, **m))
            preds_store[(group, bb, cfg)] = (yte, p)
            print(f"[{time.time() - t0:5.0f}s] {group:12s} {bb:15s} {cfg:10s} cvF1={cvf:.3f} acc={m['acc']:.3f} "
                  f"balacc={m['bal_acc']:.3f} F1={m['macro_f1']:.3f} (n={m['n']})", flush=True)
        if bb != "concat":
            zs = preds_store.get((group, bb, "zero_shot"))
            for base in ["lr", "ldaclf"]:
                if zs is not None and (group, bb, base) in preds_store:
                    pf = np.log(preds_store[(group, bb, base)][1] + 1e-6) + 0.5 * np.log(zs[1] + 1e-6)
                    pf = np.exp(pf - pf.max(1, keepdims=True))
                    pf /= pf.sum(1, keepdims=True)
                    m = metrics(yte, pf, K)
                    rows.append(dict(protocol=a.protocol, group=group, backbone=bb, clf=base + "+zs", cv_macro_f1=np.nan, **m))
                    preds_store[(group, bb, base + "+zs")] = (yte, pf)
                    print(f"{group:12s} {bb:15s} {base}+zs acc={m['acc']:.3f} F1={m['macro_f1']:.3f}", flush=True)
        pd.DataFrame(rows).to_csv(RES / f"results_{a.protocol}.csv", index=False)

df = pd.DataFrame(rows)
df.to_csv(RES / f"results_{a.protocol}.csv", index=False)
import pickle
pickle.dump(preds_store, open(RES / f"preds_{a.protocol}.pkl", "wb"))
print("done", time.time() - t0)
