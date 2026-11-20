"""P05: contact sheet (rows = methods, columns = photos) from the overlays of one try folder.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_contact_sheet.py <try_folder_name> [overlays|overlays_v0mask] [method1,method2,...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

CV = Path(__file__).resolve().parents[1]
try_name = sys.argv[1] if len(sys.argv) > 1 else "try_01"
sub = sys.argv[2] if len(sys.argv) > 2 else "overlays"
root = CV / "out/p05_design" / try_name / sub
methods = sys.argv[3].split(",") if len(sys.argv) > 3 else sorted(p.name for p in root.iterdir() if p.is_dir())
H = 300
rows = []
for m in methods:
    cells = []
    for c in ["c_001", "c_002", "c_003", "c_004", "c_005"]:
        im = cv2.imread(str(root / m / f"{c}.jpg"))
        s = H / im.shape[0]
        im = cv2.resize(im, (int(im.shape[1] * s), H), interpolation=cv2.INTER_AREA)
        canvas = np.full((H, 300, 3), 255, np.uint8)
        w = min(300, im.shape[1])
        canvas[:, :w] = im[:, :w]
        cells.append(canvas)
    rows.append(np.hstack(cells))
sheet = np.vstack(rows)
out = root.parent / f"contact_sheet_{sub}.jpg"
cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
print(out, sheet.shape)
