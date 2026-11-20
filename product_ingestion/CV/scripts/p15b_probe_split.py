"""P15b: probe glyph-height structure of the merged OCR box (c_001) to design the split rule."""
import sys
from p15b_common import *  # noqa
import cv_design_regions as cvd
ms, c = sys.argv[1], sys.argv[2]
d = load_inputs(ms)[c]
P = cvd.prepare(d["rgb"], d["mask"])
k = load_cache(ms, c)
for r in k["ocr"]:
    x0, y0, x1, y1 = [int(v) for v in r["box"]]
    ink = ((P.dev[y0:y1, x0:x1] > 12) & P.inner[y0:y1, x0:x1]).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(ink)
    print("box", r["box"], "scale", P.scale)
    for i in range(1, n):
        s = st[i]
        if s[4] >= 2:
            print("  comp x", s[0] + x0, "y", s[1] + y0, "w", s[2], "h", s[3], "area", s[4])
