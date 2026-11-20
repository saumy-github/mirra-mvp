"""Shared helpers for the P16 (multi-view) experiments.

Paths, label maps, image padding, text prompts and the three image-feature backbones
(SigLIP 2, CLIP ViT-L/14, Marqo-FashionSigLIP).  GPU use is wrapped by the callers in
`with gpu_lock("p16"):` blocks.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
CV = REPO / "product_ingestion" / "CV"
OUT = CV / "out" / "p16_multiview"
FEAT = OUT / "features"
INSHOP = CV / "data" / "deepfashion_inshop_filtered" / "data"
VITON = CV / "data" / "vitonhd_test" / "data"
MIRRA = REPO / "product_ingestion" / "input"
sys.path.insert(0, str(CV / "scripts"))

BACKBONES = {
    "siglip2": "google/siglip2-base-patch16-224",
    "clipL": "openai/clip-vit-large-patch14",
    "marqo": "hf-hub:Marqo/marqo-fashionSigLIP",
}

# In-shop file-name suffix -> (fine label, class used for training)
FINE = {"1_front": "front", "4_full": "full", "3_back": "back", "2_side": "side",
        "7_additional": "additional", "6_flat": "flat"}
# 4 view classes: front (1_front + 4_full), back, side, additional
VIEW_CLASSES = ["front", "back", "side", "additional"]
FINE_TO_VIEW = {"front": "front", "full": "front", "back": "back", "side": "side",
                "additional": "additional", "flat": "front"}

# zero-shot prompt ensembles (positive phrasing only)
VIEW_PROMPTS = {
    "front": ["a photo of the front of a garment", "the front view of a piece of clothing",
              "a person wearing clothes, seen from the front", "front view product photo of clothing"],
    "back": ["a photo of the back of a garment", "the back view of a piece of clothing",
             "a person wearing clothes, seen from behind", "rear view product photo of clothing"],
    "side": ["a photo of the side of a garment", "a side view of a piece of clothing",
             "a person wearing clothes, seen in profile from the side"],
    "additional": ["a close-up photo of a garment detail", "a close-up of fabric, print or neckline",
                   "a macro photo of clothing texture", "a detail shot of a piece of clothing"],
    "other": ["a size chart for clothing", "a clothing label or tag", "product packaging",
              "a table of measurements"],
}
PRES_PROMPTS = {
    "flat": ["a flat lay photo of a garment on a plain background", "a product photo of a folded or laid-flat piece of clothing",
             "a garment photographed alone on a white background"],
    "mannequin": ["a garment displayed on a mannequin", "a ghost mannequin product photo of clothing"],
    "person": ["a photo of a person wearing clothes", "a model wearing a garment", "a person posing in an outfit"],
}


def pad_square(im: Image.Image) -> Image.Image:
    """Pad to a square with the median border colour (keeps the aspect ratio)."""
    im = im.convert("RGB")
    w, h = im.size
    if w == h:
        return im
    a = np.asarray(im)
    border = np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]], 0)
    col = tuple(int(v) for v in np.median(border, 0))
    s = max(w, h)
    out = Image.new("RGB", (s, s), col)
    out.paste(im, ((s - w) // 2, (s - h) // 2))
    return out


def inshop_meta(split: str):
    """Metadata only (no image bytes): list of dicts relpath, item, fine, view."""
    import pyarrow.parquet as pq
    rel = pq.read_table(INSHOP / f"{split}-00000-of-00001.parquet", columns=["image_relpath"]).column(0).to_pylist()
    rows = []
    for r in rel:
        m = re.search(r"(id_\d+)/\d+_(\d_\w+)\.jpg", r)
        fine = FINE[m.group(2)]
        rows.append({"relpath": r, "item": m.group(1), "fine": fine, "view": FINE_TO_VIEW[fine]})
    return rows


def iter_inshop_images(split: str, batch_size: int = 128):
    """Yield lists of PIL images in file order, decoding one parquet batch at a time (low memory)."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(INSHOP / f"{split}-00000-of-00001.parquet")
    for b in pf.iter_batches(batch_size=batch_size, columns=["image"]):
        yield [Image.open(io.BytesIO(d["bytes"])).convert("RGB") for d in b.column(0).to_pylist()]


