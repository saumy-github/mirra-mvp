"""P07 step 5: run cv_attributes.predict_attributes on the 5 Mirra garments (raw photo and RGBA cut-out) and draw a figure.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_mirra.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from p07_common import OUT, REPO
from gpu_lock import gpu_lock
from product_ingestion import cv_attributes as cva

TRUTH = {"c_001": "navy; text 'BOSTON'; elbow sleeves; crew neck", "c_002": "pink plain; short sleeves; back view",
         "c_003": "white/teal colour block, stripe band, script text; short sleeves",
         "c_004": "brown, geometric graphic + text; short sleeves", "c_005": "red; text 'CALIFORNIA'; short sleeves"}
res = {}
fig, axs = plt.subplots(5, 2, figsize=(11, 22))
with gpu_lock("p07"):
    for r, cid in enumerate(sorted(TRUTH)):
        photo = sorted((REPO / "product_ingestion" / "input" / cid).glob("*"))[0]
        cut = REPO / "product_ingestion" / "output" / cid / "s_001" / "001" / "image_info" / "base_garment.png"
        res[cid] = {}
        for c, (name, path) in enumerate([("photo", photo), ("cutout", cut)]):
            out = cva.predict_attributes(path, groups=("pattern", "sleeve", "sleeve3", "neckline"))
            res[cid][name] = {g: {"label": v["label"], "confidence": round(v["confidence"], 3),
                                  "top3": sorted(v["probs"].items(), key=lambda kv: -kv[1])[:3]} for g, v in out.items()}
            im = Image.open(path)
            if im.mode == "RGBA":
                bg = Image.new("RGB", im.size, (200, 200, 200))
                bg.paste(im, mask=im.split()[3])
                im = bg
            axs[r, c].imshow(im.convert("RGB"))
            axs[r, c].axis("off")
            txt = "\n".join(f"{g}: {v['label']} ({v['confidence']:.2f})" for g, v in res[cid][name].items())
            axs[r, c].set_title(f"{cid} {name}\n{txt}", fontsize=9, loc="left")
        axs[r, 0].text(0, -0.02, "approx. truth: " + TRUTH[cid], transform=axs[r, 0].transAxes, fontsize=8, va="top")
    cva.release_models()
fig.tight_layout()
fig.savefig(OUT / "figs" / "mirra_predictions.png", dpi=90)
json.dump(res, open(OUT / "mirra_predictions.json", "w"), indent=1)
for cid, v in res.items():
    for n, d in v.items():
        print(cid, n, {g: (x["label"], x["confidence"]) for g, x in d.items()})
