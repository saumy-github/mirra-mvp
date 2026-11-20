import sys, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
import cv_panel_maps as pm
L = s001_layouts(); d = load_mirra()
tiles = []
for c, v in d.items():
    t = time.time()
    onp = v["label"]["presentation"] == "on_person"
    kw = dict(front_rgb=v["rgb"], back_rgb=None, front_mask=v["mask"]) if v["label"]["view"] == "front" else dict(front_rgb=None, back_rgb=v["rgb"], back_mask=v["mask"])
    if "back_rgb" in kw and kw["back_rgb"] is not None: kw["back_mask"] = v["mask"]
    res = pm.build_panel_maps(layouts=L, on_person=onp, **kw)
    print(c, round(time.time() - t, 1), "s", res["info"]["px_per_cm"], res["info"]["views"])
    row = []
    for k in ("front_panel", "back_panel", "sleeve_left", "sleeve_right"):
        a = res["panels"][k]["rgba"]; m = res["panels"][k]["meta"]
        print("  ", k, a.shape, m["photo_coverage_of_panel"], m["filled_fraction"], m["assumptions"][:2])
        im = cv2.resize(a, (180, int(180 * a.shape[0] / a.shape[1])))
        bg = np.full(im.shape[:3], 128, np.uint8); al = im[..., 3:4] / 255.
        im = (im[..., :3] * al + bg[..., :3] * (1 - al)).astype(np.uint8)
        row.append(cv2.copyMakeBorder(im, 0, 300 - im.shape[0], 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    ph = cv2.resize(v["rgb"], (int(300 * v["rgb"].shape[1] / v["rgb"].shape[0]), 300))
    tiles.append(np.hstack([ph] + row))
W = max(t.shape[1] for t in tiles)
tiles = [cv2.copyMakeBorder(t, 0, 0, 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
cv2.imwrite(str(OUT / "_try1.jpg"), cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 75])
