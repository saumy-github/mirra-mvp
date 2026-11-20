"""P01 stage 2: derive every segmentation method / combination from the cached raw model outputs and score it.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_methods.py --sets mirra            # saves masks + overlays
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_methods.py --sets viton_cloth viton_person fashionpedia

Mirra: masks go to out/p01_segmentation/methods/<method>/<cloth>/mask.png (+ overlay.jpg); score them with evaluate.py
(this script calls it for every method with label p01_<method>).
Public subsets: per-image metrics -> out/p01_segmentation/public_scores_per_image.csv and means -> public_scores.csv
(metrics computed with evaluate.mask_metrics on masks downscaled to max side 512).
Run time per image = the models' measured inference times (from the raw cache, GPU) + the post-processing time measured here.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p01_common import *  # noqa: F401,F403
import cv_segment as cs
import evaluate as ev

ALL_METHODS = [
    "v0_current", "sam2_fix", "sam2_centre_largest", "sam2_centre_agree_rmbg",
    "sam2_box_rmbg", "sam2_box_yoloe", "sam2_box_seg", "sam2_box_v0rough", "sam2_box_gdino",
    "sam2_boxonly_rmbg", "sam2_boxonly_yoloe", "sam2_boxonly_gdino",
    "rmbg_salient", "segformer_top", "segformer_all", "yolo26_person", "yolo26_person_minus_skin",
    "yoloe_tshirt", "yoloe_multi",
    "grabcut_rect", "grabcut_rmbg_box", "mrf_rmbg", "kmeans_centre", "meanshift_centre", "region_growing",
    "comb_box_rmbg_minus_skin", "comb_box_seg_minus_skin", "comb_box_yoloe_minus_skin",
    "comb_vote_sam2boxes", "comb_vote3", "comb_consensus_medoid",
    "comb_box_rmbg_grabcut", "comb_consensus_medoid_grabcut", "comb_vote3_grabcut", "comb_box_rmbg_mrf",
    "comb_box_rmbg_minus_skin_grabcut",
    "sam2_box_segpt", "sam2_box_seglc_pt", "sam2_box_seglc_ptneg",
    "comb_box_segpt_minus_skin", "comb_box_seglc_pt_minus_skin", "comb_box_seglc_ptneg_minus_skin",
    "comb_box_seglc_pt_minus_skin_grabcut",
    "sam2_box_segtop_pt", "sam2_box_segtop_ptneg", "sam2_box_gdino_segpt", "sam2_box_gdino_segptneg", "sam2_box_yoloe_segpt",
    "sam2_box_segadapt_pt", "comb_box_segadapt_pt_minus_skin",
    "comb_box_segtop_pt_minus_skin", "comb_box_gdino_segpt_minus_skin", "comb_majority3_top", "comb_majority3_gdino_yoloe",
]
SLOW = {"grabcut_rect", "grabcut_rmbg_box", "mrf_rmbg", "kmeans_centre", "meanshift_centre", "region_growing",
        "comb_consensus_medoid", "comb_box_rmbg_grabcut", "comb_consensus_medoid_grabcut", "comb_vote3_grabcut",
        "comb_box_rmbg_mrf", "comb_box_rmbg_minus_skin_grabcut", "comb_box_seglc_pt_minus_skin_grabcut"}
FAST = False
PRIMARY_BOX_SRCS = ["rmbg", "yoloe", "seg", "v0rough", "gdino"]


def _t(d, *keys):
    return float(sum(float(d[k]) for k in keys if d is not None and k in d))


def sam_pick(sam, name, rule="iou", other=None):
    masks, sc = sam[f"{name}_masks"], sam[f"{name}_scores"]
    i = cs.pick_candidate(masks, sc, rule, other)
    return masks[i], float(sc[i])


def derive(bgr, raw):
    """Return {method: (mask uint8 0/255, model_time_s, post_time_s, sam_iou|None)} for every method possible."""
    sam, seg, rm, yo, yl, gd = (raw.get(k) for k in ("sam2", "segformer", "rmbg", "yoloe", "yolo", "gdino"))
    sb = raw.get("sam2b")
    sc_ = raw.get("sam2c")
    out = {}
    cache = {}
    H, W = bgr.shape[:2]

    def add(name, fn, model_t=0.0, sam_iou=None):
        if FAST and name in SLOW:
            return
        t0 = time.perf_counter()
        try:
            m = fn()
        except Exception as e:  # noqa: BLE001
            print(f"    method {name} failed: {e}", flush=True)
            return
        if m is None:
            return
        out[name] = (cs.to_u8(m), model_t, time.perf_counter() - t0, sam_iou)
        cache[name] = out[name][0]

    # ── SAM 2 variants ──
    if sam is not None:
        te = float(sam["t_embed"])
        def v0(legacy):
            m, sc = sam_pick(sam, "v0")
            m = cs.clean_mask(m, legacy_fill=legacy)
            used_grid = not (5.0 <= (m > 0).mean() * 100 <= 95.0)
            if used_grid:
                m, sc = sam_pick(sam, "v0grid")
                m = cs.clean_mask(m, legacy_fill=legacy)
            return m, sc, used_grid
        for nm, legacy in (("v0_current", True), ("sam2_fix", False)):
            t0 = time.perf_counter()
            m, sc, grid = v0(legacy)
            out[nm] = (cs.to_u8(m), te + _t(sam, "v0_t") + (_t(sam, "v0grid_t") if grid else 0), time.perf_counter() - t0, sc)
            cache[nm] = out[nm][0]
        add("sam2_centre_largest", lambda: cs.clean_mask(sam_pick(sam, "centre", "largest_inside")[0]),
            te + _t(sam, "centre_t"), sam_pick(sam, "centre", "largest_inside")[1])
        if rm is not None:
            rm_mask = cs.largest_component(cs.to_u8(rm["soft"] > 127))
            add("sam2_centre_agree_rmbg", lambda: cs.clean_mask(sam_pick(sam, "centre", "agree", rm_mask)[0]),
                te + _t(sam, "centre_t") + _t(rm, "t"))
        for src in PRIMARY_BOX_SRCS:
            if f"box_{src}_masks" in sam:
                extra = {"rmbg": _t(rm, "t"), "yoloe": _t(yo, "tB"), "seg": _t(seg, "t"), "gdino": _t(gd, "t1"),
                         "v0rough": _t(sam, "v0_t")}[src]
                add(f"sam2_box_{src}", lambda src=src: cs.clean_mask(sam[f"box_{src}_masks"][0]),
                    te + _t(sam, f"box_{src}_t") + extra, float(sam[f"box_{src}_scores"][0]))
            if f"boxonly_{src}_masks" in sam:
                extra = {"rmbg": _t(rm, "t"), "yoloe": _t(yo, "tB"), "gdino": _t(gd, "t1")}[src]
                add(f"sam2_boxonly_{src}", lambda src=src: cs.clean_mask(sam[f"boxonly_{src}_masks"][0]),
                    te + _t(sam, f"boxonly_{src}_t") + extra, float(sam[f"boxonly_{src}_scores"][0]))

    if sb is not None:
        for nm in ("box_segpt", "box_seglc_pt", "box_seglc_ptneg"):
            if f"{nm}_masks" in sb:
                add(f"sam2_{nm}", lambda nm=nm: cs.clean_mask(sb[f"{nm}_masks"][0]),
                    float(sb["t_embed"]) + _t(sb, f"{nm}_t") + _t(seg, "t"), float(sb[f"{nm}_scores"][0]))

    if sc_ is not None:
        for nm in ("box_segtop_pt", "box_segtop_ptneg", "box_gdino_segpt", "box_gdino_segptneg", "box_yoloe_segpt"):
            if f"{nm}_masks" in sc_:
                extra = {"segtop": _t(seg, "t"), "gdino": _t(gd, "t1") + _t(seg, "t"), "yoloe": _t(yo, "tB") + _t(seg, "t")}[nm.split("_")[1]]
                add(f"sam2_{nm}", lambda nm=nm: cs.clean_mask(sc_[f"{nm}_masks"][0]),
                    float(sc_["t_embed"]) + _t(sc_, f"{nm}_t") + extra, float(sc_[f"{nm}_scores"][0]))

    # ── single other models ──
    if rm is not None:
        add("rmbg_salient", lambda: cs.clean_mask(rm["soft"] > 127), _t(rm, "t"))
    if seg is not None:
        lab = seg["labels"]
        add("segformer_top", lambda: cs.clean_mask(cs.seg_mask(lab, cs.SEG_GARMENT_TOP)), _t(seg, "t"))
        add("segformer_all", lambda: cs.clean_mask(cs.seg_mask(lab, cs.SEG_GARMENT_ALL)), _t(seg, "t"))
    if yl is not None:
        add("yolo26_person", lambda: cs.clean_mask(yl["mask"]), _t(yl, "t"))
        if seg is not None:
            add("yolo26_person_minus_skin", lambda: cs.clean_mask(cs.sam2_minus_skin(yl["mask"], seg["labels"], cs.SEG_SKIN + (1, 3, 9, 10, 6, 5))),
                _t(yl, "t") + _t(seg, "t"))
    if yo is not None:
        add("yoloe_tshirt", lambda: cs.clean_mask(yo["maskA"]), _t(yo, "tA"))
        add("yoloe_multi", lambda: cs.clean_mask(yo["maskB"]), _t(yo, "tB"))

    # ── classical (Unit III) ──
    add("grabcut_rect", lambda: cs.clean_mask(cs.grabcut_box(bgr)))
    if rm is not None:
        rb = cs.bbox_of(cs.largest_component(cs.to_u8(rm["soft"] > 127)))
        if rb:
            add("grabcut_rmbg_box", lambda: cs.clean_mask(cs.grabcut_box(bgr, rb)), _t(rm, "t"))
        add("mrf_rmbg", lambda: cs.clean_mask(cs.mrf_smooth(rm["soft"], bgr)), _t(rm, "t"))
    add("kmeans_centre", lambda: cs.clean_mask(cs.kmeans_region(bgr)))
    add("meanshift_centre", lambda: cs.clean_mask(cs.meanshift_region(bgr)))
    add("region_growing", lambda: cs.clean_mask(cs.region_growing(bgr)))

    # ── combinations ──
    def comb_minus_skin(base):
        return lambda: cs.clean_mask(cs.sam2_minus_skin(cache[base], seg["labels"]))
    for base in ("sam2_box_rmbg", "sam2_box_seg", "sam2_box_yoloe"):
        if base in cache and seg is not None:
            add(f"comb_{base[5:]}_minus_skin", comb_minus_skin(base), out[base][1] + _t(seg, "t"), out[base][3])
    for nm in ("box_segpt", "box_seglc_pt", "box_seglc_ptneg"):
        if f"sam2_{nm}" in cache and seg is not None:
            add(f"comb_{nm}_minus_skin", comb_minus_skin(f"sam2_{nm}"), out[f"sam2_{nm}"][1], out[f"sam2_{nm}"][3])
    if "comb_box_seglc_pt_minus_skin" in cache:
        add("comb_box_seglc_pt_minus_skin_grabcut", lambda: cs.clean_mask(cs.grabcut_refine(bgr, cache["comb_box_seglc_pt_minus_skin"])),
            out["comb_box_seglc_pt_minus_skin"][1], out["comb_box_seglc_pt_minus_skin"][3])
    for nm in ("box_segtop_pt", "box_gdino_segpt"):
        if f"sam2_{nm}" in cache and seg is not None:
            add(f"comb_{nm}_minus_skin", comb_minus_skin(f"sam2_{nm}"), out[f"sam2_{nm}"][1], out[f"sam2_{nm}"][3])
    sd = raw.get("sam2e")
    if sd is not None and "sam2_box_segtop_pt" in cache:
        if "box_segadapt_pt_masks" in sd:
            add("sam2_box_segadapt_pt", lambda: cs.clean_mask(sd["box_segadapt_pt_masks"][0]),
                float(sd["t_embed"]) + _t(sd, "box_segadapt_pt_t") + _t(seg, "t"), float(sd["box_segadapt_pt_scores"][0]))
        else:   # rule did not add Skirt: identical to box_segtop_pt (or its fallback)
            add("sam2_box_segadapt_pt", lambda: cache["sam2_box_segtop_pt"], out["sam2_box_segtop_pt"][1], out["sam2_box_segtop_pt"][3])
    if "sam2_box_segadapt_pt" in cache and seg is not None:
        add("comb_box_segadapt_pt_minus_skin", comb_minus_skin("sam2_box_segadapt_pt"), out["sam2_box_segadapt_pt"][1], out["sam2_box_segadapt_pt"][3])
    mj = ["segformer_top", "sam2_box_gdino_segpt", "sam2_box_segtop_pt"]
    if all(n in cache for n in mj):
        add("comb_majority3_top", lambda: cs.clean_mask(cs.weighted_vote([cache[n] for n in mj], [1, 1, 1])),
            sum(out[n][1] for n in mj))
    mj2 = ["segformer_top", "sam2_box_gdino", "sam2_box_yoloe"]
    if all(n in cache for n in mj2):
        add("comb_majority3_gdino_yoloe", lambda: cs.clean_mask(cs.weighted_vote([cache[n] for n in mj2], [1, 1, 1])),
            sum(out[n][1] for n in mj2))
    votes = [n for n in ("sam2_box_rmbg", "sam2_box_yoloe", "sam2_box_seg") if n in cache]
    if len(votes) >= 2:
        add("comb_vote_sam2boxes", lambda: cs.clean_mask(cs.weighted_vote(
            [cache[n] for n in votes], [out[n][3] or 0.5 for n in votes])),
            sum(out[n][1] for n in votes))
    v3 = []
    if "sam2_box_rmbg" in cache:
        v3.append(("sam2_box_rmbg", out["sam2_box_rmbg"][3] or 0.5))
    if "segformer_all" in cache and seg is not None:
        v3.append(("segformer_all", 0.8))
    if "yoloe_multi" in cache:
        v3.append(("yoloe_multi", float(yo["confB"])))
    if "rmbg_salient" in cache and len(v3) < 3:
        v3.append(("rmbg_salient", float(np.mean(rm["soft"][cache["rmbg_salient"] > 0] / 255.0)) if cache["rmbg_salient"].any() else 0.3))
    if len(v3) >= 3:
        names = [n for n, _ in v3[:3]]
        add("comb_vote3", lambda: cs.clean_mask(cs.weighted_vote([cache[n] for n, _ in v3[:3]], [w for _, w in v3[:3]])),
            sum(out[n][1] for n in names))
    pool = [n for n in ("sam2_box_rmbg", "sam2_box_yoloe", "sam2_box_seg", "sam2_centre_largest", "rmbg_salient",
                        "segformer_all", "yoloe_multi") if n in cache and cache[n].any()]
    if len(pool) >= 3:
        def consensus():
            sc = [sum(cs.iou(cache[a], cache[b]) for b in pool if b != a) for a in pool]
            return cache[pool[int(np.argmax(sc))]]
        add("comb_consensus_medoid", consensus, sum(out[n][1] for n in pool))
    for base in ("sam2_box_rmbg", "comb_consensus_medoid", "comb_vote3"):
        if base in cache:
            add(f"comb_{base.replace('sam2_', '').replace('comb_', '')}_grabcut", lambda b=base: cs.clean_mask(cs.grabcut_refine(bgr, cache[b])), out[base][1], out[base][3])
    if "sam2_box_rmbg" in cache:
        add("comb_box_rmbg_mrf", lambda: cs.clean_mask(cs.mrf_smooth(cv2.GaussianBlur(cache["sam2_box_rmbg"].astype(np.float32) / 255, (0, 0), 3), bgr)),
            out["sam2_box_rmbg"][1], out["sam2_box_rmbg"][3])
    if "comb_box_rmbg_minus_skin" in cache:
        add("comb_box_rmbg_minus_skin_grabcut", lambda: cs.clean_mask(cs.grabcut_refine(bgr, cache["comb_box_rmbg_minus_skin"])),
            out["comb_box_rmbg_minus_skin"][1])
    # a method that found nothing (no detector box, empty mask) counts as an empty mask = a failure, so that
    # means over images are not computed only on the images where the method happened to fire
    for name in ALL_METHODS:
        if name not in out and not (FAST and name in SLOW):
            out[name] = (np.zeros((H, W), np.uint8), 0.0, 0.0, None)
    return out


def load_raw(s, i):
    return {m: load_cache(s, i, m) for m in ("sam2", "sam2b", "sam2c", "sam2e", "segformer", "rmbg", "yolo", "yoloe", "gdino")}


def metric_small(pred, gt, max_side=512):
    h, w = gt.shape
    sc = min(1.0, max_side / max(h, w))
    if sc < 1.0:
        sz = (int(round(w * sc)), int(round(h * sc)))
        pred = cv2.resize(cs.to_u8(pred), sz, interpolation=cv2.INTER_NEAREST) > 0
        gt = cv2.resize(cs.to_u8(gt), sz, interpolation=cv2.INTER_NEAREST) > 0
    return ev.mask_metrics(pred > 0, gt > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="*", default=["mirra"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--eval-only", nargs="*", default=None, help="only call evaluate.py for these methods")
    ap.add_argument("--fast", action="store_true", help="skip the slow classical / GrabCut / MRF / consensus methods")
    ap.add_argument("--tag", default="", help="suffix for the public csv names (new attempt = new file)")
    a = ap.parse_args()
    global FAST
    FAST = a.fast
    rows = []
    for s in a.sets:
        its = items([s], a.limit)
        for k, (_, i, p, gtp) in enumerate(its):
            bgr = read_bgr(p)
            res = derive(bgr, load_raw(s, i))
            gt = ev.load_mask(gtp) if gtp is not None else None
            for name, (m, mt, pt, si) in res.items():
                if s == "mirra":
                    d = METHODS_DIR / name / i
                    d.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(d / "mask.png"), m)
                    cv2.imwrite(str(d / "overlay.jpg"), cs.overlay(bgr, m), [cv2.IMWRITE_JPEG_QUALITY, 85])
                else:
                    r = metric_small(m, gt)
                    rows.append({"set": s, "id": i, "method": name, **r, "time_s": mt + pt, "model_time_s": mt, "post_time_s": pt})
            if (k + 1) % 25 == 0:
                print(f"  {s}: {k + 1}/{len(its)}", flush=True)
    if "mirra" in a.sets:
        names = sorted(p.name for p in METHODS_DIR.iterdir() if p.is_dir())
        if a.eval_only:
            names = [n for n in names if n in a.eval_only]
        for n in names:
            subprocess.run([sys.executable, str(HERE / "evaluate.py"), "--pred", str(METHODS_DIR / n),
                            "--label", f"p01_{n}", "--plan", "p01"], capture_output=True)
        print("evaluated", len(names), "Mirra methods")
    if rows:
        per = OUT / f"public_scores_per_image{a.tag}.csv"
        new = not per.exists()
        keys = list(rows[0].keys())
        with open(per, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            if new:
                w.writeheader()
            w.writerows(rows)
        print("wrote", per)


if __name__ == "__main__":
    main()
