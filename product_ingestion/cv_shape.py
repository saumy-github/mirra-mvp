"""cv_shape: read a garment's SHAPE from its outline mask (CV project, plan P06).

Input : a binary garment mask (uint8 0/255 or bool), upright, ideally a FLAT, FRONT or BACK
        photo of a top (T-shirt, tank, long sleeve). Optional photo only for overlays.
Output: a JSON-serialisable dict with landmarks (pixel coords in the INPUT mask frame), lengths
        in pixels, scale-free ratios, a sleeve-length class, neckline depth and a fit estimate.

Method (all classical, numpy / OpenCV only):
  1. clean_outline : largest component, small holes filled, contour resampled to a fixed number of
     points and Gaussian-smoothed along the arc (curvature-safe).
  2. armpits       : deepest convexity defects of the contour in the left and right halves
                     (primary). Fallback: steepest drop of the row-width profile.
  3. neck points   : highest points of the top profile either side of the neckline dip.
  4. shoulder pts  : where the contour leaves the straight shoulder line fitted just outside the neck.
  5. sleeve        : contour between shoulder point and armpit; cuff corners from the sleeve axis.
  6. hem corners   : outer bottom corners of the body contour between the two armpits.
  7. Hough lines   : straight outline segments (hem, side seams) as a cross-check (hough_outline_lines).

No metric scale exists in a photo, so every ratio is a ratio of two pixel lengths.
Everything is computed at a working size (garment height WORK_H) and mapped back to input pixels.

Usage:
    from cv_shape import analyze_shape, draw_overlay, detect_keypoints
    res = analyze_shape(mask)                 # dict, JSON-serialisable
    res["sleeve"]["class"], res["ratios"]["hem_to_chest"], res["landmarks"]["armpit_left"]
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

WORK_H = 480            # garment bbox height at working size
N_CONTOUR = 900         # resampled contour points
SMOOTH_SIGMA = 2.0      # in contour points (~ 6 px at WORK_H)

# Sleeve length class thresholds on  sleeve_length / garment_length  (calibrated, see out/p06_shape/REPORT.md)
SLEEVE_BREAKS = (("sleeveless", 0.10), ("short", 0.40), ("elbow", 0.56), ("three_quarter", 0.70), ("long", 9.0))

LANDMARK_NAMES = ["neck_left", "neck_right", "neck_dip", "shoulder_left", "shoulder_right",
                  "armpit_left", "armpit_right", "cuff_left_upper", "cuff_left_lower",
                  "cuff_right_upper", "cuff_right_lower", "hem_left", "hem_right"]


# --------------------------------------------------------------------------- helpers
def _binary(mask) -> np.ndarray:
    m = np.asarray(mask)
    if m.ndim == 3:
        m = m[..., 0]
    if m.dtype == bool:
        return m.astype(np.uint8)
    if m.max() <= 1:
        return (m > 0).astype(np.uint8)
    return (m > 127).astype(np.uint8)


def clean_mask(mask, min_hole_frac: float = 0.0004) -> np.ndarray:
    """Largest component, holes smaller than min_hole_frac of the area filled, 3x3 open/close."""
    m = _binary(mask)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return m
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == k).astype(np.uint8)
    area = int(m.sum())
    inv = 1 - m
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    for j in range(1, n2):
        x, y, w, h, a = st2[j]
        touches = x == 0 or y == 0 or x + w == m.shape[1] or y + h == m.shape[0]
        if not touches and a < min_hole_frac * area:
            m[lab2 == j] = 1
    k3 = np.ones((3, 3), np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k3)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k3)
    return m


def _resample_closed(pts: np.ndarray, n: int) -> np.ndarray:
    pts = pts.astype(np.float64)
    d = np.sqrt((np.diff(np.vstack([pts, pts[:1]]), axis=0) ** 2).sum(1))
    s = np.concatenate([[0], np.cumsum(d)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    return np.stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])], 1)


def open_slits(wm: np.ndarray, min_area_frac: float = 0.0006):
    """Long sleeves that hang against the body leave a thin enclosed gap (slit) between sleeve and body, so the OUTER
    outline has no armpit concavity. Cut a 3 px channel from the bottom of each tall side hole to the bottom of the
    garment so the slit becomes an ordinary outline notch whose far end is the armpit. Returns (mask, n_cut)."""
    m = wm.copy()
    area = int(m.sum())
    ys, xs = np.nonzero(m)
    H, W = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    cx = xs.mean()
    n, lab, st, cen = cv2.connectedComponentsWithStats(1 - m, connectivity=4)
    cut = 0
    for j in range(1, n):
        x, y, w, h, a = st[j]
        if x == 0 or y == 0 or x + w == m.shape[1] or y + h == m.shape[0]:
            continue                      # not enclosed (background)
        if a < min_area_frac * area or h < 0.12 * H or h < 2.0 * w:
            continue
        if abs(cen[j][0] - cx) < 0.12 * W:
            continue
        yy, xx = np.nonzero(lab == j)
        yb = yy.max()
        xb = int(round(xx[yy >= yb - 3].mean()))
        m[yb:, max(xb - 1, 0):xb + 2] = 0
        cut += 1
    return m, cut


def clean_outline(mask, work_h: int = WORK_H, n: int = N_CONTOUR, sigma: float = SMOOTH_SIGMA):
    """Return (work_mask, contour(n,2) float in WORK coords, scale, bbox_input). Contour order:
    starts at the top-most point and runs top -> left -> bottom -> right (visual counter-clockwise)."""
    m = clean_mask(mask)
    ys, xs = np.nonzero(m)
    if len(xs) < 50:
        raise ValueError("mask is empty")
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    scale = work_h / float(y1 - y0 + 1)
    wm = cv2.resize(m.astype(np.float32), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    wm = (wm > 0.5).astype(np.uint8)
    wm = clean_mask(wm * 255)
    wm, n_slits = open_slits(wm)
    cs, _ = cv2.findContours(wm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :]
    c = _resample_closed(c, n)
    c = np.stack([gaussian_filter1d(c[:, 0], sigma, mode="wrap"), gaussian_filter1d(c[:, 1], sigma, mode="wrap")], 1)
    # rotate to start at the top-most point, orient top -> left -> bottom -> right
    it = int(np.argmin(c[:, 1]))
    c = np.roll(c, -it, axis=0)
    il, ir = int(np.argmin(c[:, 0])), int(np.argmax(c[:, 0]))
    if il > ir:                      # right visited before left -> reverse
        c = np.vstack([c[:1], c[1:][::-1]])
    return wm, c, scale, (int(x0), int(y0), int(x1), int(y1))


def _arc(c: np.ndarray, i: int, j: int) -> np.ndarray:
    """Indices from i forward to j (inclusive), circular."""
    n = len(c)
    i, j = i % n, j % n
    return np.arange(i, j + 1) if j >= i else np.concatenate([np.arange(i, n), np.arange(0, j + 1)])


def convexity_defects(c: np.ndarray) -> List[dict]:
    """Defects of the convex hull of the (smoothed) contour: far point, depth (px), start/end idx."""
    n = len(c)
    hull = cv2.convexHull(c.astype(np.float32), returnPoints=False).ravel()
    hull = np.sort(hull)
    out = []
    for k in range(len(hull)):
        a, b = int(hull[k]), int(hull[(k + 1) % len(hull)])
        idx = _arc(c, a, b)
        if len(idx) < 4:
            continue
        pa, pb = c[a], c[b]
        d = pb - pa
        L = float(np.hypot(*d))
        if L < 1e-6:
            continue
        nrm = np.array([-d[1], d[0]]) / L
        dist = np.abs((c[idx] - pa) @ nrm)
        j = int(np.argmax(dist))
        out.append({"start": a, "end": b, "far": int(idx[j]), "depth": float(dist[j])})
    return out


def _top_profile(wm: np.ndarray) -> np.ndarray:
    h, w = wm.shape
    any_ = wm.any(0)
    tp = np.where(any_, wm.argmax(0).astype(np.float64), np.nan)
    # fill gaps, smooth lightly
    xs = np.arange(w)
    ok = ~np.isnan(tp)
    if ok.sum() < 3:
        return tp
    tp = np.interp(xs, xs[ok], tp[ok])
    tp[~any_] = np.nan
    return tp


def _row_extent(wm: np.ndarray):
    any_ = wm.any(1)
    xl = np.where(any_, wm.argmax(1), 0)
    xr = np.where(any_, wm.shape[1] - 1 - wm[:, ::-1].argmax(1), 0)
    return xl.astype(np.int64), xr.astype(np.int64), wm.sum(1).astype(np.int64)


def _dist_to_line(P: np.ndarray, p0: np.ndarray, d: np.ndarray) -> np.ndarray:
    d = d / (np.linalg.norm(d) + 1e-12)
    n = np.array([-d[1], d[0]])
    return (P - p0) @ n


# --------------------------------------------------------------------------- landmarks
def _find_armpits(wm, c, W, H, x0, y0):
    """Return (iL, iR, method). Index into contour or None."""
    cx = (wm.nonzero()[1].mean())
    defects = convexity_defects(c)
    cand = []
    for d in defects:
        p = c[d["far"]]
        if d["depth"] < 0.02 * H:
            continue
        if not (y0 + 0.06 * H <= p[1] <= y0 + 0.80 * H):
            continue
        cand.append((d["depth"], d["far"], p))
    left = [t for t in cand if t[2][0] < cx - 0.12 * W]
    right = [t for t in cand if t[2][0] > cx + 0.12 * W]
    iL = max(left, key=lambda t: t[0])[1] if left else None
    iR = max(right, key=lambda t: t[0])[1] if right else None
    method = "convexity_defect"
    if iL is None or iR is None:
        # width-profile fallback: steepest drop of the row width
        xl, xr, cnt = _row_extent(wm)
        k = max(2, int(0.03 * H))
        ys = np.arange(int(y0 + 0.12 * H), int(y0 + 0.70 * H))
        drop = np.array([cnt[y - k] - cnt[min(y + k, len(cnt) - 1)] for y in ys])
        yA = int(ys[int(np.argmax(drop))]) + k // 2
        pL = np.array([xl[min(yA + k, len(xl) - 1)], yA], float)
        pR = np.array([xr[min(yA + k, len(xr) - 1)], yA], float)
        if iL is None:
            iL = int(np.argmin(((c - pL) ** 2).sum(1)))
        if iR is None:
            iR = int(np.argmin(((c - pR) ** 2).sum(1)))
        method = "width_profile_fallback"
    return iL, iR, method


def _neck(wm, c, xL, xR, W, H, cx):
    tp = _top_profile(wm)
    xs = np.arange(len(tp))
    tps = gaussian_filter1d(np.nan_to_num(tp, nan=np.nanmax(tp)), 2.0)
    lo, hi = int(cx - 0.22 * W), int(cx + 0.22 * W)
    lo, hi = max(lo, 0), min(hi, len(tp) - 1)
    xd = lo + int(np.argmax(tps[lo:hi + 1]))
    # neck points: highest point left / right of the dip within 0.30 W
    a, b = max(int(xd - 0.30 * W), 0), xd
    xnl = a + int(np.argmin(tps[a:b + 1]))
    a, b = xd, min(int(xd + 0.30 * W), len(tp) - 1)
    xnr = a + int(np.argmin(tps[a:b + 1]))
    ynl, ynr, yd = tps[xnl], tps[xnr], tps[xd]
    depth = float(yd - 0.5 * (ynl + ynr))
    # notch area for the V / round decision
    seg = tps[xnl:xnr + 1]
    base = 0.5 * (ynl + ynr)
    area = float(np.clip(seg - base, 0, None).sum())
    width = float(max(xnr - xnl, 1))
    fullness = area / (width * max(depth, 1e-6)) if depth > 1e-6 else 0.0
    return (xnl, float(ynl)), (xnr, float(ynr)), (xd, float(yd)), depth, fullness


def _nearest_idx(c, p, idx=None):
    if idx is None:
        idx = np.arange(len(c))
    d = ((c[idx] - np.asarray(p, float)) ** 2).sum(1)
    return int(idx[int(np.argmin(d))])


def _shoulder_point(c, path_idx, W, H):
    """path_idx: contour indices from neck point outwards to the armpit. Return contour index of S, method."""
    P = c[path_idx]
    seg = np.sqrt((np.diff(P, axis=0) ** 2).sum(1))
    s = np.concatenate([[0], np.cumsum(seg)])
    sel = (s >= 0.04 * W) & (s <= 0.12 * W)
    if sel.sum() < 4:
        sel = (s >= 0.02 * W) & (s <= 0.20 * W)
    if sel.sum() < 3:
        return int(path_idx[len(path_idx) // 3]), "fallback_third"
    Q = P[sel]
    q0 = Q.mean(0)
    u, sv, vt = np.linalg.svd(Q - q0)
    d = vt[0]
    if d[0] * (P[-1, 0] - P[0, 0]) < 0 and abs(d[0]) > 0.2:   # point outward
        d = -d
    dist = np.abs(_dist_to_line(P, q0, d))
    delta = 0.012 * H
    start = int(np.argmax(sel))
    over = np.nonzero((dist > delta) & (np.arange(len(P)) > start))[0]
    # require persistent departure
    for k in over:
        if np.all(dist[k:k + 6] > delta * 0.9):
            j = k
            while j > start and dist[j] > 0.5 * delta:
                j -= 1
            return int(path_idx[j]), "line_departure"
    return int(path_idx[len(path_idx) // 2]), "fallback_mid"


def _sleeve_corners(c, i_s, i_a, forward: bool, H):
    """Sleeve geometry from the contour path shoulder point -> armpit. The path is a U: upper edge, cuff edge, lower
    edge. Cuff corners = the two sharpest CONVEX turns on the path (>= 35 deg over +-5 contour points); none -> sleeveless (returns None).
    The sleeve axis is perpendicular to the cuff edge; the sleeve width is measured across it."""
    idx = _arc(c, i_s, i_a) if forward else _arc(c, i_a, i_s)[::-1]
    Q = c[idx]
    n = len(Q)
    S, A = Q[0], Q[-1]
    k = 5
    if n < 3 * k:
        return ("one_peak", 0.0)
    a_ = Q[k:-k] - Q[:-2 * k]
    b_ = Q[2 * k:] - Q[k:-k]
    turn = np.degrees(np.arctan2(a_[:, 0] * b_[:, 1] - a_[:, 1] * b_[:, 0], (a_ * b_).sum(1)))
    # convex sign of the whole contour: sum of turns around the closed contour
    full_a = c - np.roll(c, k, axis=0)
    full_b = np.roll(c, -k, axis=0) - c
    sgn = np.sign(np.degrees(np.arctan2(full_a[:, 0] * full_b[:, 1] - full_a[:, 1] * full_b[:, 0], (full_a * full_b).sum(1))).sum())
    conv = turn * sgn
    order = np.argsort(-conv)
    picks = []
    for j in order:
        if conv[j] < 30.0 or len(picks) >= 2:
            break
        if all(abs(j - q) >= 5 for q in picks):
            picks.append(int(j))
    if len(picks) < 2:
        return ("one_peak", float(conv.max()) if len(conv) else 0.0)
    ka, kb = sorted(p + k for p in picks)
    Cu, Cl = Q[ka], Q[kb]
    cuff_vec = Cl - Cu
    cw = float(np.hypot(*cuff_vec))
    if cw < 1e-6:
        return ("one_peak", 0.0)
    chat = cuff_vec / cw
    a = np.array([-chat[1], chat[0]])
    Cm = 0.5 * (Cu + Cl)
    if a @ (0.5 * (S + A) - Cm) < 0:
        a = -a
    u = (Q - Cm) @ a
    v = (Q - Cm) @ chat
    umax = float(u.max())
    out = {"axis": a.tolist(), "cuff_upper": Cu.tolist(), "cuff_lower": Cl.tolist(), "cuff_width": cw,
           "chord_len": float(np.hypot(*(S - A))), "axis_extent": umax}
    out["length"] = float(0.5 * (np.hypot(*(S - Cu)) + np.hypot(*(A - Cl))))
    out["length_upper_edge"] = float(np.hypot(*(S - Cu)))
    w1 = (u >= 0.55 * umax) & (u <= 0.80 * umax)
    out["bicep_band"] = float(v[w1].max() - v[w1].min()) if w1.sum() >= 2 else out["chord_len"]
    out["method"] = "two_cuff_corners"
    return out


def _sleeve_tip(c, i_s, i_a, forward: bool, H, peak_deg: float):
    """Fallback for a rounded cuff (one turn only): axis from the armhole-chord midpoint to the tip (farthest path point)."""
    idx = _arc(c, i_s, i_a) if forward else _arc(c, i_a, i_s)[::-1]
    Q = c[idx]
    S, A = Q[0], Q[-1]
    M = 0.5 * (S + A)
    dM = np.sqrt(((Q - M) ** 2).sum(1))
    T = Q[int(np.argmax(dM))]
    axis = T - M
    L = float(np.hypot(*axis))
    if L < 1e-6:
        return None
    a = axis / L
    nrm = np.array([-a[1], a[0]])
    u = (Q - M) @ a
    v = (Q - M) @ nrm
    umax = float(u.max())
    band = u >= 0.88 * umax
    bi = np.nonzero(band)[0]
    if len(bi) < 2:
        bi = np.nonzero(u >= 0.75 * umax)[0]
    ka, kb = sorted([int(bi[int(np.argmin(v[bi]))]), int(bi[int(np.argmax(v[bi]))])])
    Cu, Cl = Q[ka], Q[kb]
    out = {"axis": a.tolist(), "cuff_upper": Cu.tolist(), "cuff_lower": Cl.tolist(),
           "cuff_width": float(np.hypot(*(Cu - Cl))), "chord_len": float(np.hypot(*(S - A))), "axis_extent": umax,
           "length": float(0.5 * (np.hypot(*(S - Cu)) + np.hypot(*(A - Cl)))),
           "length_upper_edge": float(np.hypot(*(S - Cu)))}
    w1 = (u >= 0.15 * umax) & (u <= 0.35 * umax)
    out["bicep_band"] = float(v[w1].max() - v[w1].min()) if w1.sum() >= 2 else out["chord_len"]
    out["method"] = "tip_axis"
    return out


def _edge_departure(P: np.ndarray, H: float, delta_frac: float = 0.015):
    """P: path from a sleeve root (S or A) towards the cuff. Fit a line to its 15-55 % arc-length part, return
    (index where the contour leaves that line, (point, direction) of the line)."""
    seg = np.sqrt((np.diff(P, axis=0) ** 2).sum(1))
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    if L < 1e-6 or len(P) < 8:
        return len(P) - 1, None
    sel = (s >= 0.15 * L) & (s <= 0.55 * L)
    if sel.sum() < 3:
        return len(P) - 1, None
    Q = P[sel]
    q0 = Q.mean(0)
    d = np.linalg.svd(Q - q0)[2][0]
    dist = np.abs(_dist_to_line(P, q0, d))
    delta = delta_frac * H
    start = int(np.argmax(sel))
    for k in range(start, len(P)):
        if dist[k] > delta and np.all(dist[k:k + 5] > 0.9 * delta):
            j = k
            while j > start and dist[j] > 0.6 * delta:
                j -= 1
            return j, (q0, d)
    return len(P) - 1, (q0, d)


def _sleeve_edges(c, i_s, i_a, forward: bool, H):
    """Sleeve from the two straight edges: upper edge leaves the shoulder point S, lower edge leaves the armpit A; the
    cuff corners are where the contour departs from those lines. Works for angled (T-shirt) and hanging (long) sleeves.
    bicep = perpendicular distance of A to the upper-edge line (sleeve width across the axis at the armpit)."""
    idx = _arc(c, i_s, i_a) if forward else _arc(c, i_a, i_s)[::-1]
    Q = c[idx]
    S, A = Q[0], Q[-1]
    M = 0.5 * (S + A)
    kT = int(np.argmax(np.sqrt(((Q - M) ** 2).sum(1))))
    if kT < 8 or len(Q) - kT < 8:
        return None
    up = Q[:kT + 1]
    lo = Q[kT:][::-1]
    ju, line_u = _edge_departure(up, H)
    jl, line_l = _edge_departure(lo, H)
    Cu, Cl = up[ju], lo[jl]
    cw = float(np.hypot(*(Cu - Cl)))
    if cw < 1e-6 or line_u is None:
        return None
    bic = float(abs(_dist_to_line(A[None, :], line_u[0], line_u[1])[0]))
    out = {"cuff_upper": Cu.tolist(), "cuff_lower": Cl.tolist(), "cuff_width": cw,
           "chord_len": float(np.hypot(*(S - A))), "bicep_band": bic,
           "length": float(0.5 * (np.hypot(*(S - Cu)) + np.hypot(*(A - Cl)))),
           "length_upper_edge": float(np.hypot(*(S - Cu))), "axis_extent": float(np.hypot(*(Cu - S))), "method": "edge_departure"}
    return out


def _sleeve(c, i_s, i_a, forward: bool, H):
    """Sleeve geometry for one side, or None (no sleeve: tank top, strap)."""
    r = _sleeve_corners(c, i_s, i_a, forward, H)
    if isinstance(r, dict):
        peak = 99.0
    else:
        peak = r[1]
    if peak < 25.0:               # no convex turn at all on the path: armhole curve only
        return None
    out = _sleeve_edges(c, i_s, i_a, forward, H)
    if out is None:
        out = r if isinstance(r, dict) else _sleeve_tip(c, i_s, i_a, forward, H, peak)
    if out is None or out["axis_extent"] < 0.03 * H:
        return None
    return out


def _classify_sleeve(r: float) -> str:
    for name, hi in SLEEVE_BREAKS:
        if r < hi:
            return name
    return "long"


def _pt(p, scale, ox=0.0, oy=0.0):
    return [round(float(p[0]) / scale + ox, 2), round(float(p[1]) / scale + oy, 2)]


# --------------------------------------------------------------------------- main API
def analyze_shape(mask, name: Optional[str] = None) -> dict:
    """Garment shape attributes from a binary mask. Never raises: returns {'ok': False, 'error': ...} on failure."""
    try:
        return _analyze(mask, name)
    except Exception as e:  # pragma: no cover - robust fallback
        return {"ok": False, "name": name, "error": f"{type(e).__name__}: {e}"}


def _analyze(mask, name):
    m0 = _binary(mask)
    h0, w0 = m0.shape
    wm, c, scale, bbox = clean_outline(m0)
    ys, xs = np.nonzero(wm)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    W, H = x1 - x0 + 1, y1 - y0 + 1
    flags = []
    border = {"top": bool(bbox[1] <= 1), "left": bool(bbox[0] <= 1), "right": bool(bbox[2] >= w0 - 2), "bottom": bool(bbox[3] >= h0 - 2)}
    if any(border.values()):
        flags.append("touches_image_border:" + ",".join(k for k, v in border.items() if v))

    iL, iR, m_arm = _find_armpits(wm, c, W, H, x0, y0)
    A_L, A_R = c[iL], c[iR]
    cx = 0.5 * (A_L[0] + A_R[0])
    if abs(A_L[1] - A_R[1]) > 0.15 * H:
        flags.append("armpit_height_asymmetric")

    (xnl, ynl), (xnr, ynr), (xd, yd), nd, fullness = _neck(wm, c, A_L[0], A_R[0], W, H, cx)
    iNL = _nearest_idx(c, (xnl, ynl), _arc(c, 0, iL))      # left neck point lies before the left armpit
    iNR = _nearest_idx(c, (xnr, ynr), _arc(c, iR, len(c) - 1))
    # left outward path: forward from iNL to iL ; right outward path: backward from iNR to iR
    pathL = _arc(c, iNL, iL)
    pathR = _arc(c, iR, iNR)[::-1]
    iSL, m_sh = _shoulder_point(c, pathL, W, H)
    iSR, m_sh2 = _shoulder_point(c, pathR, W, H)
    S_L, S_R = c[iSL], c[iSR]
    N_L, N_R = c[iNL], c[iNR]

    slv_L = _sleeve(c, iSL, iL, True, H)
    slv_R = _sleeve(c, iSR, iR, False, H)

    # hem: body contour between the armpits via the bottom
    body = c[_arc(c, iL, iR)]
    y_bot = float(body[:, 1].max())
    band = body[:, 1] >= y_bot - 0.05 * H
    bl = body[band & (body[:, 0] < cx)]
    br = body[band & (body[:, 0] >= cx)]
    if len(bl) == 0 or len(br) == 0:
        bl, br = body[body[:, 0] < cx], body[body[:, 0] >= cx]
    hem_L = bl[int(np.argmin(bl[:, 0]))]
    hem_R = br[int(np.argmax(br[:, 0]))]
    hem_width = float(hem_R[0] - hem_L[0])
    chest_width = float(abs(A_R[0] - A_L[0]))
    neck_y = 0.5 * (N_L[1] + N_R[1])
    garment_len = float(y_bot - neck_y)
    shoulder_w = float(np.hypot(*(S_R - S_L)))
    neck_w = float(np.hypot(*(N_R - N_L)))
    # hem sanity
    if hem_width <= 0 or garment_len <= 0:
        flags.append("degenerate_body")

    sl = [s for s in (slv_L, slv_R) if s is not None]
    len_r = [s["length"] / garment_len for s in sl] if sl else [0.0]
    sleeve_len_ratio = float(np.mean(len_r))
    sleeve_cls = _classify_sleeve(sleeve_len_ratio)
    if len(sl) == 2 and abs(len_r[0] - len_r[1]) > 0.25:
        flags.append("sleeves_unequal")
    cuff_w = [s["cuff_width"] for s in sl]
    bic_chord = [s["chord_len"] for s in sl]
    bic_band = [s["bicep_band"] for s in sl]
    wrist_to_bicep = float(np.mean(cuff_w) / np.mean(bic_chord)) if sl and np.mean(bic_chord) > 0 else None
    wrist_to_bicep_band = float(np.mean(cuff_w) / np.mean(bic_band)) if sl and np.mean(bic_band) > 0 else None

    drop = []
    for N, S, A in ((N_L, S_L, A_L), (N_R, S_R, A_R)):
        den = max(A[1] - N[1], 1e-6)
        drop.append(float((S[1] - N[1]) / den))
    shoulder_drop = float(np.mean(drop))
    slope = []
    for N, S in ((N_L, S_L), (N_R, S_R)):
        slope.append(math.degrees(math.atan2(S[1] - N[1], max(abs(S[0] - N[0]), 1e-6))))
    chest_to_len = chest_width / garment_len if garment_len > 0 else None
    bbox_aspect = W / float(H)
    neck_depth_ratio = nd / garment_len if garment_len > 0 else None
    if nd < 0.02 * H:
        neck_shape = "flat"
    else:
        neck_shape = "v" if fullness < 0.62 else "round"

    fit = {
        "chest_to_length": _r(chest_to_len),
        "shoulder_to_chest": _r(shoulder_w / chest_width if chest_width > 0 else None),
        "bbox_width_to_height": _r(bbox_aspect),
        "shoulder_drop_frac": _r(shoulder_drop),
        "shoulder_slope_deg": _r(float(np.mean(slope))),
        "dropped_shoulder": bool(shoulder_drop > 0.45),
    }

    # Hough cross-check of the hem
    hough = hough_outline_lines(wm)
    hem_h = hough.get("hem")
    res = {
        "ok": True, "name": name,
        "image_size_hw": [int(h0), int(w0)], "bbox_xyxy": [int(v) for v in bbox], "work_scale": round(scale, 5),
        "borders_touched": border, "flags": flags,
        "methods": {"armpit": m_arm, "shoulder_left": m_sh, "shoulder_right": m_sh2},
        "landmarks": {},
        "lengths_px": {},
        "ratios": {},
        "sleeve": {"class": sleeve_cls, "length_over_garment_length": _r(sleeve_len_ratio),
                   "left": _sleeve_out(slv_L, scale, bbox, garment_len), "right": _sleeve_out(slv_R, scale, bbox, garment_len)},
        "neckline": {"depth_px": _r(nd / scale), "depth_over_garment_length": _r(neck_depth_ratio),
                     "width_px": _r(neck_w / scale), "width_over_shoulder": _r(neck_w / shoulder_w if shoulder_w > 0 else None),
                     "shape": neck_shape, "notch_fullness": _r(fullness)},
        "fit": fit,
        "hough": {"hem_width_px": _r(hem_h["width"] / scale) if hem_h else None,
                  "n_lines": hough.get("n_lines"), "n_vertical": hough.get("n_vertical")},
    }
    ox, oy = bbox[0] - 0.0, bbox[1] - 0.0
    # work coords are relative to the work-image origin (0,0) after scaling the FULL mask? No:
    # wm is the full mask scaled by `scale` (no crop), so input coords = work / scale.
    lm = {"neck_left": N_L, "neck_right": N_R, "neck_dip": np.array([xd, yd]), "shoulder_left": S_L,
          "shoulder_right": S_R, "armpit_left": A_L, "armpit_right": A_R, "hem_left": hem_L, "hem_right": hem_R}
    if slv_L:
        lm["cuff_left_upper"], lm["cuff_left_lower"] = np.array(slv_L["cuff_upper"]), np.array(slv_L["cuff_lower"])
    if slv_R:
        lm["cuff_right_upper"], lm["cuff_right_lower"] = np.array(slv_R["cuff_upper"]), np.array(slv_R["cuff_lower"])
    res["landmarks"] = {k: _pt(v, scale) for k, v in lm.items()}
    res["lengths_px"] = {k: _r(v / scale) for k, v in {
        "garment_length": garment_len, "chest_width": chest_width, "hem_width": hem_width, "shoulder_width": shoulder_w,
        "sleeve_length_mean": float(np.mean([s["length"] for s in sl])) if sl else 0.0,
        "cuff_width_mean": float(np.mean(cuff_w)) if sl else 0.0,
        "bicep_chord_mean": float(np.mean(bic_chord)) if sl else 0.0,
        "bicep_band_mean": float(np.mean(bic_band)) if sl else 0.0}.items()}
    res["ratios"] = {
        "hem_to_chest": _r(hem_width / chest_width if chest_width > 0 else None),
        "sleeve_to_body_length": _r(sleeve_len_ratio),
        "wrist_to_bicep": _r(wrist_to_bicep),
        "wrist_to_bicep_band": _r(wrist_to_bicep_band),
        "chest_to_length": _r(chest_to_len),
        "length_to_chest": _r(garment_len / chest_width if chest_width > 0 else None),
        "shoulder_to_chest": _r(shoulder_w / chest_width if chest_width > 0 else None),
        "neck_depth_to_length": _r(neck_depth_ratio),
        "hem_to_chest_hough": _r(hem_h["width"] / chest_width if (hem_h and chest_width > 0) else None),
    }
    return res


def _r(v, nd=4):
    return None if v is None else round(float(v), nd)


def _sleeve_out(s, scale, bbox, glen):
    if s is None:
        return None
    return {"length_px": _r(s["length"] / scale), "cuff_width_px": _r(s["cuff_width"] / scale),
            "bicep_chord_px": _r(s["chord_len"] / scale), "bicep_band_px": _r(s["bicep_band"] / scale),
            "length_over_garment_length": _r(s["length"] / glen) if glen > 0 else None}


# --------------------------------------------------------------------------- Hough lines on the outline
def hough_outline_lines(wm: np.ndarray) -> dict:
    """Probabilistic Hough on the one-pixel outline of a WORK-size mask. Returns near-horizontal bottom
    line (hem) and counts. Lines are [x1,y1,x2,y2] in the mask's own pixel frame."""
    m = (np.asarray(wm) > 0).astype(np.uint8)
    H = int(np.nonzero(m.any(1))[0].ptp() + 1)
    edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) * 255
    lines = cv2.HoughLinesP(edge, 1, np.pi / 180, threshold=max(20, int(0.05 * H)),
                            minLineLength=max(15, int(0.08 * H)), maxLineGap=max(3, int(0.012 * H)))
    out = {"lines": [], "hem": None, "n_lines": 0, "n_vertical": 0}
    if lines is None:
        return out
    ys = np.nonzero(m.any(1))[0]
    ybot = ys.max()
    hem, best = None, 0.0
    hl = []
    nv = 0
    for x1, y1, x2, y2 in lines[:, 0, :]:
        ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        ang = min(ang, 180 - ang)
        ln = float(math.hypot(x2 - x1, y2 - y1))
        out["lines"].append([int(x1), int(y1), int(x2), int(y2)])
        if ang > 75:
            nv += 1
        if ang < 10 and max(y1, y2) > ybot - 0.10 * H:
            hl.append((min(x1, x2), max(x1, x2), y1, y2))
            if ln > best:
                best = ln
    if hl:   # union extent of all near-horizontal bottom segments = hem width
        xa, xb = min(h[0] for h in hl), max(h[1] for h in hl)
        ya = float(np.mean([0.5 * (h[2] + h[3]) for h in hl]))
        hem = {"line": [int(xa), int(ya), int(xb), int(ya)], "width": float(xb - xa)}
    out.update({"hem": hem, "n_lines": len(lines), "n_vertical": nv})
    return out


