"""P17: evaluate the fine-tuned YOLO-seg model on P01's exact public test subsets, the Mirra photos and my val split.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p17_eval.py --weights out/p17_yolo_seg/runs/run1/weights/best.pt [--sam2]

Mask variants of the YOLO output (all instances with conf >= --conf):
  top1     the highest-confidence instance
  union    the union of all instances
  largest  the largest instance
The variant is CHOSEN ON MY VAL SPLIT (VITON val + Fashionpedia val, never the test sets) by macro IoU.
--sam2: also YOLO box (+ interior point of the YOLO mask) -> SAM 2 (single mask) for the chosen variant's box.
Scoring = P01's: evaluate.mask_metrics on masks downscaled to max side 512 (metric_small); no mask = empty (IoU 0);
fail = IoU < 0.1. Times are wall-clock per image on the shared GPU (after one warm-up).
Outputs: out/p17_yolo_seg/{public_scores.csv, per_image_<label>.csv, val_scores.csv, eval_summary.json, mirra/<cloth>/mask.png}
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from p01_common import items, read_bgr, REPO, ROOT, SUBSETS  # noqa: E402
import cv_segment as cs  # noqa: E402
import evaluate as ev  # noqa: E402
from gpu_lock import gpu_lock  # noqa: E402

OUTD = ROOT / "out" / "p17_yolo_seg"
VAL_DIR = OUTD / "dataset" / "images" / "val"
VAR = ("top1", "union", "largest")
KEYS = ["iou", "boundary_f@1.0%", "hd95_pct_diag", "leakage", "miss"]


def metric_small(pred, gt, max_side=512):
    h, w = gt.shape
    sc = min(1.0, max_side / max(h, w))
    if sc < 1.0:
        sz = (int(round(w * sc)), int(round(h * sc)))
        pred = cv2.resize(cs.to_u8(pred), sz, interpolation=cv2.INTER_NEAREST) > 0
        gt = cv2.resize(cs.to_u8(gt), sz, interpolation=cv2.INTER_NEAREST) > 0
    return ev.mask_metrics(pred > 0, gt > 0)


def val_items():
    out = []
    for p in sorted(VAL_DIR.glob("*.jpg")):
        lab = OUTD / "dataset" / "labels" / "val" / (p.stem + ".txt")
        im = cv2.imread(str(p))
        h, w = im.shape[:2]
        gt = np.zeros((h, w), np.uint8)
        for ln in lab.read_text().splitlines():
            v = np.array(ln.split()[1:], float).reshape(-1, 2) * [w, h]
            cv2.fillPoly(gt, [v.round().astype(np.int32)], 255)
        set_ = {"vc": "val_viton_cloth", "vp": "val_viton_person", "fp": "val_fashionpedia"}[p.stem[:2]]
        out.append((set_, p.stem, p, gt))
    return out


def yolo_instances(model, bgr, conf, imgsz):
    """-> list of (conf, box xyxy, mask bool HxW) sorted by conf desc; and elapsed seconds."""
    import torch
    t = time.perf_counter()
    r = model.predict(bgr, imgsz=imgsz, conf=conf, retina_masks=True, verbose=False, device=0)[0]
    if r.masks is None or len(r.boxes) == 0:
        torch.cuda.synchronize()
        return [], time.perf_counter() - t
    m = r.masks.data.cpu().numpy() > 0.5
    c = r.boxes.conf.cpu().numpy()
    b = r.boxes.xyxy.cpu().numpy()
    dt = time.perf_counter() - t
    o = np.argsort(-c)
    return [(float(c[i]), b[i], m[i]) for i in o], dt


def pick(inst, variant, shape):
    if not inst:
        return np.zeros(shape, bool), None
    if variant == "top1":
        return inst[0][2], inst[0][1]
    if variant == "union":
        u = np.zeros(shape, bool)
        for _, _, m in inst:
            u |= m
        return u, inst[0][1]
    k = int(np.argmax([m.sum() for _, _, m in inst]))
    return inst[k][2], inst[k][1]


def interior_point(mask):
    d = cv2.distanceTransform(cs.to_u8(cs.largest_component(mask)), cv2.DIST_L2, 5)
    y, x = np.unravel_index(int(np.argmax(d)), d.shape)
    return [int(x), int(y)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(OUTD / "runs" / "run1" / "weights" / "best.pt"))
    ap.add_argument("--label", default="p17_yolo_seg_finetuned")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--sam2", action="store_true")
    ap.add_argument("--variant", default=None, help="force a variant instead of choosing on val")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    from ultralytics import YOLO

    test_items = items(["viton_cloth", "viton_person", "fashionpedia"])
    mirra = items(["mirra"])
    vitems = val_items()

    rows = []   # per image rows: set, id, variant, metrics..., t
    store = {}  # (set,id) -> instances for the SAM 2 stage (boxes only) + times
    with gpu_lock("p17"):
        model = YOLO(a.weights)
        _ = yolo_instances(model, read_bgr(test_items[0][2]), a.conf, a.imgsz)  # warm-up
        # ---- val split (variant choice) and test sets ----
        for group, its in (("val", vitems), ("test", test_items)):
            for s, i, p, g in its:
                bgr = read_bgr(p) if group == "test" else cv2.imread(str(p))
                gt = (cv2.imread(str(g), cv2.IMREAD_GRAYSCALE) > 127) if group == "test" else (g > 127)
                inst, dt = yolo_instances(model, bgr, a.conf, a.imgsz)
                store[(s, i)] = (p, [(c, b.tolist()) for c, b, _ in inst], dt, group)
                for v in VAR:
                    pm, _ = pick(inst, v, gt.shape)
                    m = metric_small(pm, gt)
                    rows.append(dict(set=s, id=i, variant=v, n_inst=len(inst), t=dt, **{k: m[k] for k in KEYS}))
        # ---- Mirra: all variants saved, standard format for the chosen one later ----
        mirra_masks = {}
        for s, i, p, _ in mirra:
            bgr = read_bgr(p)
            inst, dt = yolo_instances(model, bgr, a.conf, a.imgsz)
            mirra_masks[i] = (bgr, inst, dt)
        # choose variant on val
        def macro(v, sets):
            vals = []
            for st in sets:
                x = [r["iou"] for r in rows if r["set"] == st and r["variant"] == v]
                vals.append(np.mean(x))
            return float(np.mean(vals))
        vsets = ["val_viton_cloth", "val_viton_person", "val_fashionpedia"]
        val_macro = {v: macro(v, vsets) for v in VAR}
        chosen = a.variant or max(val_macro, key=val_macro.get)
        print("val macro IoU per variant:", val_macro, "-> chosen:", chosen, flush=True)

        # ---- Mirra masks (chosen variant) ----
        mdir = OUTD / "mirra"
        for i, (bgr, inst, dt) in mirra_masks.items():
            pm, _ = pick(inst, chosen, bgr.shape[:2])
            (mdir / i).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(mdir / i / "mask.png"), cs.to_u8(pm))
            cv2.imwrite(str(mdir / i / "overlay.jpg"), cs.overlay(bgr, pm))
        # ---- optional: YOLO box -> SAM 2 ----
        sam_rows = []
        if a.sam2:
            sam = cs.Sam2Wrapper().load()
            from PIL import Image
            for group, its in (("val", vitems), ("test", test_items)):
                for s, i, p, g in its:
                    pth, boxes, dt_y, _ = store[(s, i)]
                    bgr = read_bgr(pth) if group == "test" else cv2.imread(str(pth))
                    gt = (cv2.imread(str(g), cv2.IMREAD_GRAYSCALE) > 127) if group == "test" else (g > 127)
                    if not boxes:
                        for v in ("box", "box_pt"):
                            sam_rows.append(dict(set=s, id=i, variant="yolo_" + v + "_sam2", n_inst=0, t=dt_y,
                                                 **{k: metric_small(np.zeros(gt.shape, bool), gt)[k] for k in KEYS}))
                        continue
                    inst, _ = yolo_instances(model, bgr, a.conf, a.imgsz)
                    pm, bx = pick(inst, chosen, gt.shape)
                    if chosen == "union":   # box = union of all boxes
                        bx = [min(b[0] for _, b, _ in inst), min(b[1] for _, b, _ in inst),
                              max(b[2] for _, b, _ in inst), max(b[3] for _, b, _ in inst)]
                    pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                    t = time.perf_counter()
                    sam.set_image(pil)
                    ms, sc = sam.predict(box=list(map(float, bx)), multimask=False)
                    m_box = ms[0]
                    t_box = time.perf_counter() - t
                    pt = interior_point(pm) if pm.any() else [int((bx[0] + bx[2]) / 2), int((bx[1] + bx[3]) / 2)]
                    ms2, _ = sam.predict(points=[pt], labels=[1], box=list(map(float, bx)), multimask=False)
                    m_pt = ms2[0]
                    t_pt = time.perf_counter() - t
                    for v, mm, tt in (("box", m_box, t_box), ("box_pt", m_pt, t_pt)):
                        mm = cs.clean_mask(mm)
                        m = metric_small(mm, gt)
                        sam_rows.append(dict(set=s, id=i, variant="yolo_" + v + "_sam2", n_inst=len(inst),
                                             t=dt_y + tt, **{k: m[k] for k in KEYS}))
            # Mirra with SAM 2 (box + point), saved separately
            for i, (bgr, inst, dt) in mirra_masks.items():
                if not inst:
                    continue
                pm, bx = pick(inst, chosen, bgr.shape[:2])
                if chosen == "union":
                    bx = [min(b[0] for _, b, _ in inst), min(b[1] for _, b, _ in inst),
                          max(b[2] for _, b, _ in inst), max(b[3] for _, b, _ in inst)]
                sam.set_image(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
                pt = interior_point(pm) if pm.any() else [int((bx[0] + bx[2]) / 2), int((bx[1] + bx[3]) / 2)]
                ms2, _ = sam.predict(points=[pt], labels=[1], box=list(map(float, bx)), multimask=False)
                mm = cs.clean_mask(ms2[0])
                d = OUTD / "mirra_sam2" / i
                d.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(d / "mask.png"), cs.to_u8(mm))
                cv2.imwrite(str(d / "overlay.jpg"), cs.overlay(bgr, mm))
            sam.unload()
        del model
        cs.free_gpu()

    # ---- summaries ----
    allrows = rows + sam_rows
    tag = a.tag
    with open(OUTD / f"per_image_{a.label}{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0].keys()))
        w.writeheader()
        w.writerows(allrows)
    sets_all = ["val_viton_cloth", "val_viton_person", "val_fashionpedia", "viton_cloth", "viton_person", "fashionpedia"]
    variants = list(dict.fromkeys(r["variant"] for r in allrows))
    summ = []
    for v in variants:
        for st in sets_all:
            x = [r for r in allrows if r["set"] == st and r["variant"] == v]
            if not x:
                continue
            d = dict(set=st, method=f"{a.label}:{v}", n=len(x),
                     iou=np.mean([r["iou"] for r in x]), bf1=np.mean([r["boundary_f@1.0%"] for r in x]),
                     hd95=np.mean([r["hd95_pct_diag"] for r in x]), leakage=np.mean([r["leakage"] for r in x]),
                     miss=np.mean([r["miss"] for r in x]), fail=np.mean([r["iou"] < 0.1 for r in x]),
                     time_s=np.mean([r["t"] for r in x]))
            summ.append(d)
    with open(OUTD / f"public_scores{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys()))
        w.writeheader()
        w.writerows(summ)
    out = {"chosen_variant": chosen, "val_macro_iou": val_macro, "weights": a.weights, "conf": a.conf}
    for v in variants:
        tests = [d for d in summ if d["method"].endswith(":" + v) and d["set"] in ("viton_cloth", "viton_person", "fashionpedia")]
        if len(tests) == 3:
            out[v] = {"macro_iou": float(np.mean([d["iou"] for d in tests])),
                      "macro_bf1": float(np.mean([d["bf1"] for d in tests])),
                      "macro_fail": float(np.mean([d["fail"] for d in tests])),
                      "time_s": float(np.mean([d["time_s"] for d in tests])),
                      **{d["set"]: d["iou"] for d in tests}}
    out["mirra_times_s"] = {i: v[2] for i, v in mirra_masks.items()}
    (OUTD / f"eval_summary{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