def iter_viton_images(kind: str, n: int = 800, batch_size: int = 64):
    """Yield lists of PIL images (kind 'cloth' or 'image'), a fixed random subset of n rows (seed 0).
    Metadata order: file order of the two parquet files, selected rows ascending."""
    import pyarrow.parquet as pq
    files = sorted(VITON.glob("*.parquet"))
    counts = [pq.ParquetFile(f).metadata.num_rows for f in files]
    idx = set(np.random.RandomState(0).permutation(sum(counts))[:n].tolist())
    off = 0
    for f, c in zip(files, counts):
        pf = pq.ParquetFile(f)
        pos = off
        for b in pf.iter_batches(batch_size=batch_size, columns=[kind]):
            vals = b.column(0).to_pylist()
            sel = [Image.open(io.BytesIO(v["bytes"])).convert("RGB") for k, v in enumerate(vals) if pos + k in idx]
            pos += len(vals)
            if sel:
                # shrink big product photos early to save RAM
                yield [x.resize((x.width // 2, x.height // 2)) if max(x.size) > 800 else x for x in sel]
        off += c


def mirra_images():
    out = []
    for d in sorted(MIRRA.glob("c_00*")):
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                out.append(p)
    return out


# approximate truth for the 5 Mirra photos (from the task description)
MIRRA_TRUTH = {
    "c_001": {"view": "front", "pres": "person"},
    "c_002": {"view": "back", "pres": "flat"},
    "c_003": {"view": "front", "pres": "person"},
    "c_004": {"view": "front", "pres": "flat"},
    "c_005": {"view": "front", "pres": "person"},
}


class Backbone:
    """Wraps a backbone: encode_images(list[PIL]) and encode_texts(list[str]) -> L2-normalised float32."""

    def __init__(self, key: str, device: str = "cuda"):
        import torch
        self.key, self.device, self.torch = key, device, torch
        name = BACKBONES[key]
        if key == "marqo":
            import open_clip
            self.model, _, self.pre = open_clip.create_model_and_transforms(name)
            self.tok = open_clip.get_tokenizer(name)
        else:
            from transformers import AutoModel, AutoProcessor
            self.model = AutoModel.from_pretrained(name, torch_dtype=torch.float16)
            self.proc = AutoProcessor.from_pretrained(name)
        self.model.eval().to(device)
        if key == "marqo":
            self.model.half()

    @property
    def dim(self):
        return self.encode_texts(["a"]).shape[1]

    def encode_images(self, ims, bs: int = 64):
        torch = self.torch
        outs = []
        for i in range(0, len(ims), bs):
            batch = [pad_square(x).resize((256, 256), Image.BICUBIC) for x in ims[i:i + bs]]
            with torch.no_grad():
                if self.key == "marqo":
                    x = torch.stack([self.pre(b) for b in batch]).to(self.device).half()
                    f = self.model.encode_image(x)
                else:
                    px = self.proc(images=batch, return_tensors="pt")["pixel_values"].to(self.device).half()
                    f = self.model.get_image_features(pixel_values=px)
            f = f.float()
            f = f / f.norm(dim=-1, keepdim=True)
            outs.append(f.cpu().numpy())
        return np.concatenate(outs, 0)

    def encode_texts(self, texts):
        torch = self.torch
        with torch.no_grad():
            if self.key == "marqo":
                t = self.tok(texts).to(self.device)
                f = self.model.encode_text(t)
            else:
                kw = dict(padding="max_length", max_length=64) if self.key == "siglip2" else dict(padding=True)
                t = self.proc(text=texts, return_tensors="pt", **kw).to(self.device)
                t = {k: v for k, v in t.items() if k in ("input_ids", "attention_mask")}
                if self.key == "siglip2":
                    t.pop("attention_mask", None)
                f = self.model.get_text_features(**t)
        f = f.float()
        f = f / f.norm(dim=-1, keepdim=True)
        return f.cpu().numpy()

    def close(self):
        del self.model
        import gc
        gc.collect()
        self.torch.cuda.empty_cache()


def loadf(path):
    """Load a cached feature file (float16 on disk) as float32."""
    return np.load(path).astype(np.float32)
