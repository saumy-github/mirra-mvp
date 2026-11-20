"""P00: candidate garment masks for the 5 Mirra photos, used to build the reference masks.

For each photo it saves:
  - the 3 raw SAM 2 candidates for the current prompt (centre point + 4 corner background
    points), with SAM 2's predicted IoU for each, before any clean-up;
  - the SegFormer clothes-parser label map (sayeed99/segformer_b3_clothes) and its
    "Upper-clothes" mask;
  - an overlay sheet to choose and check the reference by eye.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p00_reference_candidates.py
Out:  product_ingestion/CV/out/p00_baseline/reference_candidates/<cloth>/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gpu_lock import gpu_lock  # noqa: E402

REPO = HERE.parents[2]
INPUT = REPO / "product_ingestion" / "input"
OUT = HERE.parent / "out" / "p00_baseline" / "reference_candidates"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


def first_image(cloth: str) -> Path:
    files = sorted(p for p in (INPUT / cloth).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    return files[0]


def overlay(rgb: np.ndarray, mask: np.ndarray, colour=(255, 0, 0)) -> np.ndarray:
    out = rgb.copy().astype(np.float32)
    m = mask > 0
    out[m] = 0.55 * out[m] + 0.45 * np.array(colour, np.float32)
    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = out.astype(np.uint8)
    cv2.drawContours(out, cnts, -1, (255, 255, 0), 2)
    return out


def label_strip(img: np.ndarray, text: str) -> np.ndarray:
    bar = np.full((28, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def main() -> None:
    from transformers import (AutoModelForSemanticSegmentation, SegformerImageProcessor,
                              Sam2Model, Sam2Processor)

    OUT.mkdir(parents=True, exist_ok=True)
    images = {c: Image.open(first_image(c)).convert("RGB") for c in CLOTHS}
    results: dict = {}

    with gpu_lock("p00_reference"):
        proc = Sam2Processor.from_pretrained("facebook/sam2-hiera-large")
        model = Sam2Model.from_pretrained("facebook/sam2-hiera-large").to("cuda").eval()
        for c, pil in images.items():
            W, H = pil.size
            pts = [[W // 2, H // 2], [0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1]]
            labels = [1, 0, 0, 0, 0]
            inputs = proc(images=pil, input_points=[[pts]], input_labels=[[labels]], return_tensors="pt")
            inputs = {k: v.to("cuda") if hasattr(v, "to") else v for k, v in inputs.items()}
            with torch.no_grad():
                o = model(**inputs)
            masks = o.pred_masks.cpu().float()
            while masks.dim() > 3:
                masks = masks.squeeze(0)
            scores = o.iou_scores.cpu().flatten().tolist()
            cand = []
            for i in range(masks.shape[0]):
                m = F.interpolate(masks[i][None, None], size=(H, W), mode="bilinear", align_corners=False).squeeze()
                cand.append((m > 0).numpy().astype(np.uint8) * 255)
            results[c] = {"sam2_iou_scores": scores, "sam2": cand}
        del model
        torch.cuda.empty_cache()

        sp = SegformerImageProcessor.from_pretrained("sayeed99/segformer_b3_clothes")
        seg = AutoModelForSemanticSegmentation.from_pretrained("sayeed99/segformer_b3_clothes").to("cuda").eval()
        id2label = seg.config.id2label
        for c, pil in images.items():
            W, H = pil.size
            inputs = sp(images=pil, return_tensors="pt").to("cuda")
            with torch.no_grad():
                logits = seg(**inputs).logits
            up = F.interpolate(logits, size=(H, W), mode="bilinear", align_corners=False)
            lab = up.argmax(1)[0].cpu().numpy().astype(np.uint8)
            results[c]["parse"] = lab
        del seg
        torch.cuda.empty_cache()

    meta = {"id2label": {int(k): v for k, v in id2label.items()}}
    upper_id = [k for k, v in meta["id2label"].items() if v.lower() == "upper-clothes"][0]
    for c, pil in images.items():
        rgb = np.array(pil)
        d = OUT / c
        d.mkdir(parents=True, exist_ok=True)
        r = results[c]
        tiles = []
        for i, m in enumerate(r["sam2"]):
            cv2.imwrite(str(d / f"sam2_cand{i}.png"), m)
            area = float((m > 0).mean() * 100)
            tiles.append(label_strip(overlay(rgb, m), f"SAM2 cand{i} iou={r['sam2_iou_scores'][i]:.3f} area={area:.1f}%"))
        lab = r["parse"]
        cv2.imwrite(str(d / "parse_labels.png"), lab)
        upper = (lab == upper_id).astype(np.uint8) * 255
        cv2.imwrite(str(d / "segformer_upper.png"), upper)
        tiles.append(label_strip(overlay(rgb, upper, (0, 200, 0)), f"SegFormer upper-clothes area={(upper > 0).mean() * 100:.1f}%"))
        present = {meta["id2label"][int(v)]: round(float((lab == v).mean() * 100), 2) for v in np.unique(lab)}
        h = max(t.shape[0] for t in tiles)
        tiles = [np.vstack([t, np.full((h - t.shape[0], t.shape[1], 3), 255, np.uint8)]) for t in tiles]
        sheet = np.hstack(tiles)
        scale = min(1.0, 2400 / sheet.shape[1])
        sheet = cv2.resize(sheet, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(d / "candidates_sheet.jpg"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
        meta[c] = {"image": str(first_image(c)), "size_wh": list(pil.size),
                   "sam2_iou_scores": r["sam2_iou_scores"], "parse_classes_percent": present}
    (OUT / "candidates_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({c: meta[c] for c in CLOTHS}, indent=1)[:3000])


if __name__ == "__main__":
    main()
