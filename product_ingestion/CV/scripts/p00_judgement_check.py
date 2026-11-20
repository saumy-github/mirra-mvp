"""P00 meta-evaluation, step 2: does the outline score agree with judgement by eye?

make:  for each Mirra photo, draw every method's mask outline on the photo in a random
       order labelled A, B, C ... (method names hidden) -> out/p00_baseline/judgement/<cloth>_sheet.jpg
       and a hidden key -> judgement/key.json
rank:  the judge writes judgement/ranks.json: {"c_001": [["A", "C"], "D", "B"], ...} (best first).
       A nested list is a group of outlines the judge cannot tell apart (a tie); ties are scored
       with Kendall's tau-b, which allows ties.
score: Kendall's tau-b between the judge's order and the order given by each candidate metric
       (outline_score, IoU, boundary F @1%, HD95) -> results/judgement_agreement.csv

Usage:
  python p00_judgement_check.py make --methods <name>=<pred_root> <name>=<pred_root> ...
  python p00_judgement_check.py score
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import kendalltau

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import CLOTHS, RESULTS, load_mask, load_reference, mask_metrics  # noqa: E402

OUT = HERE.parent / "out" / "p00_baseline" / "judgement"


def make(methods: dict[str, Path]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    refs = load_reference()
    rnd = random.Random(7)
    key = {}
    for c in CLOTHS:
        ref = refs[c]
        w, h = ref["size_wh"]
        rgb = cv2.cvtColor(cv2.imread(ref["image"]), cv2.COLOR_BGR2RGB)
        names = [n for n, root in methods.items() if (root / c / "mask.png").exists()]
        rnd.shuffle(names)
        letters = [chr(ord("A") + i) for i in range(len(names))]
        key[c] = dict(zip(letters, names))
        tiles = []
        for L, n in zip(letters, names):
            m = load_mask(methods[n] / c / "mask.png", (h, w)).astype(np.uint8)
            t = rgb.copy()
            dim = (t * 0.55).astype(np.uint8)
            t = np.where(m[..., None] > 0, t, dim)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(t, cnts, -1, (0, 255, 0), max(2, w // 300))
            scale = 360 / max(h, w)
            t = cv2.resize(t, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            cv2.putText(t, L, (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
            tiles.append(t)
        if not tiles:
            continue
        hmax = max(t.shape[0] for t in tiles)
        tiles = [np.vstack([t, np.zeros((hmax - t.shape[0], t.shape[1], 3), np.uint8)]) for t in tiles]
        rows = [np.hstack(tiles[i:i + 5] + [np.zeros_like(tiles[0])] * (5 - len(tiles[i:i + 5])))
                for i in range(0, len(tiles), 5)]
        cv2.imwrite(str(OUT / f"{c}_sheet.jpg"), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))
    (OUT / "key.json").write_text(json.dumps({"methods": {k: str(v) for k, v in methods.items()}, "key": key}, indent=1))
    print("sheets in", OUT)


def score() -> None:
    key_doc = json.loads((OUT / "key.json").read_text())
    methods = {k: Path(v) for k, v in key_doc["methods"].items()}
    ranks = json.loads((OUT / "ranks.json").read_text())
    refs = load_reference()
    rows = []
    for c, order in ranks.items():
        if c.startswith("_"):
            continue
        ref = refs[c]
        w, h = ref["size_wh"]
        g = load_mask(Path(ref["garment_mask"]), (h, w))
        names, judge = [], []          # judge: 0 = best; equal numbers = a tie
        for rank, item in enumerate(order):
            for L in (item if isinstance(item, list) else [item]):
                names.append(key_doc["key"][c][L])
                judge.append(rank)
        mets = {n: mask_metrics(load_mask(methods[n] / c / "mask.png", (h, w)), g) for n in names}
        cand = {
            "outline_score": [-(0.5 * mets[n]["iou"] + 0.5 * mets[n]["boundary_f@1.0%"]) for n in names],
            "iou": [-mets[n]["iou"] for n in names],
            "boundary_f@1.0%": [-mets[n]["boundary_f@1.0%"] for n in names],
            "hd95_pct_diag": [mets[n]["hd95_pct_diag"] for n in names],
        }
        for metric, vals in cand.items():
            tau, _ = kendalltau(judge, vals)
            rows.append({"cloth": c, "metric": metric, "kendall_tau": round(float(tau), 3), "n_methods": len(names),
                         "n_groups": len(order)})
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "judgement_agreement.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["cloth", "metric", "kendall_tau", "n_methods", "n_groups"])
        wr.writeheader()
        wr.writerows(rows)
    import pandas as pd
    print(pd.DataFrame(rows).pivot_table(index="metric", columns="cloth", values="kendall_tau").assign(
        mean=lambda d: d.mean(axis=1)).round(3).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make")
    mk.add_argument("--methods", nargs="+", required=True)
    sub.add_parser("score")
    a = ap.parse_args()
    if a.cmd == "make":
        make({m.split("=", 1)[0]: Path(m.split("=", 1)[1]) for m in a.methods})
    else:
        score()
