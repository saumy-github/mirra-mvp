"""P16: end-to-end test of multi_view.assign_views on real image files.

1. Builds multi-photo sets from In-shop TEST items (>= 2 photos, at most 60 sets, items not seen in the
   training split first), copies the photos (shuffled random names) to out/p16_multiview/testsets/<set>/ and
   about half of the sets get one photo of a different item added (the foreign photo).
2. Runs assign_views on every set, scores it, writes <set>/view_assignment.json and sets_end_to_end.csv.
3. Runs the 5 Mirra photos one by one and as one mixed folder (they are 5 different garments), writes
   mirra/*.json and draws example grids.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_eval_files.py [model_dir]
"""
from __future__ import annotations

import gc
import io
import json
import os
import sys
import uuid
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p16_common import FEAT, INSHOP, MIRRA_TRUTH, OUT, mirra_images
from p16_sets import build_sets, score_assignment, summarise, truth_for
from gpu_lock import gpu_lock
import multi_view as mv

N_SETS = 60
TS = OUT / "testsets"


def make_sets():
    import pyarrow.parquet as pq
    meta = json.loads((FEAT / "meta_inshop_test.json").read_text())
    tr_items = {m["item"] for m in json.loads((FEAT / "meta_inshop_train.json").read_text())}
    sets = build_sets(meta, range(len(meta)), seed=0)
    for s in sets:
        s["unseen"] = s["item"] not in tr_items
    sets = sorted(sets, key=lambda s: (not s["unseen"], s["set_id"]))[:N_SETS]
    rng = np.random.RandomState(0)
    need = {i for s in sets for i in s["indices"]}
    names = {}
    TS.mkdir(parents=True, exist_ok=True)
    for s in sets:
        (TS / s["set_id"]).mkdir(exist_ok=True)
        for i in s["indices"]:
            names[(s["set_id"], i)] = "".join(rng.choice(list("abcdefghijklmnopqrstuvwxyz0123456789"), 10)) + ".jpg"
    pf = pq.ParquetFile(INSHOP / "test-00000-of-00001.parquet")
    pos = 0
    for b in pf.iter_batches(batch_size=128, columns=["image"]):
        vals = b.column(0).to_pylist()
        for k, v in enumerate(vals):
            i = pos + k
            if i in need:
                for s in sets:
                    if i in s["indices"]:
                        (TS / s["set_id"] / names[(s["set_id"], i)]).write_bytes(v["bytes"])
        pos += len(vals)
    gt = {}
    for s in sets:
        gt[s["set_id"]] = {"item": s["item"], "unseen": s["unseen"], "foreign": names.get((s["set_id"], s["foreign"])) if s["foreign"] is not None else None,
                           "photos": {names[(s["set_id"], i)]: {"index": i, "fine": meta[i]["fine"], "view": meta[i]["view"]} for i in s["indices"]}}
        (TS / s["set_id"] / "truth.json").write_text(json.dumps(gt[s["set_id"]], indent=1))
    return meta, sets, names


def grid(paths_titles, out, ncols=6, size=150):
    n = len(paths_titles)
    nrows = (n + ncols - 1) // ncols
    fig, axs = plt.subplots(nrows, ncols, figsize=(ncols * 1.9, nrows * 2.4))
    axs = np.atleast_2d(axs)
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (p, t) in zip(axs.ravel(), paths_titles):
        ax.imshow(Image.open(p).convert("RGB"))
        ax.set_title(t, fontsize=6)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def main(model_dir=None):
    meta, sets, names = make_sets()
    rows, examples = [], []
    with gpu_lock("p16"):
        for s in sets:
            d = TS / s["set_id"]
            files = sorted(p for p in d.glob("*.jpg"))
            va = mv.assign_views([str(p) for p in files], model_dir=model_dir)
            mv.write_view_assignment_json(va, d / "view_assignment.json")
            rev = {names[(s["set_id"], i)]: i for i in s["indices"]}
            idx = lambda p: rev[Path(p).name] if p else None
            r = score_assignment(meta, s, idx(va.front), idx(va.back), [idx(p) for p in va.outliers])
            r.update({"set_id": s["set_id"], "n_photos": len(files), "unseen": s["unseen"], "method": va.method})
            rows.append(r)
            if len(examples) < 4 * 8:
                for ph in va.photos:
                    i = rev[Path(ph.path).name]
                    t = f"{s['set_id']} true:{meta[i]['fine']}{'*FOREIGN' if i == s['foreign'] else ''}\npred:{ph.role} {ph.presentation[:3]}"
                    examples.append((ph.path, t))
        # Mirra
        mdir = OUT / "mirra"
        mdir.mkdir(exist_ok=True)
        mp = mirra_images()
        mrows = []
        for p in mp:
            va = mv.assign_views([str(p)], model_dir=model_dir)
            mv.write_view_assignment_json(va, mdir / f"{p.parent.name}_single.json")
            va5 = None
            ph = va.photos[0]
            mrows.append({"cloth": p.parent.name, "mode": "single", "view": ph.view, "role": ph.role,
                          "pres": ph.presentation, "face": ph.face_found, "view_probs": {k: round(v, 3) for k, v in ph.view_probs.items()},
                          "truth_view": MIRRA_TRUTH[p.parent.name]["view"], "truth_pres": MIRRA_TRUTH[p.parent.name]["pres"]})
        va5 = mv.assign_views([str(p) for p in mp], model_dir=model_dir)
        mv.write_view_assignment_json(va5, mdir / "mixed_5_photos.json")
        for ph in va5.photos:
            c = Path(ph.path).parent.name
            mrows.append({"cloth": c, "mode": "mixed", "view": ph.view, "role": ph.role, "pres": ph.presentation,
                          "face": ph.face_found, "same_garment_score": round(ph.same_garment_score, 3),
                          "view_probs": {k: round(v, 3) for k, v in ph.view_probs.items()},
                          "truth_view": MIRRA_TRUTH[c]["view"], "truth_pres": MIRRA_TRUTH[c]["pres"]})
        (mdir / "mirra_results.json").write_text(json.dumps(mrows, indent=1))
        grid([(ph.path, f"{Path(ph.path).parent.name} {ph.role}\n{ph.view} {ph.presentation} same={ph.same_garment_score:.2f}") for ph in va5.photos],
             OUT / "mirra_mixed_grid.png", ncols=5)
        for k in list(mv._CACHE):
            if k[0] == "emb":
                mv._CACHE[k].close()
                del mv._CACHE[k]
        gc.collect()
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "sets_end_to_end.csv", index=False)
    res = {"all": summarise(rows), "unseen_items_only": summarise([r for r in rows if r["unseen"]]),
           "n_sets": len(rows), "n_unseen_sets": int(sum(r["unseen"] for r in rows)),
           "n_with_foreign": int(sum(r["has_foreign"] for r in rows)),
           "n_with_back": int(sum(r["has_back"] for r in rows))}
    (OUT / "sets_end_to_end_summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    for k in range(0, min(len(examples), 32), 32):
        pass
    grid(examples[:48], OUT / "examples_testsets.png", ncols=8)


if __name__ == "__main__":
    main(*sys.argv[1:])
