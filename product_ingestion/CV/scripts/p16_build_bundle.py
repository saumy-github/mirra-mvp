"""P16: fit the final models on all training data and save the bundle used by product_ingestion/multi_view.py.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_build_bundle.py <backbone> <pre> <clf>
Writes product_ingestion/models/view_classifier/{view_clf.joblib, metrics.json}  (README.md written by hand).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p16_common import FEAT, OUT, REPO, VIEW_CLASSES, loadf
from p16_train import build, fit_model, load_meta
from p16_train_aux import pair_data, pres_data
import p16_train_aux  # noqa: F401

warnings.filterwarnings("ignore")
MODEL_DIR = REPO / "product_ingestion" / "models" / "view_classifier"


def main(bb, pre, clf, pres_pre="none", pres_clf="lr"):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    mtr = load_meta("inshop_train")
    Xtr = loadf(FEAT / f"{bb}_inshop_train.npy")
    ytr = np.array([m["view"] for m in mtr])
    view = build(pre, clf, 4, Xtr.shape[1])
    fit_model(view, Xtr, ytr, clf_name=clf)
    # presentation: all VITON rows (cloth = flat, image = person) + 800 In-shop train photos as person
    Fv, n, Fins, _ = pres_data(bb)
    X = np.concatenate([Fv, Fins])
    y = np.array(["flat"] * n + ["person"] * (n + len(Fins)))
    pres = build(pres_pre, pres_clf, 2, X.shape[1])
    fit_model(pres, X, y, clf_name=pres_clf)
    # same-garment pair classifier
    ctr = np.load(FEAT / "cues_train.npz")["colour"]
    Xp, yp = pair_data("train", bb, ctr, mtr, np.random.RandomState(0), cap_pos=6000)
    same = LogisticRegression(C=10, max_iter=2000, class_weight="balanced").fit(Xp, yp)
    txt = np.load(FEAT / f"{bb}_text.npz")
    zs = {}
    for c in VIEW_CLASSES + ["other"]:
        v = txt[f"view_{c}"].mean(0)
        zs[c] = (v / np.linalg.norm(v)).astype(np.float32)
    zsp = {}
    for c in ("flat", "mannequin", "person"):
        v = txt[f"pres_{c}"].mean(0)
        zsp[c] = (v / np.linalg.norm(v)).astype(np.float32)
    pfile = OUT / f"tuned_params_{bb}.json"
    params = json.loads(pfile.read_text()) if pfile.exists() else {"back_threshold": 0.5, "usability_weight": 0.3, "other_threshold": 0.6}
    bundle = {"name": f"{bb}+{pre}+{clf}", "backbone": bb, "view_model": view, "pres_model": pres, "same_model": same,
              "zs_text": zs, "zs_pres": zsp, "pres_zs_weight": 0.5, "params": params, "view_classes": VIEW_CLASSES}
    joblib.dump(bundle, MODEL_DIR / "view_clf.joblib", compress=3)
    best = json.loads((OUT / "best.json").read_text()) if (OUT / "best.json").exists() else {}
    (MODEL_DIR / "metrics.json").write_text(json.dumps({"backbone": bb, "pre": pre, "clf": clf, "params": params,
                                                        "selection": best}, indent=1))
    print("saved", MODEL_DIR, (MODEL_DIR / "view_clf.joblib").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
