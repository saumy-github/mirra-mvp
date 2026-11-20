"""P18: texture check - project panel textures back onto the photo and compare.

For every photo that fed a panel: each photo pixel inside the garment mask is looked up in the
panel texture that it was mapped to (inverse of the warp), giving a re-projected photo.  We then
compare it with the real photo inside the garment mask:

  * mean / median / 95th percentile CIEDE2000 (deltaE00), overall and per colour region
    (k-means regions of the photo, seed 0),
  * SSIM of the grey images inside the mask (eroded 3 px),
  * covered share: garment pixels that land on opaque, photo-derived panel pixels,
  * silhouette IoU: the photo region warped onto the panel versus the panel polygon.

Caveat (honest): v1 re-projects with the inverse of the SAME landmark warp it was cut with, so the
numbers measure what is lost by resampling / filling / the panel clip, plus how well the region
outline fits the panel outline (silhouette IoU) - not whether the landmarks are right.
v0 is re-projected through its own bounding-box homography in the same way.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import structural_similarity

SEED = 0


# ----------------------------------------------------------------------------- helpers
def _load_rgba(path):
    from PIL import Image
    return np.array(Image.open(path).convert("RGBA"))


def _inverse_maps(src, dst, w, h, tex_w, tex_h, step=8):
    """Maps for cv2.remap that give, for each photo pixel (w x h), the panel texture coordinates."""
    rbf = RBFInterpolator(np.asarray(src, float), np.asarray(dst, float), kernel="thin_plate_spline", smoothing=10.0)
    gx = np.arange(0, w // step + 2) * step
    gy = np.arange(0, h // step + 2) * step
    G = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2).astype(float)
    S = rbf(G).reshape(len(gy), len(gx), 2).astype(np.float32)
    ix = (np.arange(w, dtype=np.float32) / step)[None, :].repeat(h, 0)
    iy = (np.arange(h, dtype=np.float32) / step)[:, None].repeat(w, 1)
    return cv2.remap(S[:, :, 0], ix, iy, cv2.INTER_LINEAR), cv2.remap(S[:, :, 1], ix, iy, cv2.INTER_LINEAR)


def _lookup(tex_rgba, mx, my, region, photo_valid=None):
    """Re-project: sample tex at (mx, my) for pixels in region. Returns rgb, ok-mask."""
    h, w = region.shape
    rgb = cv2.remap(np.ascontiguousarray(tex_rgba[:, :, :3]), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a = cv2.remap(tex_rgba[:, :, 3], mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    ok = region & (a > 127)
    return rgb, ok


def _splat(tex_rgba, mx, my, valid, region):
    """Exact re-projection by forward splatting: every valid (photo-derived) panel pixel is written to the
    photo pixel it was cut from (mx, my = panel -> photo maps); photo pixels hit several times are averaged.
    Returns rgb, ok (photo pixels in `region` that received data; <=2 px gaps are closed)."""
    H, W = region.shape
    xi = np.rint(mx[valid]).astype(np.int64); yi = np.rint(my[valid]).astype(np.int64)
    inb = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
    idx = (yi * W + xi)[inb]
    col = tex_rgba[:, :, :3][valid][inb].astype(np.float64)
    cnt = np.bincount(idx, minlength=H * W).astype(np.float64)
    acc = np.stack([np.bincount(idx, weights=col[:, c], minlength=H * W) for c in range(3)], 1)
    hit = cnt > 0
    rgb = np.zeros((H * W, 3), np.float64)
    rgb[hit] = acc[hit] / cnt[hit, None]
    rgb = rgb.reshape(H, W, 3).astype(np.uint8)
    hit = hit.reshape(H, W)
    # close sub-pixel gaps (panel coarser than the photo) from the nearest hit within 2 px
    gaps = region & ~hit
    if gaps.any() and hit.any():
        from scipy import ndimage as ndi
        dist, (iy, ix) = ndi.distance_transform_edt(~hit, return_indices=True)
        near = gaps & (dist <= 2.0)
        rgb[near] = rgb[iy[near], ix[near]]
        hit = hit | near
    return rgb, region & hit


def _de00(a_rgb, b_rgb, sel):
    la = rgb2lab(a_rgb[sel].reshape(-1, 1, 3).astype(np.float32) / 255.0)
    lb = rgb2lab(b_rgb[sel].reshape(-1, 1, 3).astype(np.float32) / 255.0)
    out = np.empty(len(la), np.float32)
    for i in range(0, len(la), 200000):
        out[i:i + 200000] = deltaE_ciede2000(la[i:i + 200000], lb[i:i + 200000])[:, 0]
    return out


def colour_regions(rgb, mask, k=4):
    """k-means colour regions of the photo inside the mask (small working size). Returns label map (-1 outside) and centres (RGB)."""
    h, w = mask.shape
    s = min(1.0, 256.0 / max(h, w))
    small = cv2.resize(rgb, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    sm = cv2.resize(mask.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    pts = lab[sm]
    if len(pts) < k * 20:
        return np.where(mask, 0, -1), np.array([rgb[mask].mean(0)])
    cv2.setRNGSeed(SEED)
    _, _, cen = cv2.kmeans(pts, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    lab_full = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    d = ((lab_full[:, :, None, :] - cen[None, None]) ** 2).sum(-1)
    lbl = np.where(mask, d.argmin(-1), -1)
    cen_rgb = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    return lbl, cen_rgb


def metrics(ref_rgb, re_rgb, mask, ok):
    """Compare re-projected photo with the photo inside mask & ok."""
    sel = mask & ok
    n_mask = int(mask.sum())
    out = {"garment_px": n_mask, "covered_share": round(float(sel.sum() / max(n_mask, 1)), 4)}
    if sel.sum() < 50:
        out.update(dE_mean=None, dE_median=None, dE_p95=None, ssim=None, regions=[])
        return out
    de = _de00(ref_rgb, re_rgb, sel)
    out.update(dE_mean=round(float(de.mean()), 3), dE_median=round(float(np.median(de)), 3), dE_p95=round(float(np.percentile(de, 95)), 3))
    g1 = cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2GRAY); g2 = cv2.cvtColor(re_rgb, cv2.COLOR_RGB2GRAY)
    _, smap = structural_similarity(g1, g2, win_size=7, data_range=255, full=True)
    er = cv2.erode(sel.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=3) > 0
    out["ssim"] = round(float(smap[er].mean() if er.sum() > 20 else smap[sel].mean()), 4)
    lbl, cen = colour_regions(ref_rgb, mask)
    regs = []
    full_de = np.full(mask.shape, np.nan, np.float32)
    full_de[sel] = de
    for i in range(len(cen)):
        r = (lbl == i) & sel
        if r.sum() < 30:
            continue
        regs.append({"colour": "#%02x%02x%02x" % tuple(int(v) for v in cen[i]),
                     "share": round(float((lbl == i).sum() / max(n_mask, 1)), 4),
                     "dE_mean": round(float(np.nanmean(full_de[r])), 3)})
    out["regions"] = sorted(regs, key=lambda d: -d["share"])
    out["_dE_map"] = full_de
    return out


# ----------------------------------------------------------------------------- v1
def reproject_v1(result):
    """{view: dict(ref, mask, recon, ok, torso_iou...)} for each photo that fed panels in a v1 result."""
    out = {}
    warps = result.warps
    views = {}
    for piece, w in warps.items():
        if w["kind"] == "body" and w["photo_view"] == w["view"].view and ("back" in piece) == (w["view"].view == "back"):
            views[w["view"].view] = w["view"]
    for vn, v in views.items():
        H, W = v.mask.shape
        recon = np.zeros_like(v.rgb); ok = np.zeros((H, W), bool)
        sil = {}
        for piece, w in warps.items():
            tex = _load_rgba(result.textures[piece])
            th, tw = tex.shape[:2]
            if w["kind"] == "body" and w["view"] is v and ("back" in piece) == (vn == "back") and w["photo_view"] == vn:
                r = w["res"]
                rgb, o = _splat(tex, r["mx"], r["my"], r["valid"], v.reg["torso"])
                recon[o] = rgb[o]; ok |= o
                # silhouette IoU: torso region warped onto panel canvas vs panel polygon
                warped = cv2.remap(v.reg["torso"].astype(np.float32), r["mx"], r["my"], cv2.INTER_LINEAR, borderValue=0) > 0.5
                pm = r["pm"]
                sil[piece] = round(float((warped & pm).sum() / max((warped | pm).sum(), 1)), 4)
            elif w["kind"] == "sleeve":
                for hn, hh in w["halves"].items():
                    if hh["side"] is None or w["halves"][hn]["tex"] is None:
                        continue
                    if hn != vn:
                        continue
                    rgb, o = _splat(tex, hh["mx"], hh["my"], hh["valid"], v.reg["sleeve_" + hh["side"]])
                    recon[o] = rgb[o]; ok |= o
                    warped = cv2.remap(v.reg["sleeve_" + hh["side"]].astype(np.float32), hh["mx"], hh["my"], cv2.INTER_LINEAR, borderValue=0) > 0.5
                    half = hh["half"] & hh["pm"]
                    sil[piece] = round(float((warped & half).sum() / max((warped | half).sum(), 1)), 4)
        out[vn] = dict(ref=v.rgb, mask=v.mask, recon=recon, ok=ok, sil_iou=sil)
    return out


# ----------------------------------------------------------------------------- v0
def reproject_v0(photo_rgb, mask, layouts, textures_dir, ppc=10.0):
    """Re-project v0 textures (bbox homography; front panel = whole garment, sleeves = left/right 35 %)."""
    from pathlib import Path
    try:
        from .step_06_0_texture_projection import TextureProjector
    except ImportError:
        from step_06_0_texture_projection import TextureProjector
    tp = TextureProjector()
    H, W = mask.shape
    rgba = np.dstack([photo_rgb, mask.astype(np.uint8) * 255])
    gb = tp._garment_bbox(rgba)
    recon = np.zeros_like(photo_rgb); ok = np.zeros((H, W), bool)
    sil = {}
    for piece, region_bbox in (("front_panel", gb), ("sleeve_left", tp._arm_region_bbox(gb, "left")),
                               ("sleeve_right", tp._arm_region_bbox(gb, "right"))):
        tex = _load_rgba(Path(textures_dir) / f"{piece}_texture.png")
        th, tw = tex.shape[:2]
        gx0, gy0, gx1, gy1 = region_bbox
        # homography photo -> texture is a box-to-box scale
        sx, sy = (tw - 1) / max(gx1 - gx0, 1), (th - 1) / max(gy1 - gy0, 1)
        xs, ys = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        mx, my = (xs - gx0) * sx, (ys - gy0) * sy
        inside = mask & (xs >= gx0) & (xs <= gx1) & (ys >= gy0) & (ys <= gy1) & ~ok
        rgb, o = _lookup(tex, mx.astype(np.float32), my.astype(np.float32), inside)
        recon[o] = rgb[o]; ok |= o
        # silhouette IoU: the region of the photo (garment pixels in its bbox) warped to the panel canvas vs the polygon
        reg = (mask & (xs >= gx0) & (xs <= gx1) & (ys >= gy0) & (ys <= gy1)).astype(np.uint8)
        warped = cv2.resize(reg[int(gy0):int(gy1) + 1, int(gx0):int(gx1) + 1], (tw, th), interpolation=cv2.INTER_NEAREST) > 0
        pm = tex[:, :, 3] > 127
        sil[piece] = round(float((warped & pm).sum() / max((warped | pm).sum(), 1)), 4)
    return dict(ref=photo_rgb, mask=mask, recon=recon, ok=ok, sil_iou=sil)


# ----------------------------------------------------------------------------- figures
def error_map_image(ref, mask, dmap, vmax=20.0):
    d = np.nan_to_num(dmap, nan=0.0)
    u8 = np.clip(d / vmax * 255, 0, 255).astype(np.uint8)
    hm = cv2.applyColorMap(u8, cv2.COLORMAP_INFERNO)[:, :, ::-1]
    out = (ref * 0.35).astype(np.uint8)
    sel = mask
    out[sel] = hm[sel]
    return out


def flat_preview(textures_dir_or_paths, layouts, out_path, height=700, bg=(128, 128, 128)):
    """All panels laid out like the pattern (front | back | sleeves), each with its outline."""
    from pathlib import Path
    order = [k for k in ("front_panel", "back_panel", "sleeve_left", "sleeve_right") if k in layouts]
    tiles = []
    for k in order:
        p = Path(textures_dir_or_paths) / f"{k}_texture.png" if not isinstance(textures_dir_or_paths, dict) else textures_dir_or_paths[k]
        t = _load_rgba(p)
        poly = np.array(layouts[k].polygon(n_per_segment=64), float)
        w_cm = poly[:, 0].max() - poly[:, 0].min()
        h_cm = poly[:, 1].max() - poly[:, 1].min()
        s = height / 71.0 * 0.0 + (height / 71.0)           # px per cm of the preview (same for all panels)
        tw, th = int(round(w_cm * s)), int(round(h_cm * s))
        tt = cv2.resize(t, (tw, th), interpolation=cv2.INTER_AREA)
        a = tt[:, :, 3:4] / 255.0
        canvas = np.full((height, tw, 3), bg, np.uint8)
        y0 = height - th if "sleeve" not in k else int(height * 0.5 - th / 2)
        reg = canvas[y0:y0 + th]
        reg[:] = (tt[:, :, :3] * a + reg * (1 - a)).astype(np.uint8)
        pts = np.stack([(poly[:, 0] - poly[:, 0].min()) * s, y0 + (poly[:, 1].max() - poly[:, 1]) * s], 1).astype(np.int32)
        cv2.polylines(canvas, [pts.reshape(-1, 1, 2)], True, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, k, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(np.pad(canvas, ((0, 0), (0, 6), (0, 0)), constant_values=255))
    img = np.hstack(tiles)
    cv2.imwrite(str(out_path), img[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
    return img
