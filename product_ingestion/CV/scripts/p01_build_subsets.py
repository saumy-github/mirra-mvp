"""P01: build the fixed public-dataset subsets used to score the segmentation methods.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_build_subsets.py [--n 150]

Writes out/p01_segmentation/subsets/<set>/images/<id>.(png|jpg), gt/<id>.png and index.json for
  viton_cloth   VITON-HD test product photo (flat top on white), GT = cloth_mask > 127
  viton_person  VITON-HD test person photo, GT = parse labels {5 torso, 21, 22 sleeves}  (verified by eye)
  fashionpedia  Fashionpedia val street photo; GT = the largest upper-body garment instance
                (shirt/blouse, top/t-shirt, sweater, cardigan, jacket, vest, coat; polygons only).
                Only photos where that instance is >= 8 % of the image and >= 70 % of the union of all
                upper-body garments are kept, so "the garment" is unambiguous.
Fixed seed 0. VITON-HD is read in row batches (low memory).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
OUT = ROOT / "out" / "p01_segmentation" / "subsets"
UPPER_FP = (0, 1, 2, 3, 4, 5, 9)   # Fashionpedia upper-body categories


def build_viton(n: int, seed: int = 0):
    files = sorted((DATA / "vitonhd_test" / "data").glob("*.parquet"))
    counts = [pq.ParquetFile(f).metadata.num_rows for f in files]
    total = sum(counts)
    rng = np.random.RandomState(seed)
    chosen = set(rng.choice(total, n, replace=False).tolist())
    for s in ("viton_cloth", "viton_person"):
        (OUT / s / "images").mkdir(parents=True, exist_ok=True)
        (OUT / s / "gt").mkdir(parents=True, exist_ok=True)
    idx_c, idx_p = [], []
    base = 0
    for f, cnt in zip(files, counts):
        pf = pq.ParquetFile(f)
        pos = base
        for batch in pf.iter_batches(batch_size=16, columns=["cloth", "cloth_mask", "image", "parse"]):
            for r in batch.to_pylist():
                if pos in chosen:
                    name = f"{pos:05d}"
                    cl = Image.open(io.BytesIO(r["cloth"]["bytes"])).convert("RGB")
                    cm = np.array(Image.open(io.BytesIO(r["cloth_mask"]["bytes"])).convert("L")) > 127
                    cl.save(OUT / "viton_cloth" / "images" / f"{name}.png")
                    cv2.imwrite(str(OUT / "viton_cloth" / "gt" / f"{name}.png"), cm.astype(np.uint8) * 255)
                    idx_c.append(name)
                    im = Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB")
                    par = np.array(Image.open(io.BytesIO(r["parse"]["bytes"])))[..., 0]
                    gt = np.isin(par, (5, 21, 22))
                    im.save(OUT / "viton_person" / "images" / f"{name}.png")
                    cv2.imwrite(str(OUT / "viton_person" / "gt" / f"{name}.png"), gt.astype(np.uint8) * 255)
                    idx_p.append(name)
                pos += 1
        base += cnt
    for s, idx in (("viton_cloth", idx_c), ("viton_person", idx_p)):
        (OUT / s / "index.json").write_text(json.dumps(sorted(idx)), encoding="utf-8")
    return len(idx_c)


def build_fashionpedia(n: int, seed: int = 0):
    d = json.loads((DATA / "fashionpedia" / "instances_attributes_val2020.json").read_text(encoding="utf-8"))
    imgs = {i["id"]: i for i in d["images"]}
    by_img: dict[int, list] = {}
    for a in d["annotations"]:
        if a["category_id"] in UPPER_FP and not a.get("iscrowd", 0) and isinstance(a["segmentation"], list):
            by_img.setdefault(a["image_id"], []).append(a)
    (OUT / "fashionpedia" / "images").mkdir(parents=True, exist_ok=True)
    (OUT / "fashionpedia" / "gt").mkdir(parents=True, exist_ok=True)
    cands = []
    for iid, anns in by_img.items():
        info = imgs[iid]
        h, w = info["height"], info["width"]
        masks = []
        for a in anns:
            m = np.zeros((h, w), np.uint8)
            for poly in a["segmentation"]:
                if len(poly) >= 6:
                    cv2.fillPoly(m, [np.array(poly, np.float32).reshape(-1, 2).round().astype(np.int32)], 1)
            masks.append(m)
        areas = [int(m.sum()) for m in masks]
        k = int(np.argmax(areas))
        union = int(np.logical_or.reduce(masks).sum())
        if areas[k] >= 0.08 * h * w and areas[k] >= 0.7 * union:
            cands.append((iid, k))
    rng = np.random.RandomState(seed)
    order = rng.permutation(len(cands))[:n]
    idx = []
    for o in order:
        iid, k = cands[o]
        info = imgs[iid]
        src = DATA / "fashionpedia" / "test" / info["file_name"]
        if not src.exists():
            continue
        h, w = info["height"], info["width"]
        m = np.zeros((h, w), np.uint8)
        for poly in by_img[iid][k]["segmentation"]:
            if len(poly) >= 6:
                cv2.fillPoly(m, [np.array(poly, np.float32).reshape(-1, 2).round().astype(np.int32)], 255)
        name = Path(info["file_name"]).stem
        Image.open(src).convert("RGB").save(OUT / "fashionpedia" / "images" / f"{name}.jpg", quality=95)
        cv2.imwrite(str(OUT / "fashionpedia" / "gt" / f"{name}.png"), m)
        idx.append(name)
    (OUT / "fashionpedia" / "index.json").write_text(json.dumps(sorted(idx)), encoding="utf-8")
    return len(idx), len(cands)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--n_fp", type=int, default=100)
    a = ap.parse_args()
    print("viton rows:", build_viton(a.n))
    print("fashionpedia kept / eligible:", build_fashionpedia(a.n_fp))