# --------------------------------------------------------------------------- corner / keypoint detectors
DETECTORS = ["harris", "shi_tomasi", "hessian", "fast", "orb", "sift", "akaze"]


def detect_keypoints(gray: np.ndarray, method: str, region: Optional[np.ndarray] = None, n: int = 150,
                     min_dist: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """Run one corner / keypoint detector; return (xy (k,2) float, strength (k,)) of at most n strongest points.
    `region` is an optional uint8 mask (non-zero = search here). `gray` uint8 or float."""
    from skimage.feature import corner_peaks, hessian_matrix, hessian_matrix_det
    g8 = gray if gray.dtype == np.uint8 else np.clip(gray, 0, 255).astype(np.uint8)
    reg = None if region is None else (region > 0).astype(np.uint8) * 255
    if method == "harris":
        r = cv2.cornerHarris(np.float32(g8), 3, 3, 0.04)
        pk = corner_peaks(r, min_distance=min_dist, threshold_rel=0.01, num_peaks=n * 3, exclude_border=False)
        pts = pk[:, ::-1].astype(float)
        st = r[pk[:, 0], pk[:, 1]] if len(pk) else np.zeros(0)
    elif method == "hessian":
        det = hessian_matrix_det(np.float32(g8), sigma=2.0)
        det = np.abs(det)
        pk = corner_peaks(det, min_distance=min_dist, threshold_rel=0.01, num_peaks=n * 3, exclude_border=False)
        pts = pk[:, ::-1].astype(float)
        st = det[pk[:, 0], pk[:, 1]] if len(pk) else np.zeros(0)
    elif method == "shi_tomasi":
        p = cv2.goodFeaturesToTrack(g8, maxCorners=n * 3, qualityLevel=0.01, minDistance=min_dist, blockSize=3)
        pts = p[:, 0, :].astype(float) if p is not None else np.zeros((0, 2))
        eig = cv2.cornerMinEigenVal(g8, 3)
        st = eig[pts[:, 1].astype(int), pts[:, 0].astype(int)] if len(pts) else np.zeros(0)
    else:
        if method == "fast":
            d = cv2.FastFeatureDetector_create(threshold=20, nonmaxSuppression=True)
        elif method == "orb":
            d = cv2.ORB_create(nfeatures=n, fastThreshold=10, edgeThreshold=8, patchSize=15)
        elif method == "sift":
            d = cv2.SIFT_create(nfeatures=n)
        elif method == "akaze":
            d = cv2.AKAZE_create()
        else:
            raise ValueError(method)
        kp = d.detect(g8, reg)
        pts = np.array([k.pt for k in kp], float).reshape(-1, 2)
        st = np.array([k.response for k in kp], float)
    if reg is not None and len(pts):
        xi = np.clip(pts[:, 0].round().astype(int), 0, reg.shape[1] - 1)
        yi = np.clip(pts[:, 1].round().astype(int), 0, reg.shape[0] - 1)
        keep = reg[yi, xi] > 0
        pts, st = pts[keep], st[keep]
    o = np.argsort(-st)[:n]
    return pts[o], st[o]


def contour_curvature_points(c: np.ndarray, n: int = 40, k: int = 12, min_turn_deg: float = 25.0,
                             min_sep: int = 15) -> Tuple[np.ndarray, np.ndarray]:
    """Turning angle (deg) at every contour point using chords +-k points away; greedy non-max suppression."""
    N = len(c)
    a = c - np.roll(c, k, axis=0)
    b = np.roll(c, -k, axis=0) - c
    ang = np.degrees(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1)))
    mag = np.abs(ang)
    order = np.argsort(-mag)
    chosen = []
    for i in order:
        if mag[i] < min_turn_deg or len(chosen) >= n:
            break
        if all(min(abs(i - j), N - abs(i - j)) >= min_sep for j in chosen):
            chosen.append(int(i))
    return c[chosen], mag[chosen]


