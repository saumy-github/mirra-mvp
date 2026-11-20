"""P07 step 2: extract frozen-backbone features (and class-prompt text embeddings) for every crop.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_extract.py --backbone siglip2 --splits val train

Backbones: siglip2 (google/siglip2-base-patch16-224), clip_l14 (openai/clip-vit-large-patch14),
           fashion_siglip (open_clip hf-hub:Marqo/marqo-fashionSigLIP).
Features are L2-normalised float32, saved as out/p07_attributes/feats/<backbone>__<split>__<group>[_variant].npy
in the row order of manifest_<split>.csv restricted to that group.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from PIL import Image
from p07_common import *  # noqa
from p07_prompts import PROMPTS  # noqa
from gpu_lock import gpu_lock

ap = argparse.ArgumentParser()
ap.add_argument("--backbone", required=True)
ap.add_argument("--splits", nargs="+", default=["val"])
ap.add_argument("--bs", type=int, default=24)
a = ap.parse_args()

FEAT = OUT / "feats"
FEAT.mkdir(parents=True, exist_ok=True)


def load_backbone(name, D):
    import torch
    dev = "cpu"
    if name == "siglip2":
        from transformers import AutoModel, AutoProcessor
        mid = "google/siglip2-base-patch16-224"
        m = AutoModel.from_pretrained(mid, torch_dtype=torch.float16).eval()
        pr = AutoProcessor.from_pretrained(mid)
        img_fn = lambda ims: m.get_image_features(**{k: v.to(D["dev"]).half() if v.dtype.is_floating_point else v.to(D["dev"]) for k, v in pr(images=ims, return_tensors="pt").items()})
        def txt_fn(txts):
            t = pr(text=txts, padding="max_length", max_length=64, return_tensors="pt")
            return m.get_text_features(**{k: v.to(D["dev"]) for k, v in t.items()})
        return m, img_fn, txt_fn
    if name == "clip_l14":
        from transformers import CLIPModel, CLIPProcessor
        mid = "openai/clip-vit-large-patch14"
        m = CLIPModel.from_pretrained(mid, torch_dtype=torch.float16).eval()
        pr = CLIPProcessor.from_pretrained(mid)
        img_fn = lambda ims: m.get_image_features(pixel_values=pr(images=ims, return_tensors="pt")["pixel_values"].to(D["dev"]).half())
        def txt_fn(txts):
            t = pr(text=txts, padding=True, return_tensors="pt")
            return m.get_text_features(**{k: v.to(D["dev"]) for k, v in t.items()})
        return m, img_fn, txt_fn
    if name == "fashion_siglip":
        import open_clip
        m, _, pre = open_clip.create_model_and_transforms("hf-hub:Marqo/marqo-fashionSigLIP")
        m = m.half().eval()
        tok = open_clip.get_tokenizer("hf-hub:Marqo/marqo-fashionSigLIP")
        img_fn = lambda ims: m.encode_image(torch.stack([pre(i) for i in ims]).to(D["dev"]).half())
        txt_fn = lambda txts: m.encode_text(tok(txts).to(D["dev"]))
        return m, img_fn, txt_fn
    raise ValueError(name)


def main():
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    jobs = []   # (split, group, variant, paths)
    for sp in a.splits:
        mf = OUT / f"manifest_{sp}.csv"
        if not mf.exists():
            print("missing", mf)
            continue
        df = pd.read_csv(mf)
        for g in ["pattern", "sleeve", "neckline"]:
            sub = df[df.group == g]
            if not len(sub):
                continue
            for v in (["mask", "raw"] if g == "pattern" else [None]):
                tag = f"{g}_{v}" if v else g
                f = FEAT / f"{a.backbone}__{sp}__{tag}.npy"
                if f.exists():
                    print("skip", f.name)
                    continue
                jobs.append((sp, tag, f, [crop_path(OUT / "crops", sp, g, c, v) for c in sub.crop_id]))
    need_text = not (FEAT / f"{a.backbone}__text__pattern.npy").exists()
    if not jobs and not need_text:
        return
    t0 = time.time()
    D = {"dev": "cpu"}
    m, img_fn, txt_fn = load_backbone(a.backbone, D)     # download / load on CPU outside the lock
    with gpu_lock("p07"):
        m.to(dev)
        D["dev"] = dev
        with torch.no_grad():
            if need_text:
                for grp, (classes, temps) in PROMPTS.items():
                    embs = []
                    for c, descs in classes.items():
                        txts = [t.format(d) for d in descs for t in temps]
                        e = txt_fn(txts).float()
                        e = e / e.norm(dim=-1, keepdim=True)
                        e = e.mean(0)
                        embs.append((e / e.norm()).cpu().numpy())
                    np.save(FEAT / f"{a.backbone}__text__{grp}.npy", np.stack(embs).astype(np.float32))
            for sp, tag, f, paths in jobs:
                feats = []
                for i in range(0, len(paths), a.bs):
                    ims = [Image.open(p).convert("RGB") for p in paths[i:i + a.bs]]
                    e = img_fn(ims).float()
                    feats.append((e / e.norm(dim=-1, keepdim=True)).cpu().numpy())
                np.save(f, np.concatenate(feats).astype(np.float16))
                print(f"{a.backbone} {sp} {tag}: {len(paths)} crops, {time.time() - t0:.0f}s", flush=True)
        del m
        import gc
        gc.collect()
        torch.cuda.empty_cache()


main()
