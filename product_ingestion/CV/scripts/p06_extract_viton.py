"""P06: stream VITON-HD test parquet files and save a fixed subset of cloth masks (every 4th row, 500 max)
plus the cloth photo of the first 24 selected rows. Streaming, batch 32, one image at a time."""
import sys, numpy as np, cv2, pyarrow.parquet as pq
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "product_ingestion/CV/data/vitonhd_test/data"
OUT = ROOT / "product_ingestion/CV/out/p06_shape"
STRIDE, MAXN, NPHOTO = 4, 500, 24
def main():
    k = 0; saved = 0
    for pf in sorted(DATA.glob("*.parquet")):
        f = pq.ParquetFile(pf)
        for b in f.iter_batches(batch_size=32, columns=["cloth", "cloth_mask"]):
            for r in b.to_pylist():
                if k % STRIDE == 0 and saved < MAXN:
                    m = cv2.imdecode(np.frombuffer(r["cloth_mask"]["bytes"], np.uint8), 0)
                    cv2.imwrite(str(OUT / "viton_masks" / f"v{saved:03d}.png"), m)
                    if saved < NPHOTO:
                        c = cv2.imdecode(np.frombuffer(r["cloth"]["bytes"], np.uint8), 1)
                        cv2.imwrite(str(OUT / "viton_photos" / f"v{saved:03d}.jpg"), c, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    saved += 1
                k += 1
    print("rows seen", k, "saved", saved)
main()
