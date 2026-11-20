"""P16: extract frozen image features (and text embeddings) once per backbone, cache as .npy.

Low memory: parquet files are read in row batches, only one batch of decoded images lives in RAM.
Run (from repo root), one backbone per call, e.g.:
  .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_extract_features.py siglip2
Outputs: out/p16_multiview/features/<backbone>_<dataset>.npy, meta_<dataset>.json, <backbone>_text.npz
Datasets: inshop_train, inshop_test, viton (cloth then person, 800 each, seed 0), mirra (5 photos).
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p16_common import (FEAT, PRES_PROMPTS, VIEW_PROMPTS, Backbone, inshop_meta, iter_inshop_images,
                        iter_viton_images, mirra_images)
from gpu_lock import gpu_lock


def run_iter(bb, it):
    feats = []
    for ims in it:
        feats.append(bb.encode_images(ims, bs=32))
        del ims
    gc.collect()
    return np.concatenate(feats).astype(np.float16)


def main(key):
    FEAT.mkdir(parents=True, exist_ok=True)
    mp = mirra_images()
    for split in ("train", "test"):
        p = FEAT / f"meta_inshop_{split}.json"
        if not p.exists():
            p.write_text(json.dumps(inshop_meta(split)))
    p = FEAT / "meta_mirra.json"
    if not p.exists():
        p.write_text(json.dumps([{"path": str(x), "cloth": x.parent.name} for x in mp]))

    with gpu_lock("p16"):
        t0 = time.time()
        bb = Backbone(key)
        print(key, "loaded", round(time.time() - t0, 1), "s", flush=True)
        txt = {}
        for grp, d in (("view", VIEW_PROMPTS), ("pres", PRES_PROMPTS)):
            for cls, prompts in d.items():
                txt[f"{grp}_{cls}"] = bb.encode_texts(prompts)
        np.savez(FEAT / f"{key}_text.npz", **txt)
        jobs = {
            "inshop_train": lambda: iter_inshop_images("train"),
            "inshop_test": lambda: iter_inshop_images("test"),
        }
        for name, mk in jobs.items():
            out = FEAT / f"{key}_{name}.npy"
            if out.exists():
                continue
            t0 = time.time()
            F = run_iter(bb, mk())
            np.save(out, F)
            print(key, name, F.shape, round(time.time() - t0, 1), "s", flush=True)
        out = FEAT / f"{key}_viton.npy"
        if not out.exists():
            t0 = time.time()
            Fc = run_iter(bb, iter_viton_images("cloth"))
            Fp = run_iter(bb, iter_viton_images("image"))
            np.save(out, np.concatenate([Fc, Fp]))
            print(key, "viton", Fc.shape, Fp.shape, round(time.time() - t0, 1), "s", flush=True)
        np.save(FEAT / f"{key}_mirra.npy", bb.encode_images([Image.open(p).convert("RGB") for p in mp]).astype(np.float16))
        bb.close()
        del bb
        gc.collect()
        print(key, "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
