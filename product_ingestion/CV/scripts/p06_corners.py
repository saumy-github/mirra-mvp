"""P06: compare corner / keypoint detectors. (1) 5 Mirra photos: gallery JPEG per photo + CSV (photo domain and mask-outline domain).
(2) 24 VITON-HD cloth photos (photo domain) and 500 VITON-HD masks (mask domain): CSV only.
Metrics against the landmarks of cv_shape.analyze_shape (shoulder, armpit, neck, cuff, hem points), tolerance 3% of garment height:
  recall = landmarks with a detected point within tol / landmarks ; precision@N = detected points (top N) within tol of a landmark ;
  on_outline = detected points within 2% of H of the mask contour ; n_all = points before the top-N cap.
Run from repo root: .venv/Scripts/python.exe product_ingestion/CV/scripts/p06_corners.py"""
import csv, numpy as np, cv2
from p06_common import *
from scipy.ndimage import distance_transform_edt
WH = 480; N = 150; NSMALL = 40
NAMES = cv_shape.DETECTORS + ["contour_curvature", "convexity_defects"]

def prep(img, mask):
    s = WH / mask.shape[0] if mask.shape[0] != WH else 1.0
    # garment bbox height may be less than image height; use image height for working scale
    im = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC) if img is not None else None
    m = cv2.resize(mask, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    return im, m, s

def run_all(gray, m, domain, c_w):
    """Return dict name -> (pts (k,2), n_all). gray: image for detectors (photo or smoothed mask)."""
    out = {}
    region = cv2.dilate(m, np.ones((7, 7), np.uint8)) if domain == "photo" else None
    for d in cv_shape.DETECTORS:
        p, st = cv_shape.detect_keypoints(gray, d, region, n=N)
        pa, _ = cv_shape.detect_keypoints(gray, d, region, n=100000)
        out[d] = (p, len(pa))
    p, _ = cv_shape.contour_curvature_points(c_w, n=40)
    out["contour_curvature"] = (p, len(p))
    defs = cv_shape.convexity_defects(c_w)
    dp = np.array([c_w[d["far"]] for d in sorted(defs, key=lambda d: -d["depth"])[:40] if d["depth"] > 0.01 * WH]).reshape(-1, 2)
    out["convexity_defects"] = (dp, len(dp))
    return out

def metrics(pts_by, lm_w, m, name, domain, rows, extra):
    H = WH; tol = 0.03 * H
    dist_out = distance_transform_edt(1 - cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)))
    L = np.array(list(lm_w.values()))
    for d, (p, nall) in pts_by.items():
        if len(p) and len(L):
            D = np.sqrt(((p[:, None, :] - L[None, :, :]) ** 2).sum(2))
            rec = float((D.min(0) <= tol).mean()); prec = float((D.min(1) <= tol).mean())
            ps = p[:NSMALL]; precs = float((D[:len(ps)].min(1) <= tol).mean())
            xi = np.clip(p[:, 0].round().astype(int), 0, m.shape[1] - 1); yi = np.clip(p[:, 1].round().astype(int), 0, m.shape[0] - 1)
            onout = float((dist_out[yi, xi] <= 0.02 * H).mean())
        else:
            rec = prec = precs = onout = 0.0
        rows.append(dict(item=name, domain=domain, detector=d, n_all=nall, n_kept=len(p), n_landmarks=len(L),
                         recall_at_3pct=round(rec, 3), precision_all_kept=round(prec, 3), precision_top40=round(precs, 3),
                         on_outline_frac=round(onout, 3), **extra))

def lm_work(res, s):
    return {k: np.array(v) * s for k, v in res["landmarks"].items()}

def tile(im, pts, lm_w, title, th=300):
    t = im.copy()
    for x, y in pts:
        cv2.circle(t, (int(round(x)), int(round(y))), 3, (0, 0, 255), -1, cv2.LINE_AA)
    for x, y in lm_w.values():
        cv2.circle(t, (int(round(x)), int(round(y))), 6, (0, 200, 0), 1, cv2.LINE_AA)
    s = th / t.shape[0]
    t = cv2.resize(t, (int(t.shape[1] * s), th), interpolation=cv2.INTER_AREA)
    cv2.putText(t, title, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(t, title, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return t

def one(img, mask, name, domain_list, rows, gallery=None):
    res = cv_shape.analyze_shape(mask, name)
    if not res["ok"]:
        return
    im, m, s = prep(img, mask)
    # outline in work coords
    wm, c, sc, bb = cv_shape.clean_outline(m)
    lm = lm_work(res, s)
    pts_all = {}
    for domain in domain_list:
        if domain == "photo":
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        else:
            g = cv2.GaussianBlur(m * 255, (0, 0), 1.2)
        # clean_outline works at its own scale (garment bbox height WORK_H); convert contour to image-work coords
        c_img = c / sc
        pts = run_all(g, m, domain, c_img)
        metrics(pts, lm, m, name, domain, rows, {"sleeve_class": res["sleeve"]["class"]})
        pts_all[domain] = (pts, g)
    if gallery is not None:
        tiles = []
        base = im if im is not None else cv2.cvtColor(m * 255, cv2.COLOR_GRAY2BGR)
        mbase = cv2.cvtColor(m * 255, cv2.COLOR_GRAY2BGR)
        edges = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(base, cv2.COLOR_BGR2GRAY), (0, 0), 1.2), 60, 150)
        for dom in domain_list:
            pts, g = pts_all[dom]
            bg = base if dom == "photo" else mbase
            for d in NAMES:
                if dom == "mask" and d in ("contour_curvature", "convexity_defects"):
                    continue
                tiles.append(tile(bg, pts[d][0], lm, f"{dom}:{d} n={pts[d][1]}"))
        # Hough lines tile
        hl = cv_shape.hough_outline_lines(m)
        ht = mbase.copy()
        for x1, y1, x2, y2 in hl["lines"]:
            cv2.line(ht, (x1, y1), (x2, y2), (0, 0, 255), 2)
        if hl["hem"]:
            cv2.line(ht, tuple(hl["hem"]["line"][:2]), tuple(hl["hem"]["line"][2:]), (255, 128, 0), 3)
        tiles.append(tile(ht, [], lm, f"hough lines n={hl['n_lines']}"))
        tiles.append(tile(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), [], lm, "Canny (photo) ref"))
        wmax = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, 0, 0, wmax - t.shape[1], cv2.BORDER_CONSTANT, value=(40, 40, 40)) for t in tiles]
        cols = 6
        while len(tiles) % cols: tiles.append(np.full_like(tiles[0], 40))
        sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        cv2.imwrite(str(OUT / "corners" / f"{name}_corners.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])

def write(rows, fn):
    with open(OUT / "corners" / fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def main():
    rows = []
    for c in CLOTHS:
        img, m = load_mirra(c)
        one(img, (m > 127).astype(np.uint8), c, ["photo", "mask"], rows, gallery=True)
    write(rows, "mirra_corner_metrics.csv"); print("mirra rows", len(rows))
    rows = []
    for i in range(24):
        ph = cv2.imread(str(OUT / "viton_photos" / f"v{i:03d}.jpg")); m = (viton_mask(i) > 127).astype(np.uint8)
        one(ph, m, f"v{i:03d}", ["photo"], rows)
    write(rows, "viton_photo_corner_metrics.csv"); print("viton photo rows", len(rows))
    rows = []
    for i in range(500):
        m = (viton_mask(i) > 127).astype(np.uint8)
        one(None, m, f"v{i:03d}", ["mask"], rows)
    write(rows, "viton_mask_corner_metrics.csv"); print("viton mask rows", len(rows))
main()
