"""P15b shared helpers: photos, mask sets (oracle | v1 | v1_all), raw-proposal cache, overlay drawing."""
from __future__ import annotations
import json, pickle, sys
from pathlib import Path
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "product_ingestion"))
OUT = CV / "out/p15b_design"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
MASKSETS = ["oracle", "v1", "v1_all"]
COL = {"text": (255, 60, 60), "graphic": (60, 120, 255), "logo": (255, 0, 255), "stripes": (255, 160, 0),
       "colour_block": (0, 200, 0), "pattern": (0, 200, 200)}


def load_inputs(maskset: str):
    labels = json.loads((CV / "out/p00_baseline/reference/labels.json").read_text(encoding="utf-8"))["cloths"]
    data = {}
    for c in CLOTHS:
        e = labels[c]
        rgb = cv2.cvtColor(cv2.imread(e["image"], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        mp = e["garment_mask"] if maskset == "oracle" else str(OUT / "masks" / maskset / c / "mask.png")
        m = cv2.imread(mp, cv2.IMREAD_UNCHANGED)
        m = m[..., -1] if m.ndim == 3 else m
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST) > 127
        data[c] = {"rgb": rgb, "mask": m}
    return data


def cache_path(maskset: str, cloth: str) -> Path:
    return OUT / "cache" / maskset / f"{cloth}.pkl"


def load_cache(maskset: str, cloth: str) -> dict:
    p = cache_path(maskset, cloth)
    if p.exists():
        return pickle.loads(p.read_bytes())
    return {}


def draw_overlay(rgb, mask, regions, title=""):
    img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, (0, 255, 255), max(1, round(max(img.shape[:2]) / 400)))
    t = max(1, round(max(img.shape[:2]) / 350))
    fs = max(0.35, max(img.shape[:2]) / 1100)
    for r in regions:
        x0, y0, x1, y1 = [int(round(v)) for v in r["box"]]
        col = COL.get(r["type"], (255, 255, 255))[::-1]
        cv2.rectangle(img, (x0, y0), (x1, y1), col, t)
        cv2.putText(img, r["type"], (x0 + 2, max(10, y0 + int(14 * fs * 2))), cv2.FONT_HERSHEY_SIMPLEX, fs, col, max(1, t - 1), cv2.LINE_AA)
    if title:
        cv2.putText(img, title, (4, int(18 * fs * 1.5)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), t + 2, cv2.LINE_AA)
        cv2.putText(img, title, (4, int(18 * fs * 1.5)), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), t, cv2.LINE_AA)
    return img
