"""P05: plain-vs-design check on Fashionpedia val (textile-pattern attribute) - CPU only.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_fashionpedia.py [--n 120] [--out try_01]

Samples upper-body garments (shirt/blouse, top/t-shirt, sweater) with a clearly visible polygon, labelled
  plain  : attribute 'plain (pattern)' and no other textile-pattern attribute
  design : any other textile-pattern attribute (abstract, cartoon, letters/numbers, check, dot, floral,
           geometric, stripe, plant, ...)
Runs v0 (old extractor) and the new detector on the garment crop (oracle polygon mask) and reports
has-design rates, per-attribute recall, old FFT test firing rate and the fixed periodicity test.
Outputs: out/p05_design/<out>/fashionpedia/{results.csv, summary.json}
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(REPO / "product_ingestion"))
import cv_design_regions as cvd  # noqa: E402
import step_04_0_design_extraction as s4  # noqa: E402

cvd.USE_OCR = False
DATA = CV / "data/fashionpedia"
PATTERN = {317: "plain", 318: "abstract", 319: "cartoon", 320: "letters", 321: "camouflage", 322: "check", 323: "dot",
           324: "fair isle", 325: "floral", 326: "geometric", 327: "paisley", 328: "stripe", 329: "houndstooth",
           330: "herringbone", 331: "chevron", 332: "argyle", 339: "toile", 340: "plant"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120, help="samples per class")
    ap.add_argument("--out", default="try_01")
    args = ap.parse_args()
    d = json.loads((DATA / "instances_attributes_val2020.json").read_text(encoding="utf-8"))
    imgs = {i["id"]: i for i in d["images"]}
    rng = np.random.RandomState(0)
    cand = {"plain": [], "design": []}
    for a in d["annotations"]:
        if a["category_id"] not in (0, 1, 2) or a.get("iscrowd"):
            continue
        pats = [x for x in a["attribute_ids"] if x in PATTERN]
        if not pats or not a["segmentation"] or not isinstance(a["segmentation"], list):
            continue
        im = imgs[a["image_id"]]
        if a["area"] < 0.06 * im["width"] * im["height"]:
            continue
        if not (DATA / "test" / im["file_name"]).exists():
            continue
        cls = "plain" if pats == [317] else ("design" if 317 not in pats else None)
        if cls:
            cand[cls].append((a, pats))
    sample = []
    for cls in ("plain", "design"):
        idx = rng.permutation(len(cand[cls]))[: args.n]
        sample += [(cls, *cand[cls][i]) for i in idx]
    out_dir = CV / "out/p05_design" / args.out / "fashionpedia"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    t0 = time.time()
    for k, (cls, a, pats) in enumerate(sample):
        im = imgs[a["image_id"]]
        bgr = cv2.imread(str(DATA / "test" / im["file_name"]), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        h, w = bgr.shape[:2]
        m = np.zeros((h, w), np.uint8)
        for poly in a["segmentation"]:
            pts = np.array(poly, np.float32).reshape(-1, 2)
            if len(pts) >= 3:
                cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
        x, y, bw, bh = [int(v) for v in a["bbox"]]
        x0, y0, x1, y1 = max(0, x - 4), max(0, y - 4), min(w, x + bw + 4), min(h, y + bh + 4)
        rgb = cv2.cvtColor(bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
        mask = m[y0:y1, x0:x1] > 0
        if mask.sum() < 2000:
            continue
        rgba = np.dstack([rgb, mask.astype(np.uint8) * 255])
        # v0
        r0 = s4.DesignExtractor().extract(rgba)
        # old FFT value (peak/mean) to show the B4 problem
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        _, old_ratio = s4._has_repeating_pattern(cv2.bitwise_and(gray, gray, mask=mask.astype(np.uint8) * 255), mask.astype(np.uint8) * 255)
        # new
        P = cvd.prepare(rgb, mask)
        regs = cvd.detect_regions(rgb, mask, method="v2_combo", prep=P)
        per = P.info.get("periodicity", {})
        types = sorted({r["type"] for r in regs if r["type"] != "colour_block"})
        rows.append({"cls": cls, "attrs": "|".join(PATTERN[p] for p in pats), "image": im["file_name"], "ann": a["id"],
                     "v0_has": int(r0.has_design), "v0_type": r0.design_type, "old_fft_ratio": round(old_ratio, 1),
                     "periodic_new": int(bool(per.get("periodic"))), "per_ratio": round(per.get("ratio", 0), 1),
                     "new_has": int(bool(types)), "new_types": "|".join(types), "dev_cov": round(P.info.get("dev_cov", 0), 4)})
        if k % 20 == 0:
            print(k, len(sample), round(time.time() - t0), "s", flush=True)
    with open(out_dir / "results.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)
    def rate(sel, key):
        return float(np.mean([r[key] for r in sel])) if sel else float("nan")
    S = {"n_plain": sum(r["cls"] == "plain" for r in rows), "n_design": sum(r["cls"] == "design" for r in rows)}
    for key in ("v0_has", "new_has", "periodic_new"):
        S[f"{key}_on_plain"] = rate([r for r in rows if r["cls"] == "plain"], key)
        S[f"{key}_on_design"] = rate([r for r in rows if r["cls"] == "design"], key)
    S["old_fft_fires_gt8_on_plain"] = float(np.mean([r["old_fft_ratio"] > 8 for r in rows if r["cls"] == "plain"]))
    S["old_fft_fires_gt8_on_design"] = float(np.mean([r["old_fft_ratio"] > 8 for r in rows if r["cls"] == "design"]))
    S["old_fft_ratio_median_plain"] = float(np.median([r["old_fft_ratio"] for r in rows if r["cls"] == "plain"]))
    S["old_fft_ratio_median_design"] = float(np.median([r["old_fft_ratio"] for r in rows if r["cls"] == "design"]))
    per_attr = {}
    for r in rows:
        if r["cls"] != "design":
            continue
        for at in r["attrs"].split("|"):
            e = per_attr.setdefault(at, {"n": 0, "v0_has": 0, "new_has": 0, "new_stripes": 0, "new_text": 0})
            e["n"] += 1; e["v0_has"] += r["v0_has"]; e["new_has"] += r["new_has"]
            e["new_stripes"] += int("stripes" in r["new_types"]); e["new_text"] += int("text" in r["new_types"])
    S["per_attribute"] = per_attr
    S["seconds"] = round(time.time() - t0)
    (out_dir / "summary.json").write_text(json.dumps(S, indent=1), encoding="utf-8")
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main()
