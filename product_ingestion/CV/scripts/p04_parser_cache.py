"""P04: run the SegFormer clothes parser (sayeed99/segformer_b3_clothes, cached locally) once and cache label maps.

Mirra photos  -> out/p04_colour/parser_cache/mirra/<cloth>.png      (uint8 label map, photo size)
FPI subset    -> out/p04_colour/parser_cache/fpi_labels.npz          (id -> uint8 label map at the 60x80 size)

Labels: 0 Background 1 Hat 2 Hair 3 Sunglasses 4 Upper-clothes 5 Skirt 6 Pants 7 Dress 8 Belt 9 Left-shoe
10 Right-shoe 11 Face 12 Left-leg 13 Right-leg 14 Left-arm 15 Right-arm 16 Bag 17 Scarf.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_parser_cache.py [--fpi]
GPU is used under gpu_lock("p04") and freed afterwards.
"""
from __future__ import annotations
import argparse, gc, json, os, sys
from pathlib import Path
import cv2, numpy as np

os.environ.setdefault("HF_HUB_OFFLINE", "1")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from gpu_lock import gpu_lock  # noqa: E402

CACHE = ROOT / "out" / "p04_colour" / "parser_cache"
MODEL = "sayeed99/segformer_b3_clothes"


def load_model():
    import torch
    from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor
    proc = SegformerImageProcessor.from_pretrained(MODEL)
    model = AutoModelForSemanticSegmentation.from_pretrained(MODEL).to("cuda").eval()
    return torch, proc, model


def parse(torch, proc, model, rgb, upscale_to=None):
    h, w = rgb.shape[:2]
    im = rgb
    if upscale_to and max(h, w) < upscale_to:
        s = upscale_to / max(h, w)
        im = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_CUBIC)
    inp = proc(images=im, return_tensors="pt").to("cuda")
    with torch.no_grad():
        lg = model(**inp).logits
        lg = torch.nn.functional.interpolate(lg, size=(h, w), mode="bilinear", align_corners=False)
    return lg.argmax(1)[0].cpu().numpy().astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fpi", action="store_true"); a = ap.parse_args()
    import torch
    labels = json.loads((ROOT / "out" / "p00_baseline" / "reference" / "labels.json").read_text(encoding="utf-8"))["cloths"]
    with gpu_lock("p04"):
        torch_, proc, model = load_model()
        try:
            (CACHE / "mirra").mkdir(parents=True, exist_ok=True)
            for c, e in labels.items():
                bgr = cv2.imread(e["image"], cv2.IMREAD_COLOR)
                lab = parse(torch_, proc, model, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), upscale_to=512)
                cv2.imwrite(str(CACHE / "mirra" / f"{c}.png"), lab)
                print(c, bgr.shape, {int(k): int(v) for k, v in zip(*np.unique(lab, return_counts=True))})
            if a.fpi:
                import pandas as pd
                sub = pd.read_csv(ROOT / "out" / "p04_colour" / "fpi_subset" / "labels.csv")
                out = {}
                for i in sub.id.tolist():
                    bgr = cv2.imread(str(ROOT / "out" / "p04_colour" / "fpi_subset" / "images" / f"{i}.png"))
                    out[str(i)] = parse(torch_, proc, model, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), upscale_to=384)
                np.savez_compressed(CACHE / "fpi_labels.npz", **out)
                print("fpi parsed", len(out))
        finally:
            del model
            gc.collect(); torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
