import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
import cv_panel_maps as pm
L = s001_layouts(); d = load_mirra()
tiles = []
for c, v in d.items():
    onp = v["label"]["presentation"] == "on_person"
    isf = v["label"]["view"] == "front"
    res = pm.build_panel_maps(front_rgb=v["rgb"] if isf else None, back_rgb=None if isf else v["rgb"],
                              front_mask=v["mask"] if isf else None, back_mask=None if isf else v["mask"], layouts=L, on_person=onp)
    pv = list(res["views"].values())[0]
    im = pv.rgb.copy()
    for k, col in (("torso", (0, 255, 0)), ("sleeve_L", (255, 0, 0)), ("sleeve_R", (0, 0, 255))):
        r = pv.reg[k]; im[r] = (0.55 * im[r] + 0.45 * np.array(col)).astype(np.uint8)
    for kind in ("front_panel", "back_panel"):
        w = res["warps"][kind]
        if w["view"] is pv and "src" in w["res"] and kind == ("front_panel" if isf else "back_panel"):
            for p, kd in zip(w["res"]["src"], w["res"]["kinds"]):
                cv2.circle(im, tuple(int(x) for x in p), max(2, im.shape[0] // 150), (255, 255, 0), -1)
    for s in "LR":
        cc = pv.sleeve_corners(s)
        if cc:
            for k, p in cc.items():
                cv2.circle(im, tuple(int(x) for x in p), max(3, im.shape[0] // 120), (255, 0, 255), -1)
    s = 420 / im.shape[0]
    tiles.append(cv2.resize(im, None, fx=s, fy=s))
W = sum(t.shape[1] for t in tiles)
cv2.imwrite(str(OUT / "_dbg_regions.jpg"), cv2.cvtColor(np.hstack(tiles), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 75])
