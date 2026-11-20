"""P16: do the cheap geometric cues help?  (Haar face detector, garment area, blur)

Uses cached cues (p16_cpu_cues.py) and cached features.  Reports
  * face detection rate per view label on the In-shop test split,
  * view classifier (logistic regression) with and without the face / area / frame-contact cues appended to
    the embedding, on validation (held-out train items) and test.
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_geometry.py <backbone>
Outputs: out/p16_multiview/results_geometry_<backbone>.csv, face_rate_by_view.csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p16_common import FEAT, OUT, VIEW_CLASSES, loadf
from p16_train import load_meta, metrics


def geo(z):
    return np.stack([z["face"].astype(np.float32), np.minimum(z["face_area"] * 20, 1.0), z["area"], z["touches"],
                     np.log10(z["blur"] + 1) / 3], 1).astype(np.float32)


def main(bb):
    mtr, mte = load_meta("inshop_train"), load_meta("inshop_test")
    ztr, zte = np.load(FEAT / "cues_train.npz"), np.load(FEAT / "cues_test.npz")
    fine_te = np.array([m["fine"] for m in mte])
    rate = pd.DataFrame({"fine": fine_te, "face": zte["face"]}).groupby("fine")["face"].agg(["mean", "count"]).reset_index()
    rate.to_csv(OUT / "face_rate_by_view.csv", index=False)
    print(rate)
    Xtr, Xte = loadf(FEAT / f"{bb}_inshop_train.npy"), loadf(FEAT / f"{bb}_inshop_test.npy")
    ytr = np.array([m["view"] for m in mtr])
    yte = np.array([m["view"] for m in mte])
    itr = np.array([m["item"] for m in mtr])
    tr_i, va_i = next(GroupShuffleSplit(1, test_size=0.15, random_state=0).split(Xtr, ytr, itr))
    Gtr, Gte = geo(ztr), geo(zte)
    rows = []
    for name, f in (("embedding only", lambda X, G: X), ("embedding + geometric cues", lambda X, G: np.hstack([X, 3 * G])),
                    ("geometric cues only", lambda X, G: G)):
        m = LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced").fit(f(Xtr[tr_i], Gtr[tr_i]), ytr[tr_i])
        mv_ = metrics(ytr[va_i], m.predict(f(Xtr[va_i], Gtr[va_i])), VIEW_CLASSES)
        m2 = LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced").fit(f(Xtr, Gtr), ytr)
        mt = metrics(yte, m2.predict(f(Xte, Gte)), VIEW_CLASSES)
        rows.append({"backbone": bb, "features": name, "val_acc": mv_["acc"], "val_macro_f1": mv_["macro_f1"],
                     **{f"test_{k}": v for k, v in mt.items()}})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"results_geometry_{bb}.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main(sys.argv[1])
