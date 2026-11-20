"""P01 stage 1: run each model ONCE on every image and cache its raw output under out/p01_segmentation/cache.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p01_raw_models.py --model segformer [--sets mirra viton_cloth ...] [--limit N]

Models (one per invocation, one GPU lock block each; the model is deleted before the lock is released):
  segformer  label map + mean softmax confidence of the garment classes
  rmbg       BRIA RMBG-1.4 soft foreground (U2-Net family; rembg's own U2-Net needs onnxruntime, not installed)
  yolo       yolo26m-seg, COCO 'person' mask (reference only)
  yoloe      yoloe-26m-seg text prompts  A = ["t-shirt"]   B = ["t-shirt","shirt","top","sweater","jacket"]
  gdino      Grounding DINO tiny, text "t-shirt."  (and "shirt. top. sweater. jacket." as prompt 2)
  sam2       sam2-hiera-large, all prompts below (needs the other caches for the box prompts; run it last)
SAM 2 prompts (pixel coords; W, H = image size):
  v0        1 fg point (W/2, H/2) + 4 bg corner points, multimask (3 candidates)           [current pipeline]
  v0grid    3x3 fg grid in the central 60 % + 4 bg corners, multimask                       [v0 pass 2]
  centre    1 fg point (W/2, H/2) only, multimask
  box_<src> box + fg centre point, single mask (multimask_output=False);
            src = rmbg (bbox of RMBG soft>127, largest component), yoloe (box of best YOLOE-B instance),
                  seg (bbox of SegFormer Upper-clothes+Dress+Skirt), v0rough (bbox of the v0 argmax-IoU candidate),
                  gdino (Grounding DINO box)
  boxonly_<src>  box only (no point), single mask, src = rmbg, yoloe, gdino
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p01_common import *  # noqa: F401,F403
import cv_segment as cs
from gpu_lock import gpu_lock
from PIL import Image


def todo(its, model):
    return [it for it in its if not cache_path(it[0], it[1], model).exists()]


def run_segformer(its):
    m = cs.SegformerWrapper().load()
    import torch
    for s, i, p, _ in its:
        pil = Image.open(p).convert("RGB")
        t = time.perf_counter()
        lab = m.labels(pil)
        dt = time.perf_counter() - t
        save_cache(s, i, "segformer", labels=lab, t=dt)
    m.unload()


def run_rmbg(its):
    m = cs.SalientWrapper().load()
    for s, i, p, _ in its:
        pil = Image.open(p).convert("RGB")
        t = time.perf_counter()
        soft = m.soft(pil)
        save_cache(s, i, "rmbg", soft=soft, t=time.perf_counter() - t)
    m.unload()


def run_yolo(its):
    m = cs.YoloWrapper(str(WEIGHTS / "yolo26m-seg.pt")).load()
    for s, i, p, _ in its:
        bgr = read_bgr(p)
        t = time.perf_counter()
        mask, conf, box = m.person(bgr)
        dt = time.perf_counter() - t
        if mask is None:
            mask, box = np.zeros(bgr.shape[:2], np.uint8), [0, 0, 0, 0]
        save_cache(s, i, "yolo", mask=mask, conf=conf, box=box, t=dt)
    m.unload()


def run_yoloe(its):
    m = cs.YoloeWrapper(str(WEIGHTS / "yoloe-26m-seg.pt")).load()
    prompts = {"A": ["t-shirt"], "B": ["t-shirt", "shirt", "top", "sweater", "jacket"]}
    for s, i, p, _ in its:
        bgr = read_bgr(p)
        arrays = {}
        for k, names in prompts.items():
            m.set_prompts(names)
            t = time.perf_counter()
            mask, conf, box, name = m.best(bgr)
            arrays[f"t{k}"] = time.perf_counter() - t
            if mask is None:
                mask, box, name = np.zeros(bgr.shape[:2], np.uint8), [0, 0, 0, 0], ""
            arrays[f"mask{k}"], arrays[f"conf{k}"], arrays[f"box{k}"], arrays[f"name{k}"] = mask, conf, box, name
        save_cache(s, i, "yoloe", **arrays)
    m.unload()


def run_gdino(its):
    m = cs.GDinoWrapper().load()
    for s, i, p, _ in its:
        pil = Image.open(p).convert("RGB")
        arrays = {}
        for k, text in (("1", "t-shirt."), ("2", "shirt. top. sweater. jacket.")):
            t = time.perf_counter()
            box, sc = m.box(pil, text)
            arrays[f"t{k}"] = time.perf_counter() - t
            arrays[f"box{k}"] = box if box is not None else [0, 0, 0, 0]
            arrays[f"score{k}"] = sc
        save_cache(s, i, "gdino", **arrays)
    m.unload()


def rmbg_box(soft):
    m = cs.largest_component(cs.to_u8(soft > 127))
    return cs.bbox_of(m)


def run_sam2(its):
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _ in its:
        pil = Image.open(p).convert("RGB")
        W, H = pil.size
        t0 = time.perf_counter()
        sam.set_image(pil)
        t_embed = time.perf_counter() - t0
        arrays = {"t_embed": t_embed}
        centre = [[W // 2, H // 2]]
        corners = [[0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1]]
        x0, x1, y0, y1 = int(W * .2), int(W * .8), int(H * .2), int(H * .8)
        grid = [[x0 + (x1 - x0) * c // 2, y0 + (y1 - y0) * r // 2] for r in range(3) for c in range(3)]

        def go(name, **kw):
            t = time.perf_counter()
            masks, sc = sam.predict(**kw)
            arrays[f"{name}_masks"] = masks
            arrays[f"{name}_scores"] = sc
            arrays[f"{name}_t"] = time.perf_counter() - t
            return masks, sc

        masks, sc = go("v0", points=centre + corners, labels=[1] + [0] * 4, multimask=True)
        go("v0grid", points=grid + corners, labels=[1] * 9 + [0] * 4, multimask=True)
        go("centre", points=centre, labels=[1], multimask=True)
        rough = cs.bbox_of(cs.clean_mask(masks[int(np.argmax(sc))], legacy_fill=True))
        boxes = {"v0rough": rough}
        r = load_cache(s, i, "rmbg")
        if r is not None:
            boxes["rmbg"] = rmbg_box(r["soft"])
        y = load_cache(s, i, "yoloe")
        if y is not None and y["maskB"].any():
            boxes["yoloe"] = [int(v) for v in y["boxB"]]
        g = load_cache(s, i, "gdino")
        if g is not None and float(g["score1"]) > 0:
            boxes["gdino"] = [int(v) for v in g["box1"]]
        sg = load_cache(s, i, "segformer")
        if sg is not None:
            bb = cs.bbox_of(np.isin(sg["labels"], cs.SEG_GARMENT_ALL))
            if bb is not None:
                boxes["seg"] = bb
        for src, box in boxes.items():
            if box is None or box[2] <= box[0] or box[3] <= box[1]:
                continue
            go(f"box_{src}", points=centre, labels=[1], box=box, multimask=False)
            if src in ("rmbg", "yoloe", "gdino"):
                go(f"boxonly_{src}", box=box, multimask=False)
            arrays[f"box_{src}_xyxy"] = np.array(box)
        save_cache(s, i, "sam2", **arrays)
    sam.unload()


def interior_point(mask):
    """Pixel of the (largest component of the) mask that is farthest from its border."""
    m = cs.to_u8(mask)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    y, x = np.unravel_index(int(np.argmax(dt)), dt.shape)
    return [int(x), int(y)]


def run_sam2b(its):
    """SAM 2 prompts built from the SegFormer garment region (needs the segformer cache):
      box_segpt       raw bbox of SegFormer Upper-clothes+Dress+Skirt pixels + fg point at the most interior pixel of the garment
      box_seglc_pt    bbox of the largest connected garment component + the same kind of point
      box_seglc_ptneg as box_seglc_pt + up to 4 negative points (most interior pixel of Face, Hair, Left-arm, Right-arm
                      regions covering >= 0.3 % of the image)
    All single-mask output."""
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _ in its:
        sg = load_cache(s, i, "segformer")
        pil = Image.open(p).convert("RGB")
        t0 = time.perf_counter()
        sam.set_image(pil)
        arrays = {"t_embed": time.perf_counter() - t0}
        g = cs.to_u8(np.isin(sg["labels"], cs.SEG_GARMENT_ALL))
        if g.sum() > 0.005 * g.size:
            lc = cs.largest_component(g)
            pt = interior_point(lc)
            negs = []
            for lab in (11, 2, 14, 15):
                mk = cs.to_u8(sg["labels"] == lab)
                if mk.sum() >= 0.003 * mk.size:
                    negs.append(interior_point(cs.largest_component(mk)))
            def go(name, **kw):
                t = time.perf_counter()
                masks, sc = sam.predict(multimask=False, **kw)
                arrays[f"{name}_masks"], arrays[f"{name}_scores"], arrays[f"{name}_t"] = masks, sc, time.perf_counter() - t
            go("box_segpt", points=[pt], labels=[1], box=cs.bbox_of(g))
            go("box_seglc_pt", points=[pt], labels=[1], box=cs.bbox_of(lc))
            go("box_seglc_ptneg", points=[pt] + negs, labels=[1] + [0] * len(negs), box=cs.bbox_of(lc))
        save_cache(s, i, "sam2b", **arrays)
    sam.unload()


def run_sam2c(its):
    """Round-2 SAM 2 prompts (needs segformer + gdino + yoloe caches). g = SegFormer 'top' region (Upper-clothes + Dress;
    falls back to + Skirt when < 0.5 % of the image), lc = its largest component, pt = most interior pixel of lc,
    negs = most interior pixel of Face / Hair / Left-arm / Right-arm regions >= 0.3 % of the image:
      box_segtop_pt        box = bbox(lc of g), fg point pt
      box_segtop_ptneg     same + negs
      box_gdino_segpt      Grounding DINO 't-shirt.' box, fg point pt (image centre when g is empty)
      box_gdino_segptneg   same + negs
      box_yoloe_segpt      YOLOE-B best box, fg point pt
    All single-mask output."""
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _ in its:
        sg = load_cache(s, i, "segformer")
        gd = load_cache(s, i, "gdino")
        yo = load_cache(s, i, "yoloe")
        pil = Image.open(p).convert("RGB")
        W, H = pil.size
        t0 = time.perf_counter()
        sam.set_image(pil)
        arrays = {"t_embed": time.perf_counter() - t0}
        g = cs.to_u8(np.isin(sg["labels"], cs.SEG_GARMENT_TOP))
        if g.sum() < 0.005 * g.size:
            g = cs.to_u8(np.isin(sg["labels"], cs.SEG_GARMENT_ALL))
        have_g = g.sum() >= 0.005 * g.size
        lc = cs.largest_component(g) if have_g else None
        pt = interior_point(lc) if have_g else [W // 2, H // 2]
        negs = []
        for lab in (11, 2, 14, 15):
            mk = cs.to_u8(sg["labels"] == lab)
            if mk.sum() >= 0.003 * mk.size:
                negs.append(interior_point(cs.largest_component(mk)))

        def go(name, box, neg):
            if box is None or box[2] <= box[0] or box[3] <= box[1]:
                return
            pts = [pt] + (negs if neg else [])
            t = time.perf_counter()
            masks, sc = sam.predict(points=pts, labels=[1] + [0] * (len(pts) - 1), box=box, multimask=False)
            arrays[f"{name}_masks"], arrays[f"{name}_scores"], arrays[f"{name}_t"] = masks, sc, time.perf_counter() - t

        if have_g:
            bx = cs.bbox_of(lc)
            go("box_segtop_pt", bx, False)
            go("box_segtop_ptneg", bx, True)
        if float(gd["score1"]) > 0:
            gb = [int(v) for v in gd["box1"]]
            go("box_gdino_segpt", gb, False)
            go("box_gdino_segptneg", gb, True)
        if yo["maskB"].any():
            go("box_yoloe_segpt", [int(v) for v in yo["boxB"]], False)
        arrays["g_top_masks"] = g
        save_cache(s, i, "sam2c", **arrays)
    sam.unload()


LOWER_FRAC = 0.03   # attempt 1 used 0.005 (cache 'sam2d'): too small, 1.1 % of stray leg/shoe pixels in c_003 blocked the rule


def adaptive_garment(labels):
    """Garment region for the adaptive rule: Upper-clothes + Dress; Skirt is added only when no lower-body pixels
    (Pants, Left/Right-leg, shoes) cover >= 3 % of the image, i.e. the photo is cropped above the waist so that a
    'Skirt' label under a top is most likely the lower half of the same top (SegFormer mislabels it, e.g. Mirra c_003).
    Falls back to Upper-clothes + Dress + Skirt when the top region is < 0.5 % of the image."""
    top = np.isin(labels, cs.SEG_GARMENT_TOP)
    lower = np.isin(labels, (6, 9, 10, 12, 13)).mean() >= LOWER_FRAC
    use_skirt = (not lower) and np.isin(labels, (5,)).any()
    g = np.isin(labels, cs.SEG_GARMENT_ALL) if (use_skirt or top.mean() < 0.005) else top
    return cs.to_u8(g), bool(use_skirt)


def run_sam2d(its):
    """box_segadapt_pt: box = bbox of the largest component of the adaptive garment region, fg point = its most interior
    pixel; single mask. Only images where the rule adds Skirt need a new SAM 2 pass (others equal box_segtop_pt)."""
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _ in its:
        sg = load_cache(s, i, "segformer")
        g, added = adaptive_garment(sg["labels"])
        arrays = {"skirt_added": added}
        if added and g.sum() >= 0.005 * g.size:
            pil = Image.open(p).convert("RGB")
            t0 = time.perf_counter()
            sam.set_image(pil)
            arrays["t_embed"] = time.perf_counter() - t0
            lc = cs.largest_component(g)
            t = time.perf_counter()
            masks, sc = sam.predict(points=[interior_point(lc)], labels=[1], box=cs.bbox_of(lc), multimask=False)
            arrays["box_segadapt_pt_masks"], arrays["box_segadapt_pt_scores"] = masks, sc
            arrays["box_segadapt_pt_t"] = time.perf_counter() - t
        save_cache(s, i, "sam2e", **arrays)
    sam.unload()


RUN = {"segformer": run_segformer, "rmbg": run_rmbg, "yolo": run_yolo, "yoloe": run_yoloe,
       "gdino": run_gdino, "sam2": run_sam2, "sam2b": run_sam2b, "sam2c": run_sam2c, "sam2d": run_sam2d, "sam2e": run_sam2d}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(RUN))
    ap.add_argument("--sets", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    its = todo(items(a.sets, a.limit), a.model)
    print(f"{a.model}: {len(its)} images to run", flush=True)
    if its:
        # work in chunks of 60 images per lock block so other agents can interleave
        for k in range(0, len(its), 60):
            with gpu_lock("p01"):
                RUN[a.model](its[k:k + 60])
            print(f"  done {min(k + 60, len(its))}/{len(its)}", flush=True)
