import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
import cv_panel_maps as pm
L = s001_layouts(); d = load_mirra(); tiles = []
for c in ("c_003", "c_005", "c_001", "c_004"):
    v = d[c]
    res = pm.build_panel_maps(front_rgb=v["rgb"], back_rgb=None, front_mask=v["mask"], layouts=L, on_person=v["label"]["presentation"] == "on_person")
    pv = res["views"]["front"]; im = pv.rgb.copy()
    for s, col in (("L", (255, 0, 0)), ("R", (0, 0, 255))):
        r = pv.reg["sleeve_" + s]; im[r] = (0.5 * im[r] + 0.5 * np.array(col)).astype(np.uint8)
        cc = pv.sleeve_corners(s)
        if cc:
            pts = np.array([cc[k] for k in ("S","A","Ci","Co","apex") if k in cc]).astype(np.int32)
            cv2.polylines(im, [pts.reshape(-1, 1, 2)], True, (255, 255, 0), max(2, im.shape[0] // 300))
            for k, p in cc.items():
                cv2.putText(im, k, tuple(int(x) for x in p), cv2.FONT_HERSHEY_SIMPLEX, max(0.5, im.shape[0] / 1000), (255, 255, 255), 2)
    s = 450 / im.shape[0]; tiles.append(cv2.resize(im, None, fx=s, fy=s))
cv2.imwrite(str(OUT / "_dbg_sleeve.jpg"), cv2.cvtColor(np.hstack(tiles), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 75])