# --------------------------------------------------------------------------- drawing
_COL = {"neck": (0, 200, 255), "shoulder": (0, 0, 255), "armpit": (255, 0, 255), "cuff": (0, 160, 0), "hem": (255, 128, 0)}


def draw_overlay(image_bgr: np.ndarray, res: dict, thickness: Optional[int] = None) -> np.ndarray:
    """Draw outline-independent landmarks and measured lines on a copy of the image (input pixel coords)."""
    im = image_bgr.copy()
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if not res.get("ok"):
        cv2.putText(im, "FAILED " + str(res.get("error", ""))[:40], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return im
    s = thickness or max(1, int(round(min(im.shape[:2]) / 250)))
    L = {k: tuple(int(round(v)) for v in p) for k, p in res["landmarks"].items()}

    def line(a, b, col):
        if a in L and b in L:
            cv2.line(im, L[a], L[b], col, s, cv2.LINE_AA)
    line("hem_left", "hem_right", _COL["hem"])
    line("armpit_left", "armpit_right", _COL["armpit"])
    line("shoulder_left", "shoulder_right", _COL["shoulder"])
    line("neck_left", "neck_dip", _COL["neck"]); line("neck_dip", "neck_right", _COL["neck"])
    line("shoulder_left", "cuff_left_upper", _COL["cuff"]); line("armpit_left", "cuff_left_lower", _COL["cuff"])
    line("cuff_left_upper", "cuff_left_lower", (0, 255, 0))
    line("shoulder_right", "cuff_right_upper", _COL["cuff"]); line("armpit_right", "cuff_right_lower", _COL["cuff"])
    line("cuff_right_upper", "cuff_right_lower", (0, 255, 0))
    for k, p in L.items():
        key = next(t for t in _COL if k.startswith(t))
        cv2.circle(im, p, s * 3, _COL[key], -1, cv2.LINE_AA)
        cv2.circle(im, p, s * 3, (255, 255, 255), 1, cv2.LINE_AA)
    txt = f"{res['sleeve']['class']}  sl/len={res['sleeve']['length_over_garment_length']}  hem/chest={res['ratios']['hem_to_chest']}"
    fs = max(0.4, im.shape[1] / 900)
    cv2.putText(im, txt, (6, int(22 * fs + 6)), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.7, (0, 0, 0), s + 2, cv2.LINE_AA)
    cv2.putText(im, txt, (6, int(22 * fs + 6)), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.7, (255, 255, 255), s, cv2.LINE_AA)
    return im


# --------------------------------------------------------------------------- convenience API for other plans (P19 panel maps)
def garment_landmarks(mask, name: Optional[str] = None) -> dict:
    """Main entry point for other plans. mask: binary garment mask (uint8 0/255 or bool), upright, ideally flat front/back.

    Returns a JSON-serialisable dict (same as analyze_shape) plus convenient keys:
      ok            : bool (False -> only 'error' is meaningful)
      landmarks     : {name: [x, y]} in INPUT mask pixel coordinates; names in LANDMARK_NAMES
                      (cuff_* are absent for a sleeveless garment). 'left'/'right' are IMAGE left/right.
      sleeve_class  : 'sleeveless' | 'short' | 'elbow' | 'three_quarter' | 'long'
      ratios        : scale-free ratios (hem_to_chest, sleeve_to_body_length, chest_to_length, shoulder_to_chest, ...)
      polygons      : {'torso': [[x,y],...], 'sleeve_left': [...], 'sleeve_right': [...]} regions built from the landmarks
                      (sleeve polygons empty for sleeveless garments); intersect with the mask to get panel pixels
      flags         : warnings (e.g. 'touches_image_border:top', 'armpit_height_asymmetric')
    Quality: reliable for flat, front or back product photos of short-sleeve tops (see out/p06_shape/REPORT).
    On-person photos: arms and pose distort the outline; treat the result as approximate."""
    res = analyze_shape(mask, name)
    if not res.get("ok"):
        return res
    lm = res["landmarks"]
    g = lambda k: lm.get(k)
    torso = [g(k) for k in ("neck_left", "neck_dip", "neck_right", "shoulder_right", "armpit_right", "hem_right", "hem_left", "armpit_left", "shoulder_left")]
    res["polygons"] = {
        "torso": [p for p in torso if p is not None],
        "sleeve_left": [p for p in (g("shoulder_left"), g("cuff_left_upper"), g("cuff_left_lower"), g("armpit_left")) if p is not None] if g("cuff_left_upper") else [],
        "sleeve_right": [p for p in (g("shoulder_right"), g("cuff_right_upper"), g("cuff_right_lower"), g("armpit_right")) if p is not None] if g("cuff_right_upper") else [],
    }
    res["sleeve_class"] = res["sleeve"]["class"]
    return res
