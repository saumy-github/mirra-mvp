"""P16: presentation classifier = mean of trained logistic regression and zero-shot prompt probabilities.
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_pres_ensemble.py
Output: out/p16_multiview/results_presentation_ensemble.csv"""
import os, sys, json
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import f1_score, accuracy_score
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p16_common import FEAT, MIRRA_TRUTH, OUT, loadf
from p16_train import load_meta
from p16_train_aux import pres_data

rows = []
mir = load_meta("mirra"); mt = np.array([MIRRA_TRUTH[m["cloth"]]["pres"] for m in mir])
for bb in ["siglip2", "marqo"]:
    Fv, n, Fins, Fte = pres_data(bb)
    Xm = loadf(FEAT / f"{bb}_mirra.npy"); txt = np.load(FEAT / f"{bb}_text.npz")
    y = np.array(["flat"] * n + ["person"] * n)
    grp = np.concatenate([np.arange(n), np.arange(n)])
    tr, te = next(GroupShuffleSplit(1, test_size=0.25, random_state=0).split(Fv, y, grp))
    T = np.stack([txt[f"pres_{c}"].mean(0) for c in ["flat", "mannequin", "person"]]); T /= np.linalg.norm(T, axis=1, keepdims=True)
    def zs(F):
        z = 100 * F @ T.T; z -= z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
        return np.stack([p[:, 0], p[:, 1] + p[:, 2]], 1)   # flat, person(+mannequin)
    lr = LogisticRegression(C=2, max_iter=2000, class_weight="balanced").fit(np.concatenate([Fv[tr], Fins]), np.concatenate([y[tr], ["person"] * len(Fins)]))
    order = list(lr.classes_); idx = [order.index("flat"), order.index("person")]
    for w in (0.0, 0.5, 1.0):
        def pred(F):
            p = (1 - w) * lr.predict_proba(F)[:, idx] + w * zs(F)
            return np.array(["flat", "person"])[p.argmax(1)]
        pv, pi, pm = pred(Fv[te]), pred(Fte), pred(Xm)
        rows.append({"backbone": bb, "zero_shot_weight": w, "viton_test_acc": accuracy_score(y[te], pv), "viton_test_macro_f1": f1_score(y[te], pv, average="macro"),
                     "inshop_test_person_recall": float(np.mean(pi == "person")), "mirra_acc": float(np.mean(pm == mt)), "mirra_pred": " ".join(pm)})
df = pd.DataFrame(rows); df.to_csv(OUT / "results_presentation_ensemble.csv", index=False); print(df.to_string())
