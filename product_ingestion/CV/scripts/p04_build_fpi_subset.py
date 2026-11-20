"""P04: build a fixed random subset of Fashion Product Images (small) tops, memory-safe.

Pass 1 reads only (id, articleType, baseColour) to pick the subset with a fixed seed.
Pass 2 streams the parquet files in batches and writes the chosen images as PNG.
Output: out/p04_colour/fpi_subset/{images/<id>.png, labels.csv}
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_build_fpi_subset.py [--n 800]
"""
from __future__ import annotations
import argparse, glob, io
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fashion_product_images_small" / "data"
OUT = ROOT / "out" / "p04_colour" / "fpi_subset"
TYPES = {"Tshirts", "Tops", "Shirts", "Sweatshirts"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=800); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    files = sorted(glob.glob(str(DATA / "*.parquet")))
    metas = []
    for f in files:
        t = pq.read_table(f, columns=["id", "articleType", "baseColour"]).to_pandas()
        metas.append(t)
    meta = pd.concat(metas, ignore_index=True)
    sel = meta[meta.articleType.isin(TYPES) & meta.baseColour.notna()]
    print("eligible", len(sel), "of", len(meta))
    sub = sel.sample(n=min(a.n, len(sel)), random_state=a.seed).sort_values("id")
    ids = set(sub.id.tolist())
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    got = 0
    for f in files:
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=128, columns=["id", "image"]):
            d = b.to_pydict()
            for i, im in zip(d["id"], d["image"]):
                if i in ids:
                    Image.open(io.BytesIO(im["bytes"])).convert("RGB").save(OUT / "images" / f"{i}.png"); got += 1
    sub.to_csv(OUT / "labels.csv", index=False)
    print("saved", got, "images; size sample:", Image.open(next((OUT / "images").glob("*.png"))).size)
    print(sub.articleType.value_counts().to_string()); print(sub.baseColour.value_counts().to_string())

if __name__ == "__main__":
    main()
