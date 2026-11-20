"""P15a shared helpers: dev items (the P01 public subsets + 5 Mirra photos) and held-out items, with their caches."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from p01_common import *  # noqa: F401,F403,E402
import p01_common as p01  # noqa: E402

P15 = ROOT / "out" / "p15a_seg_autoselect"
HELD = P15 / "heldout"
CACHE15 = P15 / "cache"          # my own caches: <set>/<id>__<model>.npz  (dev: probs only; heldout: everything)
PUBSETS = ["viton_cloth", "viton_person", "fashionpedia"]


def items_all(split="dev", sets=None):
    """[(set, id, image_path, gt_path|None, split)]. split dev = P01 subsets (+ Mirra), held = held-out subsets."""
    out = []
    if split == "dev":
        for s, i, p, g in p01.items(sets):
            out.append((s, i, p, g, "dev"))
    else:
        for s in sets or PUBSETS:
            idx = json.loads((HELD / s / "index.json").read_text(encoding="utf-8"))
            for i in idx:
                img = next((HELD / s / "images").glob(f"{i}.*"))
                out.append((s, i, img, HELD / s / "gt" / f"{i}.png", "held"))
    return out


def cpath(split, s, i, model):
    if split == "dev" and model in ("segformer", "sam2b", "sam2c"):
        return p01.cache_path(s, i, model)
    d = CACHE15 / split / s
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{i}__{model}.npz"


def save(split, s, i, model, **arrays):
    np.savez_compressed(cpath(split, s, i, model), **{k: np.asarray(v) for k, v in arrays.items()})


def load(split, s, i, model):
    p = cpath(split, s, i, model)
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}
