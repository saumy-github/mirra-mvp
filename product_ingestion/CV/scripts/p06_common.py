"""Shared helpers for the P06 shape scripts."""
import sys, glob, json
from pathlib import Path
import cv2, numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "product_ingestion"))
import cv_shape  # noqa: E402
OUT = ROOT / "out" / "p06_shape"
REF = ROOT / "out" / "p00_baseline" / "reference"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]

def load_mirra(c):
    f = glob.glob(str(REPO / "product_ingestion" / "input" / c / "*"))[0]
    img = cv2.imread(f, cv2.IMREAD_COLOR)
    m = cv2.imread(str(REF / c / "garment_mask.png"), cv2.IMREAD_GRAYSCALE)
    if m.shape != img.shape[:2]:
        m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    return img, m

def viton_mask(i):
    return cv2.imread(str(OUT / "viton_masks" / f"v{i:03d}.png"), 0)

def labels():
    return json.loads((REF / "labels.json").read_text(encoding="utf-8"))["cloths"]
