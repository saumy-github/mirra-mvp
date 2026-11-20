"""P01 shared helpers: item lists (Mirra photos + public subsets), cache paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "product_ingestion"))

OUT = ROOT / "out" / "p01_segmentation"
CACHE = OUT / "cache"
SUBSETS = OUT / "subsets"
METHODS_DIR = OUT / "methods"
WEIGHTS = OUT / "weights"
INPUT = REPO / "product_ingestion" / "input"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
SETS = ["mirra", "viton_cloth", "viton_person", "fashionpedia"]


def items(sets=None, limit=None):
    """List of (set, id, image_path, gt_path|None)."""
    out = []
    for s in sets or SETS:
        if s == "mirra":
            for c in CLOTHS:
                p = sorted((INPUT / c).glob("*"))[0]
                out.append((s, c, p, None))
        else:
            idx = json.loads((SUBSETS / s / "index.json").read_text(encoding="utf-8"))
            if limit:
                idx = idx[:limit]
            for i in idx:
                img = next((SUBSETS / s / "images").glob(f"{i}.*"))
                out.append((s, i, img, SUBSETS / s / "gt" / f"{i}.png"))
    return out


def cache_path(s: str, i: str, model: str) -> Path:
    d = CACHE / s
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{i}__{model}.npz"


def save_cache(s, i, model, **arrays):
    np.savez_compressed(cache_path(s, i, model), **{k: np.asarray(v) for k, v in arrays.items()})


def load_cache(s, i, model):
    p = cache_path(s, i, model)
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def read_bgr(p: Path) -> np.ndarray:
    im = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if im is None:
        raise FileNotFoundError(p)
    return im
