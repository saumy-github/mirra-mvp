"""P06: landmark overlays for the 5 Mirra photos and 24 VITON-HD examples. Saves JPEGs + JSON.
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p06_overlays.py"""
import json, cv2, numpy as np
from p06_common import *
def small(im, h=520):
    s = h / im.shape[0]; return cv2.resize(im, (int(im.shape[1]*s), h), interpolation=cv2.INTER_AREA)
def main():
    res_all = {}
    tiles = []
    for c in CLOTHS:
        img, m = load_mirra(c)
        r = cv_shape.analyze_shape(m, c)
        res_all[c] = r
        ov = cv_shape.draw_overlay(img, r)
        cv2.imwrite(str(OUT / "overlays" / f"mirra_{c}.jpg"), small(ov, 800), [cv2.IMWRITE_JPEG_QUALITY, 90])
        tiles.append(small(ov))
    cv2.imwrite(str(OUT / "overlays" / "mirra_all.jpg"), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
    json.dump(res_all, open(OUT / "stats" / "mirra_shape.json", "w"), indent=1)
    rows = []
    vt = []
    for i in range(24):
        m = viton_mask(i); ph = cv2.imread(str(OUT / "viton_photos" / f"v{i:03d}.jpg"))
        r = cv_shape.analyze_shape(m, f"v{i:03d}")
        ov = cv_shape.draw_overlay(ph, r)
        cv2.imwrite(str(OUT / "overlays" / f"viton_v{i:03d}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
        vt.append(cv2.resize(ov, (288, 384)))
    for k in range(0, 24, 6):
        cv2.imwrite(str(OUT / "overlays" / f"viton_sheet_{k//6}.jpg"), np.hstack(vt[k:k+6]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print({c: (r.get("ok"), r.get("error"), r.get("sleeve", {}).get("class"), r.get("ratios", {}).get("hem_to_chest")) for c, r in res_all.items()})
main()
