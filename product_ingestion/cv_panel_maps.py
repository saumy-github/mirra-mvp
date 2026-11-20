"""P19: per-panel pixel maps (garment photo -> one image per pattern panel).

Every texture pixel is a fixed patch of fabric (1 / px_per_cm cm).  The photo is split into
torso and sleeve regions from the garment outline; each region is warped onto its panel with
a thin-plate spline fitted to landmark correspondences (neck, shoulder, armpit, hem points and
points sampled by arc length along the armhole), holes are filled from neighbouring fabric, and
a side-car dict per panel records size in px and mm, the panel polygon in texture pixels and the
assumptions made.

Conventions
-----------
* Panel coordinates are cm, y up (curve_segment.PieceLayout).  Texture image: x right, y down,
  origin = top-left of the panel bounding box, i.e. panel (xmin, ymax).
* front/back panel: panel x < 0 = image-left.  sleeve piece: front half is the -x half for
  sleeve_left and the +x half for sleeve_right (from clo_vto seams.py: arm-L-front is sewn to the
  sleeve's "right_underarm" curve).  A photo sleeve on the image-right fills the -x half of its
  sleeve piece, one on the image-left fills the +x half (orientation preserving).
  Front photo: image-right sleeve -> sleeve_left (wearer's left).  Back photo: image-left sleeve
  -> sleeve_left.
* Only numpy / OpenCV / SciPy are used (no network, no GPU).
"""
from __future__ import annotations

import math
from typing import Optional

import cv2
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator

ARM_SLOPE = 0.125          # armhole leans inward 3 cm per 24 cm (s_001 front panel)
PPC_MIN, PPC_MAX = 5.0, 20.0

try:                       # P06 landmarks (optional)
    from cv_shape import garment_landmarks as _p06_landmarks
except Exception:          # pragma: no cover
    try:
        from .cv_shape import garment_landmarks as _p06_landmarks
    except Exception:
        _p06_landmarks = None


# ----------------------------------------------------------------------------- panel geometry
def _edge_map(layout):
    return {e.name: e for e in layout.edges}


