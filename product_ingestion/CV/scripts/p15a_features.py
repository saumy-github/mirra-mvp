"""P15a stage 1: per-image features + IoU of v1 and v1_all, built from the P01 caches (CPU only, no model is loaded).

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_features.py

v1      = SAM 2 mask of the SegFormer TOP box + interior point (P01 cache 'sam2c' box_segtop_pt), cleaned   [P01 name sam2_box_segtop_pt]
v1_all  = SAM 2 mask of the SegFormer ALL box + interior point (cache 'sam2b' box_seglc_pt), minus skin, cleaned [comb_box_seglc_pt_minus_skin]
Writes out/p15a_seg_autoselect/features.csv (one row per image: IoU of v1 / v1_all against the reference + geometric
and quality features used by the selection rules) and per-set mean tables to the console.
IoU = evaluate.mask_metrics on masks downscaled to a longest side of 512 (same as P01); Mirra reference =
out/p00_baseline/reference/<cloth>/garment_mask.png (approximate).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p15a_common import *  # noqa: F401,F403
import cv_segment as cs
import evaluate as ev
import pandas as pd

P15.mkdir(parents=True, exist_ok=True)
LOWER = (6, 9, 10, 12, 13)      # Pants, shoes, legs
TOPC = (4, 7)


def small(m, max_side=512):
    return m


def iou512(pred, gt, max_side=512):
    h, w = gt.shape
    sc = min(1.0, max_side / max(h, w))
    if sc < 1.0:
        sz = (int(round(w * sc)), int(round(h * sc)))
        pred = cv2.resize(cs.to_u8(pred), sz, interpolation=cv2.INTER_NEAREST) > 0
        gt = cv2.resize(cs.to_u8(gt), sz, interpolation=cv2.INTER_NEAREST) > 0
    return ev.mask_metrics(pred > 0, gt > 0)["iou"]


def get_masks(s, i, sp="dev"):
    """v1 / v1_all masks (uint8 0/255) and SAM 2 predicted IoUs. None when the cache has no mask."""
    sg = load(sp, s, i, "segformer")
    sc_ = load(sp, s, i, "sam2c")
    sb = load(sp, s, i, "sam2b")
    lab = sg["labels"]
    m1 = m1a = None
    s1 = sa = None
    if sc_ is not None and "box_segtop_pt_masks" in sc_:
        m1 = cs.clean_mask(sc_["box_segtop_pt_masks"][0])
        s1 = float(sc_["box_segtop_pt_scores"][0])
    if sb is not None and "box_seglc_pt_masks" in sb:
        raw = cs.clean_mask(sb["box_seglc_pt_masks"][0])
        m1a = cs.clean_mask(cs.sam2_minus_skin(sb["box_seglc_pt_masks"][0], lab))
        sa = float(sb["box_seglc_pt_scores"][0])
        # the unfiltered ALL mask (no skin removal)
        m_all_raw = raw
    else:
        m_all_raw = None
    return lab, m1, m1a, s1, sa, m_all_raw


def runs_below(mask_s, mask_t):
    pass


def geom(lab, m1, m1a):
    H, W = lab.shape
    T = np.isin(lab, TOPC)
    S = lab == 5
    Tl = cs.largest_component(cs.to_u8(T)) > 0 if T.any() else T
    Sl = cs.largest_component(cs.to_u8(S)) > 0 if S.any() else S
    f = {"H": H, "W": W}
    n = float(H * W)
    f["top_frac"] = float(Tl.sum() / n)
    f["skirt_frac"] = float(Sl.sum() / n)
    f["skirt_all_frac"] = float(S.sum() / n)
    f["skirt_over_top"] = float(Sl.sum() / max(1, Tl.sum()))
    for nm, cl in (("pants", (6,)), ("legs", (12, 13)), ("shoes", (9, 10)), ("belt", (8,)), ("lower", LOWER), ("arms", (14, 15)),
                   ("face", (11,)), ("hair", (2,)), ("bag", (16,)), ("scarf", (17,))):
        f[f"{nm}_frac"] = float(np.isin(lab, cl).sum() / n)
    f["bg_frac"] = float((lab == 0).sum() / n)
    # geometry of skirt vs top
    f["contact_len"] = 0.0
    f["contact_ratio"] = 0.0
    f["width_ratio"] = 0.0
    f["skirt_below"] = 0.0
    f["skirt_bottom_gap"] = 1.0
    f["skirt_top_gap"] = 1.0
    f["lower_below_skirt"] = 0.0
    f["lower_in_between"] = 0.0
    f["narrow_ratio"] = 1.0
    if Sl.any() and Tl.any():
        ys_s, xs_s = np.nonzero(Sl)
        ys_t, xs_t = np.nonzero(Tl)
        f["skirt_below"] = float(ys_s.mean() > ys_t.mean())
        f["skirt_bottom_gap"] = float((H - 1 - ys_s.max()) / H)    # 0 = skirt reaches image bottom
        f["skirt_top_gap"] = float((ys_s.min() - ys_t.max()) / H)  # < 0 skirt starts above top's bottom (overlap in y)
        # contact: skirt pixels within 4 px of top pixels
        k = np.ones((9, 9), np.uint8)
        dt = cv2.dilate(cs.to_u8(Tl), k) > 0
        contact = (dt & Sl).sum()
        f["contact_len"] = float(contact / 4.0 / W)   # approx. boundary length in image widths
        wt = xs_t.max() - xs_t.min() + 1
        ws = xs_s.max() - xs_s.min() + 1
        f["width_ratio"] = float(ws / wt)
        f["contact_ratio"] = float(contact / 4.0 / max(1, ws))   # contact length relative to the skirt width
        # lower-body pixels strictly under the skirt top / between
        low = np.isin(lab, LOWER)
        ymid = ys_s.min()
        f["lower_below_skirt"] = float((low[int(ys_s.mean()):]).sum() / n)
        f["lower_in_between"] = float(low[max(0, ys_t.max() - 5): ys_s.min() + 5].sum() / n) if ys_s.min() > ys_t.max() - 5 else 0.0
        # waist narrowing: min row width (of top+skirt union) in the junction / min(top width, skirt width)
        U = Tl | Sl
        rows = np.nonzero(U.any(1))[0]
        widths = np.array([U[r].sum() for r in rows], float)
        # junction band: rows between top's 60% height and skirt's 40% height
        y0 = int(ys_t.min() + 0.6 * (ys_t.max() - ys_t.min()))
        y1 = int(ys_s.min() + 0.4 * (ys_s.max() - ys_s.min()))
        band = [U[r].sum() for r in range(y0, max(y0 + 1, y1 + 1)) if 0 <= r < H and U[r].any()]
        wt_ref = np.percentile([Tl[r].sum() for r in range(ys_t.min(), ys_t.max() + 1) if Tl[r].any()], 75)
        ws_ref = np.percentile([Sl[r].sum() for r in range(ys_s.min(), ys_s.max() + 1) if Sl[r].any()], 75)
        f["narrow_ratio"] = float(min(band) / max(1.0, min(wt_ref, ws_ref))) if band else 1.0
    # mask-based
    for nm, m in (("v1", m1), ("v1a", m1a)):
        if m is None:
            continue
        mb = m > 0
        f[f"{nm}_frac"] = float(mb.sum() / n)
        f[f"{nm}_border"] = cs.border_touch_ratio(m)
    if m1 is not None and m1a is not None:
        a1, a2 = m1 > 0, m1a > 0
        extra = a2 & ~a1
        f["extra_frac"] = float(extra.sum() / n)
        f["extra_over_v1"] = float(extra.sum() / max(1, a1.sum()))
        f["lost_frac"] = float((a1 & ~a2).sum() / n)
        f["iou_v1_v1a"] = cs.iou(m1, m1a)
    if m1 is not None:
        f["v1_in_skirt"] = float(((m1 > 0) & S).sum() / max(1, S.sum()))   # share of skirt pixels already in v1 mask
        f["skirt_in_v1"] = float(((m1 > 0) & S).sum() / max(1, (m1 > 0).sum()))
    if m1a is not None:
        f["v1a_skirt_cover"] = float(((m1a > 0) & S).sum() / max(1, S.sum()))
    return f


def prob_feats(sp, s, i, lab):
    """SegFormer softmax features (cache 'segprob', 18 x 128 x 128) for the Skirt component."""
    pr = load(sp, s, i, "segprob")
    f = {}
    if pr is None:
        return f
    p = pr["p"].astype(np.float32)
    lab128 = cv2.resize(lab, (128, 128), interpolation=cv2.INTER_NEAREST)
    S = lab128 == 5
    T = np.isin(lab128, TOPC)
    ptop = p[4] + p[7]
    if S.sum() >= 4:
        f["pS_skirt"] = float(p[5][S].mean())
        f["pS_top"] = float(ptop[S].mean())
        f["pS_top_share"] = float((ptop[S] / np.maximum(1e-6, ptop[S] + p[5][S])).mean())
        f["pS_max"] = float(p[:, S].max(0).mean())
        f["pS_lower"] = float(p[[6, 12, 13, 9, 10, 8]][:, S].sum(0).mean())
        f["pS_frac_top_gt02"] = float((ptop[S] > 0.2).mean())
    if T.sum() >= 4:
        f["pT_top"] = float(ptop[T].mean())
        f["pT_skirt"] = float(p[5][T].mean())
    f["p_skirt_total"] = float(p[5].sum() / (128 * 128))
    f["p_top_total"] = float(ptop.sum() / (128 * 128))
    return f


def x_feats(sp, s, i, lab, m1, gt):
    """Features / IoUs from the extra SAM 2 prompts (cache 'sam2x')."""
    x = load(sp, s, i, "sam2x")
    f = {}
    if x is None or "skirt_only_masks" not in x:
        return f
    S = lab == 5
    T = np.isin(lab, TOPC)
    sk = cs.clean_mask(x["skirt_only_masks"][0]) > 0
    f["sk_area_over_S"] = float(sk.sum() / max(1, S.sum()))
    f["sk_iou_S"] = cs.iou(sk, S)
    f["sk_in_T"] = float((sk & T).sum() / max(1, T.sum()))          # SAM's skirt-prompt mask spilling into the top
    f["sk_sam"] = float(x["skirt_only_scores"][0])
    nt = cs.clean_mask(x["top_negskirt_masks"][0])
    f["tn_area_over_v1"] = float((nt > 0).sum() / max(1, (m1 > 0).sum())) if m1 is not None else np.nan
    f["tn_sam"] = float(x["top_negskirt_scores"][0])
    an = cs.clean_mask(x["all_negtop_masks"][0]) > 0
    f["an_area_over_S"] = float(an.sum() / max(1, S.sum()))
    f["an_in_T"] = float((an & T).sum() / max(1, T.sum()))
    f["an_sam"] = float(x["all_negtop_scores"][0])
    f["iou_sk_gt"] = iou512(sk, gt)
    return f


def run_split(split):
    rows = []
    for s, i, p, gtp, sp in items_all(split):
        lab, m1, m1a, s1, sa, mraw = get_masks(s, i, sp)
        bgr = read_bgr(p)
        if s == "mirra":
            gt = ev.load_mask(ROOT / "out" / "p00_baseline" / "reference" / i / "garment_mask.png", bgr.shape[:2])
        else:
            gt = ev.load_mask(gtp)
        H, W = gt.shape
        z = np.zeros((H, W), np.uint8)
        r = {"split": split, "set": s, "id": i, "sam_v1": s1, "sam_v1a": sa}
        r["iou_v1"] = iou512(m1 if m1 is not None else z, gt)
        r["iou_v1a"] = iou512(m1a if m1a is not None else z, gt)
        r["iou_v1a_noskin"] = iou512(mraw if mraw is not None else z, gt)
        r["have_v1"] = m1 is not None
        r["have_v1a"] = m1a is not None
        if m1 is not None:
            r["edge_v1"] = cs.compute_quality(m1, bgr)[1]["edge_alignment"]
        if m1a is not None:
            r["edge_v1a"] = cs.compute_quality(m1a, bgr)[1]["edge_alignment"]
        r.update(geom(lab, m1, m1a))
        S = lab == 5
        r["gt_in_skirt"] = float((gt & S).sum() / max(1, S.sum()))
        r.update(prob_feats(sp, s, i, lab))
        r.update(x_feats(sp, s, i, lab, m1, gt))
        rows.append(r)
        if len(rows) % 50 == 0:
            print(split, len(rows), flush=True)
    return pd.DataFrame(rows)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "held"])
    a = ap.parse_args()
    df = run_split(a.split)
    name = "features.csv" if a.split == "dev" else "features_heldout.csv"
    df.to_csv(P15 / name, index=False)
    print(df.groupby("set")[["iou_v1", "iou_v1a"]].mean())
    print("n with skirt label (>0.5% image):", df.groupby("set").apply(lambda d: (d.skirt_all_frac > 0.005).sum()))


if __name__ == "__main__":
    main()
