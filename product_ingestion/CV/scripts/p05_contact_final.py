"""P05: final contact sheets (rows = methods, columns = the 5 photos) from the try_02 / try_03 overlays.
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_contact_final.py
Writes out/p05_design/contact_sheet_oracle_masks.jpg and contact_sheet_v0_masks.jpg."""
from pathlib import Path
import cv2, numpy as np
CV = Path(__file__).resolve().parents[1]; R = CV / "out/p05_design"
H = 280
def cell(p):
    im = cv2.imread(str(p))
    if im is None:
        return np.full((H, 300, 3), 200, np.uint8)
    s = H / im.shape[0]; im = cv2.resize(im, (int(im.shape[1] * s), H), interpolation=cv2.INTER_AREA)
    cv = np.full((H, 300, 3), 255, np.uint8); w = min(300, im.shape[1]); cv[:, :w] = im[:, :w]; return cv
def sheet(rows, out):
    r = [np.hstack([cell(R / t / sub / m / f"{c}.jpg") for c in ["c_001", "c_002", "c_003", "c_004", "c_005"]]) for t, sub, m in rows]
    cv2.imwrite(str(R / out), np.vstack(r), [cv2.IMWRITE_JPEG_QUALITY, 78]); print(out, len(r))
sheet([("try_02", "overlays", "v0"), ("try_02", "overlays", "b_classical"), ("try_02", "overlays", "c_colour"), ("try_02", "overlays", "d_texture"),
       ("try_02", "overlays", "d_stripes"), ("try_03", "overlays", "e_text"), ("try_02", "overlays", "f_sam2"), ("try_03", "overlays", "g_gdino"),
       ("try_02", "overlays", "h_combo"), ("try_03", "overlays", "v2_combo"), ("try_03", "overlays", "v3_combo")], "contact_sheet_oracle_masks.jpg")
sheet([("try_02", "overlays_v0mask", "v0"), ("try_02", "overlays_v0mask", "b_classical"), ("try_02", "overlays_v0mask", "c_colour"),
       ("try_03", "overlays_v0mask", "e_text"), ("try_03b", "overlays_v0mask", "f_sam2"), ("try_03", "overlays_v0mask", "g_gdino"),
       ("try_03", "overlays_v0mask", "v2_combo"), ("try_03", "overlays_v0mask", "v3_combo")], "contact_sheet_v0_masks.jpg")
