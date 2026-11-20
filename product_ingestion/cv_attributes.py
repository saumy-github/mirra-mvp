"""Trained garment-attribute readers (textile pattern, sleeve length, neckline) for Mirra product photos.

Part of the CV project (plan P07). Frozen image backbones (SigLIP 2, Marqo-FashionSigLIP) give a
feature vector; small classifiers trained on Fashionpedia labels (see models/attributes/README.md) turn it into
one label per attribute group.

    from product_ingestion.cv_attributes import predict_attributes
    out = predict_attributes("product_ingestion/input/c_001/....jpg")
    out["pattern"]["label"], out["pattern"]["probs"]       # e.g. "text", {"plain": 0.1, ...}
    out = predict_attributes(rgba_cutout_array)             # RGBA cut-out (alpha is used as the mask)
    out = predict_attributes(photo, mask=garment_mask)      # photo + 0/255 mask of the garment

Input: file path, PIL image, or numpy array (3-channel = BGR like OpenCV, 4-channel = BGRA). A mask (or alpha)
removes the background (set to grey 128, as in training) and the garment bounding box is cropped.
Models load lazily on first use, on the GPU if one is free enough, otherwise on the CPU.
Needs network access only the first time a backbone is not yet in the Hugging Face cache.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models" / "attributes"
GROUPS = ("pattern", "sleeve", "neckline")
_BACKBONE_CACHE: dict = {}
_BUNDLE_CACHE: dict = {}


# ------------------------------------------------------------------ images
def _to_rgb_and_mask(image, mask=None):
    """Return an RGB uint8 array and an optional bool garment mask."""
    from PIL import Image
    if isinstance(image, (str, Path)):
        im = Image.open(image)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
        arr = np.array(im)
        if arr.ndim == 3 and arr.shape[2] == 4:
            rgb, alpha = arr[..., :3], arr[..., 3]
        else:
            rgb, alpha = np.array(im.convert("RGB")), None
    elif isinstance(image, Image.Image):
        arr = np.array(image.convert("RGBA")) if image.mode in ("RGBA", "LA") else np.array(image.convert("RGB"))
        rgb, alpha = (arr[..., :3], arr[..., 3]) if arr.shape[2] == 4 else (arr, None)
    else:
        arr = np.asarray(image)
        if arr.ndim == 3 and arr.shape[2] == 4:
            rgb, alpha = arr[..., [2, 1, 0]], arr[..., 3]
        elif arr.ndim == 3:
            rgb, alpha = arr[..., ::-1], None
        else:
            rgb, alpha = np.stack([arr] * 3, -1), None
    m = None
    if mask is not None:
        m = np.asarray(mask) > 0
    elif alpha is not None and (alpha < 250).any():
        m = alpha > 127
    return np.ascontiguousarray(rgb).astype(np.uint8), m


def _pad_square(a, fill=128):
    h, w = a.shape[:2]
    s = max(h, w)
    o = np.full((s, s, 3), fill, np.uint8)
    o[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = a
    return o


def _bbox(mask, shape):
    if mask is None or mask.sum() < 50:
        return 0, 0, shape[1], shape[0]
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def make_crops(image, mask=None) -> dict:
    """The three crops the classifiers were trained on (see models/attributes/README.md)."""
    rgb, m = _to_rgb_and_mask(image, mask)
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = _bbox(m, rgb.shape)
    bw, bh = x1 - x0, y1 - y0
    mx, my = int(0.05 * bw), int(0.05 * bh)
    X0, Y0, X1, Y1 = max(0, x0 - mx), max(0, y0 - my), min(w, x1 + mx), min(h, y1 + my)
    raw = rgb[Y0:Y1, X0:X1]
    if m is not None:
        masked = rgb.copy()
        masked[~m] = 128
        masked = masked[Y0:Y1, X0:X1]
        sleeve_src = masked          # cut-outs have no background left; keep the same convention
    else:
        masked, sleeve_src = raw, raw
    # neckline: square around the expected neckline position (median over Fashionpedia val garments)
    s = 0.98 * bw
    cx, cy = x0 + bw / 2, y0 + 0.117 * bw
    n0, m0 = int(max(0, cx - s / 2)), int(max(0, cy - s / 2))
    n1, m1 = int(min(w, cx + s / 2)), int(min(h, cy + s / 2))
    neck_src = (rgb if m is None else np.where(m[..., None], rgb, 128).astype(np.uint8))[m0:m1, n0:n1]
    return {"pattern": _pad_square(masked), "sleeve": _pad_square(sleeve_src),
            "neckline": _pad_square(neck_src)}


# ---------------------------------------------------------------- backbones
def _pick_device(want_gpu=True):
    import torch
    if want_gpu and torch.cuda.is_available():
        try:
            free, _ = torch.cuda.mem_get_info()
            if free > 1.5e9:
                return "cuda"
        except Exception:  # noqa: BLE001
            pass
    return "cpu"


def _load_backbone(name, device):
    key = (name, device)
    if key in _BACKBONE_CACHE:
        return _BACKBONE_CACHE[key]
    import torch
    dt = torch.float16 if device == "cuda" else torch.float32
    if name == "siglip2":
        from transformers import AutoModel, AutoProcessor
        mid = "google/siglip2-base-patch16-224"
        m = AutoModel.from_pretrained(mid, torch_dtype=dt).to(device).eval()
        pr = AutoProcessor.from_pretrained(mid)

        def enc(ims):
            px = pr(images=ims, return_tensors="pt")["pixel_values"].to(device, dt)
            return m.get_image_features(pixel_values=px)

        def txt(t):
            tt = pr(text=t, padding="max_length", max_length=64, return_tensors="pt")
            return m.get_text_features(**{k: v.to(device) for k, v in tt.items()})
    elif name == "fashion_siglip":
        import open_clip
        m, _, pre = open_clip.create_model_and_transforms("hf-hub:Marqo/marqo-fashionSigLIP")
        m = m.to(device, dt).eval()
        tok = open_clip.get_tokenizer("hf-hub:Marqo/marqo-fashionSigLIP")

        def enc(ims):
            return m.encode_image(torch.stack([pre(i) for i in ims]).to(device, dt))

        def txt(t):
            return m.encode_text(tok(t).to(device))
    else:
        raise ValueError(name)
    _BACKBONE_CACHE[key] = (enc, txt)
    return _BACKBONE_CACHE[key]


def release_models():
    """Free backbones (call when done, e.g. before a GPU-heavy step)."""
    import gc
    _BACKBONE_CACHE.clear()
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def _load_bundle(group):
    if group not in _BUNDLE_CACHE:
        with open(MODEL_DIR / f"{group}.pkl", "rb") as f:
            _BUNDLE_CACHE[group] = pickle.load(f)
    return _BUNDLE_CACHE[group]


# ---------------------------------------------------------------- predict
def predict_attributes(image, mask=None, groups=GROUPS, device: str | None = None, fuse_zero_shot: bool = True) -> dict:
    """Return {group: {"label": str, "confidence": float, "probs": {class: p}}} for each requested group.

    groups: subset of ("pattern", "sleeve", "neckline"); "sleeve3" (short/mid/long) is also available if its
    model file exists. device: "cuda" / "cpu" / None (auto).
    """
    import torch
    from PIL import Image
    crops = make_crops(image, mask)
    dev = device or _pick_device()
    bundles = {g: _load_bundle(g) for g in groups}
    feats: dict = {}
    result = {}
    for g in groups:
        b = bundles[g]
        crop_key = "sleeve" if g.startswith("sleeve") else g
        pim = Image.fromarray(crops[crop_key])
        fs = []
        for bb in b["backbones"]:
            if (bb, crop_key) not in feats:
                enc, _ = _load_backbone(bb, dev)
                with torch.no_grad():
                    e = enc([pim]).float()
                feats[(bb, crop_key)] = (e / e.norm(dim=-1, keepdim=True)).cpu().numpy()[0]
            fs.append(feats[(bb, crop_key)])
        x = np.concatenate(fs)[None]      # concat of unit-norm vectors, as in training
        p = np.zeros(b["n_classes"])
        p[b["sk_model"].classes_] = b["sk_model"].predict_proba(x)[0]
        if fuse_zero_shot and b.get("zs_weight", 0) > 0:
            zs = fs[0] @ b["text_emb"][b["backbones"][0]].T
            ez = np.exp((zs - zs.max()) * 100)
            ez /= ez.sum()
            p = np.log(p + 1e-6) + b["zs_weight"] * np.log(ez + 1e-6)
            p = np.exp(p - p.max())
            p /= p.sum()
        i = int(np.argmax(p))
        result[g] = {"label": b["classes"][i], "confidence": float(p[i]),
                     "probs": {c: float(v) for c, v in zip(b["classes"], p)}}
    return result


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(predict_attributes(sys.argv[1]), indent=1))
