"""P15a GPU stage: every model runs once per image under gpu_lock('p15a'), outputs are cached.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_gpu.py --stage segprob  --split dev
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_gpu.py --stage segformer --split held
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_gpu.py --stage sam2      --split held
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_gpu.py --stage sam2x     --split dev|held

Stages
  segprob   SegFormer again on the dev images, saving the softmax (18 classes, 128 x 128, float16) 'segprob'
            (labels come from the P01 cache; the rerun's label map is compared with it)
  segformer SegFormer on held-out images: 'segformer' (labels, same format as P01) and 'segprob'
  sam2      SAM 2 on held-out images with the two v1 prompts, in P01 cache format:
              'sam2c'  box_segtop_pt   (box = largest component of Upper-clothes+Dress [or +Skirt when < 0.5 % of image], interior point)
              'sam2b'  box_seglc_pt    (same with Skirt included)
  sam2x     extra SAM 2 prompts for the rule experiments (cache 'sam2x', one embedding per image):
              top_negskirt  TOP box + interior point + one NEGATIVE point at the interior of the Skirt component
              all_negtop    ALL box + point at the interior of the Skirt component (positive) + negative point at the interior of TOP
              skirt_only    box of the Skirt component + its interior point (positive)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p15a_common import *  # noqa: F401,F403
import cv_segment as cs
from gpu_lock import gpu_lock
from PIL import Image


def interior_point(mask):
    m = cs.to_u8(mask)
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    y, x = np.unravel_index(int(np.argmax(dt)), dt.shape)
    return [int(x), int(y)]


def seg_probs(wrapper, pil):
    import torch
    import torch.nn.functional as F
    inputs = wrapper.proc(images=pil, return_tensors="pt")
    with torch.no_grad():
        logits = wrapper.model(pixel_values=inputs["pixel_values"].to(wrapper.device)).logits
    p = F.softmax(logits.float(), 1)[0].cpu().numpy()          # 18 x 128 x 128
    return p.astype(np.float16)


def todo(its, model):
    return [it for it in its if not cpath(it[4], it[0], it[1], model).exists()]


def run_segformer(its, with_labels):
    m = cs.SegformerWrapper().load()
    for s, i, p, _, sp in its:
        pil = Image.open(p).convert("RGB")
        t = time.perf_counter()
        pr = seg_probs(m, pil)
        dt = time.perf_counter() - t
        if with_labels:
            lab = m.labels(pil)
            save(sp, s, i, "segformer", labels=lab, t=dt)
        else:
            lab = load(sp, s, i, "segformer")["labels"]
            import torch
            import torch.nn.functional as F
            up = F.interpolate(torch.from_numpy(pr.astype(np.float32))[None], size=lab.shape, mode="bilinear", align_corners=False)
            agree = float((up.argmax(1)[0].numpy().astype(np.uint8) == lab).mean())
            print(f"    {s}/{i}: label agreement with the P01 cache {agree:.4f}", flush=True) if agree < 0.999 else None
        save(sp, s, i, "segprob", p=pr)
    m.unload()


def run_sam2(its):
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _, sp in its:
        sg = load(sp, s, i, "segformer")
        lab = sg["labels"]
        pil = Image.open(p).convert("RGB")
        t0 = time.perf_counter()
        sam.set_image(pil)
        te = time.perf_counter() - t0
        top = cs.to_u8(np.isin(lab, cs.SEG_GARMENT_TOP))
        allg = cs.to_u8(np.isin(lab, cs.SEG_GARMENT_ALL))
        gt_ = top if top.sum() >= 0.005 * top.size else allg
        if gt_.sum() >= 0.005 * gt_.size:
            lc = cs.largest_component(gt_)
            t = time.perf_counter()
            m, sc = sam.predict(points=[interior_point(lc)], labels=[1], box=cs.bbox_of(lc), multimask=False)
            save(sp, s, i, "sam2c", box_segtop_pt_masks=m, box_segtop_pt_scores=sc, t_embed=te, box_segtop_pt_t=time.perf_counter() - t)
        else:
            save(sp, s, i, "sam2c", t_embed=te)
        if allg.sum() > 0.005 * allg.size:
            lc = cs.largest_component(allg)
            t = time.perf_counter()
            m, sc = sam.predict(points=[interior_point(lc)], labels=[1], box=cs.bbox_of(lc), multimask=False)
            save(sp, s, i, "sam2b", box_seglc_pt_masks=m, box_seglc_pt_scores=sc, t_embed=te, box_seglc_pt_t=time.perf_counter() - t)
        else:
            save(sp, s, i, "sam2b", t_embed=te)
    sam.unload()


def run_sam2x(its):
    sam = cs.Sam2Wrapper().load()
    for s, i, p, _, sp in its:
        sg = load(sp, s, i, "segformer")
        lab = sg["labels"]
        n = lab.size
        S = cs.to_u8(lab == 5)
        T = cs.to_u8(np.isin(lab, cs.SEG_GARMENT_TOP))
        arrays = {}
        if S.sum() >= 0.005 * n and T.sum() >= 0.005 * n:
            pil = Image.open(p).convert("RGB")
            sam.set_image(pil)
            Sl, Tl = cs.largest_component(S), cs.largest_component(T)
            ps, pt = interior_point(Sl), interior_point(Tl)
            allg = cs.largest_component(cs.to_u8(np.isin(lab, cs.SEG_GARMENT_ALL)))

            def go(name, **kw):
                m, sc = sam.predict(multimask=False, **kw)
                arrays[f"{name}_masks"], arrays[f"{name}_scores"] = m, sc

            go("top_negskirt", points=[pt, ps], labels=[1, 0], box=cs.bbox_of(Tl))
            go("all_negtop", points=[ps, pt], labels=[1, 0], box=cs.bbox_of(allg))
            go("skirt_only", points=[ps], labels=[1], box=cs.bbox_of(Sl))
        save(sp, s, i, "sam2x", **arrays)
    sam.unload()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["segprob", "segformer", "sam2", "sam2x"])
    ap.add_argument("--split", required=True, choices=["dev", "held"])
    a = ap.parse_args()
    its = items_all("dev" if a.split == "dev" else "held")
    model = {"segprob": "segprob", "segformer": "segformer", "sam2": "sam2c", "sam2x": "sam2x"}[a.stage]
    its = todo(its, model)
    print(f"{a.stage}/{a.split}: {len(its)} images", flush=True)
    for k in range(0, len(its), 60):
        chunk = its[k:k + 60]
        with gpu_lock("p15a"):
            if a.stage == "segprob":
                run_segformer(chunk, with_labels=False)
            elif a.stage == "segformer":
                run_segformer(chunk, with_labels=True)
            elif a.stage == "sam2":
                run_sam2(chunk)
            else:
                run_sam2x(chunk)
        print(f"  done {min(k + 60, len(its))}/{len(its)}", flush=True)
