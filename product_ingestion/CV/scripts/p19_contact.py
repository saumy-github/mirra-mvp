import cv2, json, numpy as np, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
lab = json.load(open(ROOT/"CV/out/p00_baseline/reference/labels.json"))["cloths"]
tiles=[]
for c,v in lab.items():
    im = cv2.imread(v["image"]); m = cv2.imread(v["garment_mask"],0)
    print(c, im.shape, m.shape, (m>127).mean().round(3))
    m = cv2.resize(m,(im.shape[1],im.shape[0]))
    ov = im.copy(); ov[m>127] = (0.5*ov[m>127]+0.5*np.array([0,255,0])).astype(np.uint8)
    s = 500/im.shape[0]
    tiles.append(np.hstack([cv2.resize(im,None,fx=s,fy=s), cv2.resize(ov,None,fx=s,fy=s)]))
W = max(t.shape[1] for t in tiles)
tiles=[cv2.copyMakeBorder(t,0,0,0,W-t.shape[1],cv2.BORDER_CONSTANT) for t in tiles]
cv2.imwrite(str(ROOT/"CV/out/p19_panel_maps/_contact.jpg"), np.vstack(tiles[:3]), [cv2.IMWRITE_JPEG_QUALITY,70])
cv2.imwrite(str(ROOT/"CV/out/p19_panel_maps/_contact2.jpg"), np.vstack(tiles[3:]), [cv2.IMWRITE_JPEG_QUALITY,70])