def _arc_points(edge, k: int):
    """k interior points of an edge, equally spaced by arc length (excluding the end points)."""
    pts = np.array(edge.points(24), float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    out = []
    for i in range(1, k + 1):
        t = cum[-1] * i / (k + 1)
        out.append([np.interp(t, cum, pts[:, 0]), np.interp(t, cum, pts[:, 1])])
    return np.array(out)


def body_panel_points(layout) -> dict:
    """Named panel landmarks (cm) of a front/back panel; keys 'L'/'R' = panel -x / +x."""
    e = _edge_map(layout)
    d = {}
    for s, side in (("R", "right"), ("L", "left")):
        sh, ah, nk, hm = e[f"{side}_shoulder"], e[f"{side}_armhole"], e[f"{side}_neckline"], e[f"{side}_hem"]
        pts = {
            "hps": np.array(sh.start if side == "right" else sh.end, float),
            "tip": np.array(sh.end if side == "right" else sh.start, float),
        }
        arm_pts = np.array(ah.points(24), float)
        pts["armpit"] = arm_pts[np.argmin(arm_pts[:, 1])]
        pts["hem"] = np.array(hm.start if side == "right" else hm.end, float)
        pts["arc"] = _arc_points(ah, 4)
        d[s] = pts
    xs = [p for p in layout.polygon()]
    d["neck_centre"] = np.array(e["right_neckline"].start, float)
    d["hem_centre"] = np.array(e["right_hem"].end, float)
    return d


def sleeve_panel_points(layout, sgn: int) -> dict:
    """Panel landmarks (cm) of the half (sgn=+1: +x half, -1: -x half) of a sleeve piece."""
    poly = np.array(layout.polygon(), float)
    top = poly[np.argmax(poly[:, 1])]
    half = poly[poly[:, 0] * sgn >= -0.01]
    a = half[np.argmax(half[:, 0] * sgn)]                           # widest point = cap end / armpit
    below = half[half[:, 1] < poly[:, 1].min() + 0.5]
    ci = below[np.argmax(below[:, 0] * sgn)]                          # hem end on the underarm side
    near0 = poly[np.abs(poly[:, 0]) < 1.5]
    co = near0[np.argmin(near0[:, 1])]                                # hem at the centre line
    arc = half[(half[:, 1] >= a[1] - 1e-6) & (half[:, 1] <= top[1] + 1e-6)]
    arc = arc[np.argsort(arc[:, 0] * sgn)]
    seg = np.hypot(*np.diff(arc, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    t_s = np.interp(np.linspace(0, cum[-1], 6)[1:-1], cum, np.arange(len(arc)))
    arc_i = np.array([arc[int(round(i))] for i in t_s])
    # arc order goes centre -> armpit; fractions measured from the shoulder tip
    fr = np.linspace(0, 1, 6)[1:-1]
    return {"tip": np.array([0.0, top[1]]), "armpit": a, "cuff_inner": ci, "cuff_outer": np.array([0.0, co[1]]),
            "arc": arc_i, "arc_frac": fr}


# ----------------------------------------------------------------------------- photo landmarks
def clean_mask(mask) -> np.ndarray:
    m = (np.asarray(mask) > 127 if np.asarray(mask).dtype != bool else np.asarray(mask)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    inv = 1 - m
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):                       # fill interior holes (not touching the border)
        x, y, w, h, a = st[i]
        if x > 0 and y > 0 and x + w < m.shape[1] and y + h < m.shape[0]:
            m[lab == i] = 1
    return m.astype(bool)


def _top_y(m: np.ndarray, x: float, half: int = 2) -> Optional[float]:
    x0, x1 = int(max(0, round(x) - half)), int(min(m.shape[1], round(x) + half + 1))
    cols = m[:, x0:x1]
    ys = np.where(cols.any(0), cols.argmax(0), -1)
    ys = ys[ys >= 0]
    return float(np.median(ys)) if len(ys) else None


def photo_landmarks(mask, on_person: bool = False, landmarks: Optional[dict] = None) -> dict:
    """Landmarks of the garment in the photo (pixels), from P06 `garment_landmarks` where
    reliable, otherwise simple outline heuristics.  Each point carries a source tag."""
    m = clean_mask(mask)
    H, W = m.shape
    ys, xs = np.where(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    bh = y1 - y0 + 1
    out = {"flags": [], "mask": m}
    lm = landmarks
    if lm is None and _p06_landmarks is not None:
        try:
            r = _p06_landmarks((m * 255).astype(np.uint8))
            if r.get("ok") and r.get("methods", {}).get("armpit") == "convexity_defect":
                lm = r["landmarks"]
            elif r.get("ok"):
                out["flags"].append("p06_armpit_fallback_not_used")
        except Exception:
            lm = None
    ok_arm = False
    if lm and "armpit_left" in lm and "armpit_right" in lm:
        al, ar = np.array(lm["armpit_left"], float), np.array(lm["armpit_right"], float)
        ok_arm = ar[0] - al[0] > 0.25 * (x1 - x0) and abs(al[1] - ar[1]) < 0.2 * bh
    if ok_arm:
        out["armpit_source"] = "p06_convexity_defect"
    else:
        al = np.array([x0 + 0.0, y0 + 0.35 * bh]); ar = np.array([x1 + 0.0, y0 + 0.35 * bh])
        out["armpit_source"] = "bbox_fallback"
        out["flags"].append("armpit_bbox_fallback")
    out["armpit"] = {"L": al, "R": ar}
    out["p06"] = {k: [float(v[0]), float(v[1])] for k, v in (lm or {}).items()} if ok_arm else None
    span = ar[0] - al[0]
    out["span_px"] = float(span)
    out["top_cropped"] = bool(y0 <= max(2, 0.004 * H))
    out["bottom_cropped"] = bool(y1 >= H - 1 - max(2, 0.004 * H))
    out["on_person"] = on_person
    cx = 0.5 * (al[0] + ar[0])
    out["cx"] = float(cx)
    # shoulder tip: walk up the (inward leaning) armhole line until the mask ends
    tips = {}
    for s, a, inw in (("L", al, 1.0), ("R", ar, -1.0)):
        last = a.copy()
        miss = 0
        for t in range(0, int(a[1]) + 1):
            p = (a[0] + inw * ARM_SLOPE * t, a[1] - t)
            xi, yi = int(round(p[0])), int(round(p[1]))
            if not (0 <= xi < W and 0 <= yi < H):
                break
            if m[yi, xi]:
                last, miss = np.array(p), 0
            else:
                miss += 1
                if miss > 3:
                    break
        tips[s] = last
        sh = (lm or {}).get("shoulder_left" if s == "L" else "shoulder_right") if ok_arm else None
        if sh is not None:
            sh = np.array(sh, float)
            if (a[1] - sh[1]) > 0.12 * bh and abs(sh[0] - a[0]) < 0.35 * span and m[int(np.clip(round(sh[1]), 0, H - 1)), int(np.clip(round(sh[0]), 0, W - 1))]:
                tips[s] = sh
                out["flags"].append(f"tip_{s}_from_p06")
    out["tip"] = tips
    out["tip_ok"] = {s: (tips[s][1] - al[1]) < -0.12 * bh and not out["top_cropped"] for s in "LR"}
    out["bottom"] = float(y1)
    out["top"] = float(y0)
    out["m_top_y"] = lambda x: _top_y(m, x)
    # hem corners
    hem = {}
    row = int(min(H - 1, y1 - max(1, 0.01 * bh)))
    xr = np.where(m[row])[0]
    if len(xr):
        hem = {"L": np.array([xr.min(), row], float), "R": np.array([xr.max(), row], float)}
    hw = (hem["R"][0] - hem["L"][0]) / max(span, 1) if hem else 0
    out["hem_ok"] = bool(hem) and not out["bottom_cropped"] and not on_person and 0.6 < hw < 1.3 \
        and (hem["L"][1] - al[1]) > 0.3 * bh * 0.5
    out["hem"] = hem
    return out


# ----------------------------------------------------------------------------- warping
def _tps_maps(src_pts, dst_pts, out_w, out_h, step=8, smoothing=10.0, mode="tps"):
    """Maps (panel px -> photo px) for cv2.remap, from landmark correspondences (dst -> src)."""
    dst = np.asarray(dst_pts, float); src = np.asarray(src_pts, float)
    gx = np.arange(0, out_w // step + 2) * step
    gy = np.arange(0, out_h // step + 2) * step
    G = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2).astype(float)
    if mode == "affine":
        A = np.hstack([dst, np.ones((len(dst), 1))])
        coef, *_ = np.linalg.lstsq(A, src, rcond=None)
        S = (np.hstack([G, np.ones((len(G), 1))]) @ coef)
    else:
        rbf = RBFInterpolator(dst, src, kernel="thin_plate_spline", smoothing=smoothing)
        S = rbf(G)
    S = S.reshape(len(gy), len(gx), 2).astype(np.float32)
    ix = (np.arange(out_w, dtype=np.float32) / step)[None, :].repeat(out_h, 0)
    iy = (np.arange(out_h, dtype=np.float32) / step)[:, None].repeat(out_w, 1)
    mx = cv2.remap(S[:, :, 0], ix, iy, cv2.INTER_LINEAR)
    my = cv2.remap(S[:, :, 1], ix, iy, cv2.INTER_LINEAR)
    return mx, my


def fill_holes(rgb, valid, panel_mask, ppc):
    """Fill panel pixels without photo data from neighbouring fabric (inpaint thin gaps,
    nearest-fabric colour smoothed over ~1 cm for large ones). Returns rgb, filled_mask."""
    need = panel_mask & ~valid
    if not need.any() or not valid.any():
        return rgb, need
    dist, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
    near = rgb[iy, ix]
    smooth = cv2.GaussianBlur(near, (0, 0), max(1.0, ppc * 0.8))
    out = rgb.copy()
    out[need] = smooth[need]
    thin = need & (dist <= 4)
    if thin.any():
        out = cv2.inpaint(np.ascontiguousarray(out), thin.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
    return out, need


def print_free(rgb, mask):
    """Photo with the print removed: pixels that differ from the local fabric colour (P04 fabric
    model, colour-block aware) are replaced by the fabric colour field of their block."""
    h, w = mask.shape
    try:
        import cv_design_regions as dr
        P = dr.prepare(rgb, mask.astype(bool))
        design = (P.dev > 9) & P.mask
        dk = int(max(5, 0.02 * P.diag)) | 1
        design = cv2.dilate(design.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dk, dk))) > 0
        good = P.mask & ~design
        small = P.rgb.astype(np.float32)
        out = small.copy()
        bid = P.block_id if P.block_id is not None else np.zeros(good.shape, np.int32)
        sig = max(4.0, 0.05 * P.diag)
        k = int(sig * 6) | 1
        for b in np.unique(bid[P.mask]):
            reg = (bid == b) & P.mask
            wt = (reg & good).astype(np.float32)
            if wt.sum() < 20:
                continue
            num = cv2.GaussianBlur(small * wt[..., None], (k, k), sig)
            den = cv2.GaussianBlur(wt, (k, k), sig)[..., None]
            # also spread beyond reach: fall back to nearest good colour
            fld = num / np.maximum(den, 1e-4)
            far = (den[..., 0] < 1e-3)
            if far.any():
                _, (iy, ix) = ndi.distance_transform_edt(wt == 0, return_indices=True)
                fld[far] = small[iy, ix][far]
            sel = reg & design
            out[sel] = fld[sel]
        s = P.scale
        up = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        dm = cv2.resize(design.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        dm = cv2.GaussianBlur(dm, (0, 0), max(1.5, 0.012 * math.sqrt(float(mask.sum()))))[..., None]
        res = (up * dm + rgb.astype(np.float32) * (1 - dm)).clip(0, 255).astype(np.uint8)
        return res, float(design.sum() / max(P.mask.sum(), 1)), "p04_fabric_model"
    except Exception as ex:                        # fallback: big median filter on the masked photo
        k = int(max(5, 0.06 * math.sqrt(mask.sum()))) | 1
        res = cv2.medianBlur(rgb, min(k, 255))
        return res, float("nan"), f"median_fallback({type(ex).__name__})"


def _panel_polygon_px(layout, ppc):
    poly = np.array(layout.polygon(n_per_segment=64), float)
    xmin, ymax = poly[:, 0].min(), poly[:, 1].max()
    w = max(1, int(round((poly[:, 0].max() - xmin) * ppc)))
    h = max(1, int(round((ymax - poly[:, 1].min()) * ppc)))
    px = np.stack([(poly[:, 0] - xmin) * ppc, (ymax - poly[:, 1]) * ppc], 1)
    return poly, px, w, h, xmin, ymax


def _to_px(pts_cm, xmin, ymax, ppc):
    p = np.atleast_2d(np.asarray(pts_cm, float))
    return np.stack([(p[:, 0] - xmin) * ppc, (ymax - p[:, 1]) * ppc], 1)


def _poly_mask(px, w, h):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(px).astype(np.int32).reshape(-1, 1, 2)], 255)
    return m > 0


# ----------------------------------------------------------------------------- one photo
class PhotoView:
    """A garment photo prepared for panel mapping (rescaled to the target density)."""

    def __init__(self, rgb, mask, view, ppc, on_person=False, landmarks=None):
        self.view = view
        lm0 = photo_landmarks(mask, on_person=on_person, landmarks=landmarks)
        panel_span_cm = 2 * 26.0   # normalised below once the layout is known
        self.lm0 = lm0
        self.rgb0, self.mask0 = rgb, lm0["mask"]
        self.on_person = on_person
        self.ppc_target = ppc

    def prepare(self, layout_body):
        pb = body_panel_points(layout_body)
        span_cm = abs(pb["R"]["armpit"][0] - pb["L"]["armpit"][0])
        self.native_ppc = self.lm0["span_px"] / span_cm
        if self.ppc_target is None:
            self.ppc_target = float(np.clip(self.native_ppc, PPC_MIN, PPC_MAX))
        f = self.ppc_target / self.native_ppc
        self.f = f if f < 0.8 else 1.0
        if self.f != 1.0:
            rgb = cv2.resize(self.rgb0, None, fx=self.f, fy=self.f, interpolation=cv2.INTER_AREA)
            mask = cv2.resize(self.mask0.astype(np.uint8), (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
            p06 = self.lm0.get("p06")
            self.lm = photo_landmarks(mask, self.on_person,
                                      landmarks={k: [v[0] * self.f, v[1] * self.f] for k, v in p06.items()} if p06 else None)
        else:
            rgb, mask, self.lm = self.rgb0, self.mask0, self.lm0
        self.rgb, self.mask = rgb, mask
        self.eff_ppc = self.native_ppc * self.f            # photo px per panel cm actually used
        return self

    # --- regions
    def regions(self):
        lm, m = self.lm, self.mask
        H, W = m.shape
        yy, xx = np.mgrid[0:H, 0:W]
        al, ar = lm["armpit"]["L"], lm["armpit"]["R"]
        def xline(A, S):
            den = max(A[1] - S[1], 1.0)
            f = np.clip((A[1] - yy) / den, 0, 1)
            return A[0] + (S[0] - A[0]) * f
        sl = m & (xx < xline(al, lm["tip"]["L"]))
        sr = m & (xx > xline(ar, lm["tip"]["R"]))
        # only keep sleeve pixels connected to the outside part (left of / right of the torso column)
        tor = m & ~sl & ~sr
        reg = {"torso": tor}
        for s, r in (("L", sl), ("R", sr)):
            r = r.astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(r)
            if n > 1:
                r = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            reg["sleeve_" + s] = r.astype(bool)
            if r.sum() < 0.012 * m.sum():
                reg["sleeve_" + s] = np.zeros_like(m)
        # sleeves pixels dropped above go back to torso only if they are tiny; leave them out
        self.reg = reg
        return reg

    def sleeve_corners(self, s):
        """Photo landmarks (tip S, armpit A, cuff outer Co, cuff inner Ci) of the sleeve on side s."""
        r = self.reg["sleeve_" + s]
        if not r.any():
            return None
        lm = self.lm
        A = lm["armpit"][s]; S = lm["tip"][s]
        u = A - S
        L = np.hypot(*u)
        if L < 5:
            return None
        u = u / L
        n = np.array([-u[1], u[0]])
        if (n[0] < 0) != (s == "L"):          # n must point away from the torso
            n = -n
        ys, xs = np.where(r)
        P = np.stack([xs, ys], 1).astype(float)
        M = 0.5 * (S + A)
        ax = P.mean(0) - M                          # arm axis: from the armhole mid-point to the sleeve centroid
        if np.hypot(*ax) < 1e-6:
            return None
        ax = ax / np.hypot(*ax)
        pe = np.array([-ax[1], ax[0]])
        e = (P - M) @ ax
        if e.max() < 0.08 * L:
            return None
        band = e >= e.max() - 0.10 * L              # cuff band: the far end of the sleeve
        q = (P[band] - M) @ pe
        t = (P[band] - S) @ u
        lo, hi = np.percentile(q, 4), np.percentile(q, 96)
        e1 = P[band][q <= lo].mean(0); e2 = P[band][q >= hi].mean(0)
        # Co = cuff corner on the shoulder side (smaller position along S->A), Ci = the underarm side
        if (e1 - S) @ u <= (e2 - S) @ u:
            co, ci = e1, e2
        else:
            co, ci = e2, e1
        if np.hypot(*(co - ci)) < 0.35 * L:        # triangle-like sleeve (apex, no usable cuff edge)
            apex = P[np.argmax(e)]
            return {"S": S, "A": A, "apex": apex}
        return {"S": S, "A": A, "Co": co, "Ci": ci}


# ----------------------------------------------------------------------------- build texture
def _sample(rgb, region, mx, my, valid_extra=None):
    h, w = mx.shape
    tex = cv2.remap(rgb, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    r = cv2.erode(region.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    rv = cv2.remap(r.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderValue=0)
    return tex, rv > 0.98


def body_src_points(pv: PhotoView, pb: dict, use_neck=True):
    """Source (photo) / destination (panel cm) landmark pairs for a torso panel.
    Landmarks that cannot be trusted (cropped, occluded, on-person hem) are *estimated* from the
    armpit span (assumption recorded)."""
    lm = pv.lm
    al, ar = lm["armpit"]["L"], lm["armpit"]["R"]
    sc = lm["span_px"] / abs(pb["R"]["armpit"][0] - pb["L"]["armpit"][0])    # photo px per cm
    cx = lm["cx"]
    pairs, notes = [], []
    # armpits (always)
    for s in "LR":
        pairs.append((lm["armpit"][s], pb[s]["armpit"], "armpit"))
    # shoulder tips and armhole arc
    for s in "LR":
        A = lm["armpit"][s]
        tip_ok = lm["tip_ok"][s]
        if tip_ok:
            S = lm["tip"][s]
        else:
            ptip, pa = pb[s]["tip"], pb[s]["armpit"]
            S = np.array([A[0] + (ptip[0] - pa[0]) * sc, A[1] - (ptip[1] - pa[1]) * sc])
            notes.append(f"shoulder_tip_{s}_estimated")
        pairs.append((S, pb[s]["tip"], "tip"))
        # arc: equal arc length fractions A->S  <->  panel armhole arc points (from armpit to tip)
        arc = pb[s]["arc"]
        order = np.argsort(arc[:, 1])                       # from armpit (low y) upward
        arc = arc[order]
        for i, p in enumerate(arc):
            fr = (i + 1) / (len(arc) + 1)
            pairs.append((A + (S - A) * fr, p, "arc"))
    # neck and shoulder line (need an uncropped top)
    if not lm["top_cropped"] and use_neck:
        # HPS x from the panel ratio, y from the photo outline
        for s, sg in (("L", -1), ("R", 1)):
            S = [p for p in pairs if p[2] == "tip" and np.allclose(p[1], pb[s]["tip"])][0][0]
            ratio = pb[s]["hps"][0] / pb[s]["tip"][0]
            hx = cx + ratio * (S[0] - cx)
            hy = lm["m_top_y"](hx)
            if hy is not None:
                pairs.append((np.array([hx, hy]), pb[s]["hps"], "hps"))
                for t in (1 / 3, 2 / 3):               # shoulder line
                    xx = hx + (S[0] - hx) * t
                    yy = lm["m_top_y"](xx)
                    if yy is not None:
                        pairs.append((np.array([xx, yy]), pb[s]["hps"] + (pb[s]["tip"] - pb[s]["hps"]) * t, "shoulder"))
        ny = lm["m_top_y"](cx)
        if ny is not None:
            pairs.append((np.array([cx, ny]), pb["neck_centre"], "neck"))
    else:
        notes.append("neck_and_shoulder_line_not_used(top_cropped_or_disabled)")
    # hem
    if lm["hem_ok"]:
        for s in "LR":
            pairs.append((lm["hem"][s], pb[s]["hem"], "hem"))
        pairs.append((np.array([cx, lm["bottom"]]), pb["hem_centre"], "hem_c"))
    else:
        notes.append("hem_estimated_from_armpit_span(cropped/occluded/on_person)")
        for s in "LR":
            pa, ph = pb[s]["armpit"], pb[s]["hem"]
            pairs.append((np.array([lm["armpit"][s][0] + (ph[0] - pa[0]) * sc, lm["armpit"][s][1] + (pa[1] - ph[1]) * sc]), ph, "hem_est"))
    src = np.array([p[0] for p in pairs], float)
    dst = np.array([p[1] for p in pairs], float)
    kinds = [p[2] for p in pairs]
    return src, dst, kinds, notes


def build_body_texture(pv: PhotoView, layout, pb, ppc, mode="tps", image=None, region=None):
    """Torso region -> body panel texture. Returns dict(rgba, valid, info)."""
    poly, ppx, w, h, xmin, ymax = _panel_polygon_px(layout, ppc)
    pm = _poly_mask(ppx, w, h)
    src, dst_cm, kinds, notes = body_src_points(pv, pb)
    dst = _to_px(dst_cm, xmin, ymax, ppc)
    mx, my = _tps_maps(src, dst, w, h, mode=mode)
    rgb = pv.rgb if image is None else image
    reg = pv.reg["torso"] if region is None else region
    tex, valid = _sample(rgb, reg, mx, my)
    valid &= pm
    return dict(tex=tex, valid=valid, pm=pm, src=src, dst=dst, kinds=kinds, notes=notes, poly=ppx,
                w=w, h=h, xmin=xmin, ymax=ymax, mx=mx, my=my)


def build_sleeve_halves(pv: PhotoView, layout, ppc, image=None, mode="tps"):
    """Warp the photo sleeves of `pv` into the matching half of the sleeve piece.
    Returns {"L": dict, "R": dict} for image sides that have a sleeve."""
    out = {}
    for s in "LR":
        c = pv.sleeve_corners(s)
        if c is None:
            continue
        # image-right sleeve -> -x half, image-left -> +x half
        sgn = -1 if s == "R" else 1
        sp = sleeve_panel_points(layout, sgn)
        poly, ppx, w, h, xmin, ymax = _panel_polygon_px(layout, ppc)
        pm = _poly_mask(ppx, w, h)
        pairs = [(c["S"], sp["tip"]), (c["A"], sp["armpit"])]
        for fr, p in zip(sp["arc_frac"], sp["arc"]):
            pairs.append((c["S"] + (c["A"] - c["S"]) * fr, p))
        if "apex" in c:                              # 3-point (affine-like) fit
            pairs.append((c["apex"], 0.5 * (sp["cuff_inner"] + sp["cuff_outer"])))
        else:
            pairs += [(c["Ci"], sp["cuff_inner"]), (c["Co"], sp["cuff_outer"])]
            for t in (1 / 3, 2 / 3):
                pairs.append((c["S"] + (c["Co"] - c["S"]) * t, sp["tip"] + (sp["cuff_outer"] - sp["tip"]) * t))
        src = np.array([p[0] for p in pairs]); dst = _to_px([p[1] for p in pairs], xmin, ymax, ppc)
        mx, my = _tps_maps(src, dst, w, h, mode=mode)
        reg = pv.reg["sleeve_" + s]
        tex, valid = _sample(pv.rgb if image is None else image, reg, mx, my)
        x0 = (0 - xmin) * ppc
        cols = np.arange(w)
        half = ((cols - x0) * sgn >= 0)[None, :].repeat(h, 0)
        valid &= half & pm
        out[s] = dict(side=s, tex=tex, valid=valid, half=half, x0=x0, sgn=sgn, pm=pm, src=src, dst=dst, poly=ppx, w=w, h=h,
                      xmin=xmin, ymax=ymax, mx=mx, my=my)
    return out


def _mirror(tex, valid, x0):
    M = np.array([[-1, 0, 2 * x0], [0, 1, 0]], np.float32)
    h, w = valid.shape
    t2 = cv2.warpAffine(tex, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    v2 = cv2.warpAffine(valid.astype(np.uint8), M, (w, h), flags=cv2.INTER_NEAREST) > 0
    return t2, v2


def _finish(tex, valid, pm, ppc):
    tex, filled = fill_holes(tex, valid, pm, ppc)
    a = pm.astype(np.uint8) * 255
    rgba = np.dstack([tex, a])
    rgba[~pm, :3] = 0
    return rgba, filled


def build_panel_maps(
    front_rgb: Optional[np.ndarray],
    back_rgb: Optional[np.ndarray],
    layouts: dict,
    front_mask: Optional[np.ndarray] = None,
    back_mask: Optional[np.ndarray] = None,
    px_per_cm: Optional[float] = None,
    on_person: bool = False,
    landmarks_front: Optional[dict] = None,
    landmarks_back: Optional[dict] = None,
    warp: str = "tps",
    sources: Optional[dict] = None,
) -> dict:
    """Return {"panels": {piece: {"rgba", "meta"}}, "info": {...}, "views": {...}}.

    front_rgb / back_rgb: RGB photos (either may be None; at least one is required).
    The photo with a view gets its own panel; the other body panel is filled from the photo's
    print-free fabric colours (assumption recorded).
    """
    assert front_rgb is not None or back_rgb is not None
    sources = sources or {}
    views = {}
    lay_b = layouts.get("front_panel") or layouts.get("back_panel")
    ppc = px_per_cm
    for name, rgb, mask, lmk in (("front", front_rgb, front_mask, landmarks_front), ("back", back_rgb, back_mask, landmarks_back)):
        if rgb is None:
            continue
        if mask is None:
            raise ValueError(f"{name} photo needs a garment mask")
        pv = PhotoView(rgb, mask, name, ppc, on_person=on_person, landmarks=lmk).prepare(lay_b)
        pv.regions()
        views[name] = pv
        if ppc is None:
            ppc = pv.ppc_target
    # one common density for all panels
    panels, info = {}, {"px_per_cm": ppc, "warp": warp, "photo_native_px_per_cm": {k: round(v.native_ppc, 3) for k, v in views.items()}}
    # re-prepare views at the common ppc (when two photos gave different densities)
    for k, v in views.items():
        if abs(v.ppc_target - ppc) > 1e-6:
            v.ppc_target = ppc
            v.prepare(lay_b); v.regions()

    main = views.get("front") or views.get("back")
    clean_cache = {}

    def clean_of(v):
        if id(v) not in clean_cache:
            rgb_c, frac, how = print_free(v.rgb, v.mask)
            clean_cache[id(v)] = (rgb_c, frac, how)
        return clean_cache[id(v)]

    warps = {}
    for piece, layout in layouts.items():
        low = piece.lower()
        if "sleeve" in low:
            continue
        kind = "back" if "back" in low else "front"
        pb = body_panel_points(layout)
        if kind in views:
            v = views[kind]
            r = build_body_texture(v, layout, pb, ppc, mode=warp)
            rgba, filled = _finish(r["tex"], r["valid"], r["pm"], ppc)
            src_desc = f"{kind} photo, torso region, {warp.upper()} warp"
            assumptions = []
            design = True
        else:
            v = main
            rgb_c, frac, how = clean_of(v)
            r = build_body_texture(v, layout, pb, ppc, mode=warp, image=rgb_c)
            rgba, filled = _finish(r["tex"], r["valid"], r["pm"], ppc)
            src_desc = f"{v.view} photo (print removed), torso region, {warp.upper()} warp"
            design = False
            assumptions = [f"No {kind} photo: this panel is the {v.view} photo with the print removed ({how}, "
                           f"{frac:.1%} of the garment treated as print). The {kind} is ASSUMED to have the same "
                           f"fabric colours / colour blocks and no print."]
        assumptions += [*r["notes"], f"landmark_source={v.lm['armpit_source']}"]
        if v.on_person:
            assumptions.append("photo is of a person: hem and (if cropped) neck/shoulders estimated from the chest width")
        warps[piece] = dict(view=v, kind="body", res=r, photo_view=kind if kind in views else v.view)
        panels[piece] = _pack(piece, rgba, filled, r, ppc, v, src_desc, assumptions, design, layout)

    for piece, layout in layouts.items():
        low = piece.lower()
        if "sleeve" not in low:
            continue
        sleeve_left = "left" in low
        # image side that carries the piece's FRONT half / BACK half
        # front photo: image-right sleeve -> sleeve_left ; back photo: image-left sleeve -> sleeve_left
        want = {"front": "R" if sleeve_left else "L", "back": "L" if sleeve_left else "R"}
        halves, used, assum = {}, [], []
        tex = None
        for vn in ("front", "back"):
            if vn not in views:
                continue
            hv = build_sleeve_halves(views[vn], layout, ppc, mode=warp)
            if want[vn] in hv:
                halves[vn] = hv[want[vn]]
                used.append(vn)
        if not halves:
            # no sleeve region in any photo: neighbouring torso fabric colour, print removed
            v = main
            rgb_c, _, _ = clean_of(v)
            poly, ppx, w, h, xmin, ymax = _panel_polygon_px(layout, ppc)
            pm = _poly_mask(ppx, w, h)
            med = np.median(rgb_c[v.reg["torso"]], axis=0).astype(np.uint8)
            tex = np.tile(med, (h, w, 1)); valid = np.zeros((h, w), bool)
            rgba, filled = _finish(tex, valid, pm, ppc)
            info.setdefault("notes", []).append(f"{piece}: no sleeve region found; solid fabric colour")
            r = dict(src=np.zeros((0, 2)), dst=np.zeros((0, 2)), poly=ppx, w=w, h=h, xmin=xmin, ymax=ymax, pm=pm, valid=valid)
            warps[piece] = dict(view=v, kind="sleeve", res=r, halves={})
            panels[piece] = _pack(piece, rgba, filled, r, ppc, v, "solid fabric colour (no sleeve region in photo)",
                                  ["no sleeve region detected: solid colour of the torso fabric (print removed)"], False, layout)
            continue
        first = halves[used[0]]
        h_, w_ = first["valid"].shape
        tex = np.zeros((h_, w_, 3), np.uint8); valid = np.zeros((h_, w_), bool)
        for vn in used:
            hh = halves[vn]
            tex = np.where(hh["valid"][..., None], hh["tex"], tex); valid |= hh["valid"]
        # second half from the mirror of the first when no photo of the other side
        if len(used) < 2:
            t2, v2 = _mirror(np.where(first["valid"][..., None], first["tex"], 0).astype(np.uint8), first["valid"], first["x0"])
            m2 = v2 & ~first["half"] & first["pm"]
            tex = np.where(m2[..., None], t2, tex); valid |= m2
            half_nm = "back" if used[0] == "front" else "front"
            assum.append(f"{half_nm} half of the sleeve is a MIRROR of the {used[0]} half (no {half_nm} photo)")
        rgba, filled = _finish(tex, valid, first["pm"], ppc)
        warps[piece] = dict(view=views[used[0]], kind="sleeve", res=first, halves={u: halves[u] for u in used})
        panels[piece] = _pack(piece, rgba, filled, first, ppc, views[used[0]],
                              "sleeve region of the " + " + ".join(used) + f" photo, {warp.upper()} warp",
                              assum + [f"landmark_source={views[used[0]].lm['armpit_source']}"], True, layout)
    info["views"] = {k: {"native_px_per_cm": round(v.native_ppc, 3), "photo_scale_applied": round(v.f, 4),
                         "armpit_source": v.lm["armpit_source"], "flags": v.lm["flags"],
                         "top_cropped": v.lm["top_cropped"], "bottom_cropped": v.lm["bottom_cropped"],
                         "hem_trusted": v.lm["hem_ok"],
                         "sleeves_found": [s for s in "LR" if v.reg["sleeve_" + s].any()]} for k, v in views.items()}
    return {"panels": panels, "info": info, "views": views, "warps": warps}


def _pack(piece, rgba, filled, r, ppc, v, src_desc, assumptions, from_photo, layout):
    h, w = rgba.shape[:2]
    pm = r["pm"]
    cover = float((r["valid"] & pm).sum() / max(pm.sum(), 1)) if "valid" in r else 0.0
    meta = {
        "texture_size_px": [w, h],
        "texture_size_mm": [round(w / ppc * 10, 2), round(h / ppc * 10, 2)],
        "px_per_cm": round(ppc, 4),
        "px_per_mm": round(ppc / 10, 5),
        "mm_per_px": round(10.0 / ppc, 5),
        "panel_bbox_cm": [round(r["xmin"], 4), round(r["ymax"] - h / ppc, 4), round(r["xmin"] + w / ppc, 4), round(r["ymax"], 4)],
        "origin": {"image_px": [0, 0], "panel_xy_cm": [round(r["xmin"], 4), round(r["ymax"], 4)],
                   "note": "image top-left = panel point (xmin, ymax) in cm; image x right = panel +x, image y down = panel -y; 1 px = 1/px_per_cm cm"},
        "panel_polygon_px": np.round(r["poly"], 2).tolist(),
        "source": src_desc,
        "from_photo": bool(from_photo),
        "photo_native_px_per_cm": round(v.native_ppc, 3),
        "photo_px_per_cm_used": round(v.eff_ppc, 3),
        "resolution_note": ("upsampled from the photo (no new detail)" if ppc > v.eff_ppc * 1.05 else
                            "at or below the photo's own density"),
        "photo_coverage_of_panel": round(cover, 4),
        "filled_fraction": round(float(filled.sum() / max(pm.sum(), 1)), 4),
        "assumptions": assumptions,
    }
    return {"rgba": rgba, "meta": meta}
