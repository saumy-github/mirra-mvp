"""P16: confusion matrix + per-class report of the chosen view model (siglip2 + logistic regression) on the In-shop test split,
overall, on test photos of items unseen in training, and for the fine labels (front vs full)."""
import os, sys, json
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import classification_report
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p16_common import FEAT, OUT, VIEW_CLASSES, loadf
from p16_train import build, fit_model, load_meta, plot_cm
mtr, mte = load_meta("inshop_train"), load_meta("inshop_test")
Xtr, Xte = loadf(FEAT / "siglip2_inshop_train.npy"), loadf(FEAT / "siglip2_inshop_test.npy")
ytr = np.array([m["view"] for m in mtr]); yte = np.array([m["view"] for m in mte]); fine = np.array([m["fine"] for m in mte])
m = build("none", "lr", 4, Xtr.shape[1]); fit_model(m, Xtr, ytr, clf_name="lr"); p = m.predict(Xte)
plot_cm(yte, p, VIEW_CLASSES, "siglip2 + logistic regression (In-shop test, n=1179)", OUT / "cm_view_chosen_siglip2_lr.png")
tr_items = {x["item"] for x in mtr}; un = np.array([x["item"] not in tr_items for x in mte])
plot_cm(yte[un], p[un], VIEW_CLASSES, f"same model, test photos of unseen items (n={un.sum()})", OUT / "cm_view_chosen_siglip2_lr_unseen.png")
rep = classification_report(yte, p, labels=VIEW_CLASSES, output_dict=True, zero_division=0)
pd.DataFrame(rep).T.to_csv(OUT / "report_view_chosen.csv")
print(classification_report(yte, p, labels=VIEW_CLASSES, zero_division=0))
print(pd.crosstab(fine, p))
# 3-class view (front/back/side only): test photos labelled additional dropped
k = yte != "additional"
print("3-class (additional photos removed from the test): acc", float((p[k] == yte[k]).mean()), "n", int(k.sum()))
print(pd.crosstab(yte[k], p[k]))
