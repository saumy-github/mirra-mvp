"""P16: compute the cheap CPU cues (blur, garment area, frame contact, Haar face, colour descriptor) for the
In-shop train and test photos, streamed in batches, cached in out/p16_multiview/features/cues_<split>.npz.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_cpu_cues.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p16_common import FEAT, iter_inshop_images
from multi_view import image_cues


def main():
    for split in ("test", "train"):
        out = FEAT / f"cues_{split}.npz"
        if out.exists():
            continue
        t0 = time.time()
        recs = []
        for ims in iter_inshop_images(split, 128):
            for im in ims:
                recs.append(image_cues(np.asarray(im)))
        np.savez(out,
                 blur=np.array([r["blur"] for r in recs]), area=np.array([r["garment_area"] for r in recs]),
                 touches=np.array([r["touches_frame"] for r in recs]), face=np.array([r["face_found"] for r in recs]),
                 face_area=np.array([r["face_area"] for r in recs]), colour=np.stack([r["colour"] for r in recs]))
        print(split, len(recs), round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
