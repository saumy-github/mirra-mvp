"""P15a: build a HELD-OUT public test set (new images, never used to design the rules).

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_build_heldout.py [--n 150] [--n_fp 100]

Same construction as p01_build_subsets.py (viton_cloth / viton_person / fashionpedia) but seed 1 and with every image of the P01
subsets excluded. Writes out/p15a_seg_autoselect/heldout/<set>/{images,gt}/ and index.json. VITON images are stored as JPEG
(quality 97) to save disk space; the VITON-HD originals are JPEG already. Read-only on data/.
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
sys.path.insert(0, str(HERE))
import p01_build_subsets as b1  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "out" / "p15a_seg_autoselect" / "heldout"
P01 = ROOT / "out" / "p01_segmentation" / "subsets"


def used(s):
    return set(json.loads((P01 / s / "index.json").read_text(encoding="utf-8")))


def build_viton(n, seed=1):
    files = sorted((b1.DATA / "vitonhd_test" / "data").glob("*.parquet"))
    counts = [pq.ParquetFile(f).metadata.num_rows for f in files]
    total = sum(counts)
    ex = {int(x) for x in used("viton_cloth")}
    pool = np.array([i for i in range(total) if i not in ex])
    rng = np.random.RandomState(seed)
    chosen = set(rng.choice(pool, n, replace=False).tolist())
    for s in ("viton_cloth", "viton_person"):
        (OUT / s / "images").mkdir(parents=True, exist_ok=True)
        (OUT / s / "gt").mkdir(parents=True, exist_ok=True)
    idx = []
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
                    cl.save(OUT / "viton_cloth" / "images" / f"{name}.jpg", quality=97)
                    cv2.imwrite(str(OUT / "viton_cloth" / "gt" / f"{name}.png"), cm.astype(np.uint8) * 255)
                    im = Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB")
                    par = np.array(Image.open(io.BytesIO(r["parse"]["bytes"])))[..., 0]
                    im.save(OUT / "viton_person" / "images" / f"{name}.jpg", quality=97)
                    cv2.imwrite(str(OUT / "viton_person" / "gt" / f"{name}.png"), (np.isin(par, (5, 21, 22))).astype(np.uint8) * 255)
                    idx.append(name)
                pos += 1
        base += cnt
    for s in ("viton_cloth", "viton_person"):
        (OUT / s / "index.json").write_text(json.dumps(sorted(idx)), encoding="utf-8")
    return len(idx)


def build_fashionpedia(n, seed=1):
    d = json.loads((b1.DATA / "fashionpedia" / "instances_attributes_val2020.json").read_text(encoding="utf-8"))
    imgs = {i["id"]: i for i in d["images"]}
    ex = used("fashionpedia")
    by_img: dict[int, list] = {}
    for a in d["annotations"]:
        if a["category_id"] in b1.UPPER_FP and not a.get("iscrowd", 0) and isinstance(a["segmentation"], list):
            by_img.setdefault(a["image_id"], []).append(a)
    (OUT / "fashionpedia" / "images").mkdir(parents=True, exist_ok=True)
    (OUT / "fashionpedia" / "gt").mkdir(parents=True, exist_ok=True)
    cands = []
    for iid, anns in by_img.items():
        info = imgs[iid]
        if Path(info["file_name"]).stem in ex:
            continue
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
    idx = []
    for o in rng.permutation(len(cands)):
        if len(idx) >= n:
            break
        iid, k = cands[o]
        info = imgs[iid]
        src = b1.DATA / "fashionpedia" / "test" / info["file_name"]
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
    print("fashionpedia kept / eligible (excluding P01 subset):", build_fashionpedia(a.n_fp))
