"""P17: build the small YOLO-seg dataset (one class "garment") on the CPU.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p17_build_dataset.py

Sources (all exact masks; P01's test rows/images are EXCLUDED, fixed seed 0):
  VITON-HD test parquet  product photo (cloth + cloth_mask>127) and person photo (parse in {5,21,22})
  Fashionpedia val       largest upper-body garment polygon (same eligibility rule as P01), street photos
Images are resized to <= 640 px (JPEG q92); labels are normalised polygons (YOLO-seg txt).
Writes out/p17_yolo_seg/dataset/{images,labels}/{train,val}/ , data.yaml and split_report.json.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import cv2
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
P01 = ROOT / "out" / "p01_segmentation" / "subsets"
OUT = ROOT / "out" / "p17_yolo_seg" / "dataset"
MAXSIDE = 640
UPPER_FP = (0, 1, 2, 3, 4, 5, 9)
N_CLOTH, N_PERSON, N_FP_TRAIN = 500, 1000, 700
N_VAL_ROWS, N_FP_VAL = 70, 40


def polys_from_mask(m: np.ndarray, min_frac=0.015):
    """List of normalised polygons (flat lists) for external contours >= min_frac of the image."""
    h, w = m.shape
    m8 = (m > 0).astype(np.uint8)
    m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        if cv2.contourArea(c) < min_frac * h * w:
            continue
        eps = 0.0015 * cv2.arcLength(c, True)
        a = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(np.float64)
        if len(a) < 3:
            continue
        a[:, 0] /= w
        a[:, 1] /= h
        out.append(np.clip(a, 0, 1).reshape(-1).tolist())
    return out


def save(split, name, img_rgb: np.ndarray, mask: np.ndarray):
    h, w = mask.shape
    sc = min(1.0, MAXSIDE / max(h, w))
    if sc < 1:
        sz = (int(round(w * sc)), int(round(h * sc)))
        img_rgb = cv2.resize(img_rgb, sz, interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask.astype(np.uint8), sz, interpolation=cv2.INTER_NEAREST)
    polys = polys_from_mask(mask)
    if not polys:
        return False
    (OUT / "images" / split).mkdir(parents=True, exist_ok=True)
    (OUT / "labels" / split).mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "images" / split / f"{name}.jpg"), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    (OUT / "labels" / split / f"{name}.txt").write_text(
        "\n".join("0 " + " ".join(f"{v:.5f}" for v in p) for p in polys), encoding="utf-8")
    return True


def main():
    rng = np.random.RandomState(0)
    report = {}
    test_rows = {int(i) for i in json.loads((P01 / "viton_cloth" / "index.json").read_text())}
    assert test_rows == {int(i) for i in json.loads((P01 / "viton_person" / "index.json").read_text())}
    files = sorted((DATA / "vitonhd_test" / "data").glob("*.parquet"))
    counts = [pq.ParquetFile(f).metadata.num_rows for f in files]
    total = sum(counts)
    pool = np.array([i for i in range(total) if i not in test_rows])
    pool = rng.permutation(pool)
    val_rows = set(pool[:N_VAL_ROWS].tolist())
    train_rows = pool[N_VAL_ROWS:]
    cloth_rows = set(train_rows[:N_CLOTH].tolist())
    # person rows: a different random subset of the train rows (some overlap is fine)
    person_rows = set(rng.permutation(train_rows)[:N_PERSON].tolist())
    report["viton_rows_total"] = total
    report["viton_test_rows_excluded"] = len(test_rows)
    n = {"train_cloth": 0, "train_person": 0, "val_cloth": 0, "val_person": 0}
    base = 0
    for f, cnt in zip(files, counts):
        pf = pq.ParquetFile(f)
        pos = base
        for batch in pf.iter_batches(batch_size=8, columns=["cloth", "cloth_mask", "image", "parse"]):
            for r in batch.to_pylist():
                if pos in test_rows:
                    pos += 1
                    continue
                isval = pos in val_rows
                split = "val" if isval else "train"
                if isval or pos in cloth_rows:
                    cl = np.array(Image.open(io.BytesIO(r["cloth"]["bytes"])).convert("RGB"))
                    cm = np.array(Image.open(io.BytesIO(r["cloth_mask"]["bytes"])).convert("L")) > 127
                    if save(split, f"vc_{pos:05d}", cl, cm):
                        n[f"{split}_cloth"] += 1
                if isval or pos in person_rows:
                    im = np.array(Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB"))
                    par = np.array(Image.open(io.BytesIO(r["parse"]["bytes"])))[..., 0]
                    if save(split, f"vp_{pos:05d}", im, np.isin(par, (5, 21, 22))):
                        n[f"{split}_person"] += 1
                pos += 1
        base += cnt
    report.update(n)

    # ---- Fashionpedia ----
    test_fp = set(json.loads((P01 / "fashionpedia" / "index.json").read_text()))
    d = json.loads((DATA / "fashionpedia" / "instances_attributes_val2020.json").read_text(encoding="utf-8"))
    imgs = {i["id"]: i for i in d["images"]}
    by_img: dict[int, list] = {}
    for a in d["annotations"]:
        if a["category_id"] in UPPER_FP and not a.get("iscrowd", 0) and isinstance(a["segmentation"], list):
            by_img.setdefault(a["image_id"], []).append(a)
    cands = []
    for iid, anns in sorted(by_img.items()):
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
        um = np.logical_or.reduce(masks)
        union = int(um.sum())
        if areas[k] >= 0.08 * h * w and areas[k] >= 0.7 * union:
            cands.append((iid, masks[k]))          # same rule as P01's test set
        elif union >= 0.03 * h * w:
            cands.append((iid, um.astype(np.uint8)))  # relaxed (training only): union of upper-body garments
    n_elig = len(cands)
    cands = [(i, m) for i, m in cands if Path(imgs[i]["file_name"]).stem not in test_fp]
    order = rng.permutation(len(cands))
    fp_val = order[:N_FP_VAL]
    fp_train = order[N_FP_VAL:N_FP_VAL + N_FP_TRAIN]
    nfp = {"train": 0, "val": 0}
    for split, sel in (("val", fp_val), ("train", fp_train)):
        for o in sel:
            iid, m = cands[o]
            name = Path(imgs[iid]["file_name"]).stem
            src = DATA / "fashionpedia" / "test" / imgs[iid]["file_name"]
            if not src.exists():
                continue
            im = np.array(Image.open(src).convert("RGB"))
            if save(split, f"fp_{name}", im, m):
                nfp[split] += 1
    report["fp_eligible_strict_or_relaxed"] = n_elig
    report["fp_eligible_after_excluding_test"] = len(cands)
    report["fp_train"], report["fp_val"] = nfp["train"], nfp["val"]
    report["train_total"] = len(list((OUT / "images" / "train").glob("*.jpg")))
    report["val_total"] = len(list((OUT / "images" / "val").glob("*.jpg")))
    (OUT / "data.yaml").write_text(
        f"path: {OUT.as_posix()}\ntrain: images/train\nval: images/val\nnames:\n  0: garment\n", encoding="utf-8")
    (OUT.parent / "split_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
