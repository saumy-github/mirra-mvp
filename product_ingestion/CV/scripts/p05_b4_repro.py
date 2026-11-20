"""P05: reproduce bug B4 on synthetic shirts and show the fix.
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_b4_repro.py
Cases: plain grey tee with two soft folds; polka-dot tee; striped tee. Reports old (peak/mean FFT ratio, v0 decision)
and new (periodicity test, v3-free CPU detector 'v2_combo' types)."""
import json, sys
from pathlib import Path
import cv2, numpy as np
CV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CV.parents[0]))
import cv_design_regions as cvd
import step_04_0_design_extraction as s4
cvd.USE_OCR = False

def tee(kind, h=400, w=400):
    img = np.full((h, w, 3), 150, np.float32)
    yy, xx = np.mgrid[:h, :w]
    if kind in ("plain_folds", "dots", "stripes"):
        # soft folds (shading only)
        img *= (1 + 0.12 * np.exp(-((xx - 140) / 25.0) ** 2) * -1 + 0.10 * np.exp(-((xx - 270 + 0.3 * yy) / 20.0) ** 2) * -1)[..., None]
    if kind == "dots":
        for y in range(15, h, 30):
            for x in range(15 + 15 * ((y // 30) % 2), w, 30):
                cv2.circle(img, (x, y), 6, (40, 60, 160), -1)
    if kind == "stripes":
        for y in range(0, h, 24):
            img[y:y + 10] = (40, 60, 160)
    img += np.random.RandomState(0).normal(0, 2, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    cv2.rectangle(mask, (30, 20), (w - 30, h - 20), 1, -1)
    img[mask == 0] = 0   # v0 paints the background black
    return img, mask > 0

out = {}
for kind in ("plain_folds", "dots", "stripes"):
    rgb, mask = tee(kind)
    rgba = np.dstack([rgb, mask.astype(np.uint8) * 255])
    r0 = s4.extract_design(rgba, method="v0")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, ratio = s4._has_repeating_pattern(gray, mask.astype(np.uint8) * 255)
    P = cvd.prepare(rgb, mask)
    per = cvd.periodicity(P)
    regs = cvd.detect_regions(rgb, mask, method="v2_combo")
    out[kind] = {"v0_has_design": r0.has_design, "v0_type": r0.design_type, "v0_coverage": round(r0.design_coverage_percent, 1),
                 "old_fft_ratio": round(float(ratio), 1), "new_periodic": per["periodic"], "new_ratio": round(per["ratio"], 1),
                 "new_n_pairs": per["n_pairs"], "new_types": sorted({r["type"] for r in regs})}
print(json.dumps(out, indent=1))
d = CV / "out/p05_design/b4_repro"; d.mkdir(parents=True, exist_ok=True)
(d / "b4_repro.json").write_text(json.dumps(out, indent=1))
