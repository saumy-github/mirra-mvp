"""P16: several unlabelled photos of one garment -> which is front, back, side, detail, other.

Public API (see also CV/out/p16_multiview/REPORT.md):

    from multi_view import assign_views, write_view_assignment_json
    va = assign_views(["a.jpg", "b.png", "c.jpg"])       # any order, any names, 1..N photos
    va.front, va.back                                    # paths (back may be None)
    write_view_assignment_json(va, run_dir / "image_info" / "view_assignment.json")

What it does
  1. One frozen image-embedding backbone (default: the one stored in models/view_classifier/) is run once
     per photo.  A small trained classifier (models/view_classifier/view_clf.joblib) turns the embedding into
     probabilities for front / back / side / additional (close-up or alternate shot); a second small classifier
     says flat-lay product photo versus on-person; a zero-shot score flags non-garment pages (size chart, label).
  2. Cheap image cues per photo: blur (variance of the Laplacian), garment area (pixels unlike the border colour),
     face found (OpenCV Haar), and a colour descriptor.
  3. Same-garment check: a pair classifier (embedding cosine + colour-histogram overlap) and a cut-aware subset
     search find the largest group of photos that look like one garment; the others are `outliers`.
  4. Joint decision: front and back are chosen together over *different* photos (best sum of log-probabilities,
     with a small usability term).  A back is reported only if its probability passes `back_threshold`.

With one photo the result is that photo as `front` (same as the old behaviour); with no model files or no
torch the function falls back to the first photo as front (`method == "fallback_first_image"`).

CLI:  python product_ingestion/multi_view.py <folder_or_images...> [--out view_assignment.json]
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent / "models" / "view_classifier"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
VIEW_CLASSES = ["front", "back", "side", "additional"]

HF_NAMES = {
    "siglip2": "google/siglip2-base-patch16-224",
    "clipL": "openai/clip-vit-large-patch14",
    "marqo": "hf-hub:Marqo/marqo-fashionSigLIP",
}

# ---------------------------------------------------------------------------------------------
# data classes
# ---------------------------------------------------------------------------------------------


@dataclass
class PhotoInfo:
    path: str
    view: str = "front"                 # front | back | side | additional | other
    view_probs: dict = field(default_factory=dict)
    presentation: str = "unknown"       # flat | person | unknown
    presentation_probs: dict = field(default_factory=dict)
    other_prob: float = 0.0             # zero-shot probability of "not a garment photo" (size chart, label)
    blur: float = 0.0                   # variance of the Laplacian (512 px long side)
    garment_area: float = 0.0           # fraction of pixels unlike the border colour
    touches_frame: float = 0.0          # fraction of the 4 borders that hold garment-like pixels
    face_found: bool = False
    usability: float = 0.0              # 0..1
    same_garment_score: float = 1.0     # mean pair probability to the photos kept as the garment set
    is_outlier: bool = False
    role: str = "unassigned"            # front | back | side | detail | other | outlier | extra_front | unassigned


@dataclass
class ViewAssignment:
    photos: list = field(default_factory=list)       # list[PhotoInfo], same order as the input
    front: Optional[str] = None
    back: Optional[str] = None
    sides: list = field(default_factory=list)
    details: list = field(default_factory=list)
    others: list = field(default_factory=list)       # size charts, labels, packaging
    outliers: list = field(default_factory=list)     # photos of a different garment
    method: str = "trained"
    notes: list = field(default_factory=list)
    pair_same_prob: list = field(default_factory=list)  # N x N matrix (list of lists), empty for N<2

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def write_view_assignment_json(assignment: ViewAssignment, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assignment.to_dict(), indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------------
# cheap image cues (CPU)
# ---------------------------------------------------------------------------------------------

_FACE = None


def _face_cascade():
    global _FACE
    if _FACE is None:
        _FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _FACE


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


def _resize_long(rgb: np.ndarray, long_side: int) -> np.ndarray:
    h, w = rgb.shape[:2]
    s = long_side / max(h, w)
    if abs(s - 1) < 1e-6:
        return rgb
    return cv2.resize(rgb, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def foreground_mask(rgb: np.ndarray, thr: float = 28.0) -> np.ndarray:
    """Pixels that differ from the median border colour (a cheap background model)."""
    b = np.concatenate([rgb[:3].reshape(-1, 3), rgb[-3:].reshape(-1, 3), rgb[:, :3].reshape(-1, 3), rgb[:, -3:].reshape(-1, 3)], 0)
    med = np.median(b, 0)
    d = np.linalg.norm(rgb.astype(np.float32) - med.astype(np.float32), axis=2)
    m = (d > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m


def image_cues(rgb: np.ndarray) -> dict:
    """blur, garment_area, touches_frame, face_found, face_area, colour descriptor (72-d)."""
    img = _resize_long(rgb, 512)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    m = foreground_mask(img)
    area = float(m.mean())
    k = 3
    edges = [m[:k].mean(), m[-k:].mean(), m[:, :k].mean(), m[:, -k:].mean()]
    touches = float(np.mean([e > 0.08 for e in edges]))
    # face: Haar frontal cascade on the upscaled image (on-person photos are often 256 px or smaller)
    big = _resize_long(rgb, 512)
    g2 = cv2.cvtColor(big, cv2.COLOR_RGB2GRAY)
    faces = _face_cascade().detectMultiScale(g2, scaleFactor=1.1, minNeighbors=6, minSize=(max(24, big.shape[1] // 14),) * 2)
    face_area = 0.0
    if len(faces):
        face_area = float(max(w * h for (_, _, w, h) in faces)) / (big.shape[0] * big.shape[1])
    # colour descriptor on garment-like pixels
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    sel = m.astype(bool)
    if sel.mean() < 0.02:
        sel = np.ones_like(sel)
    L, A, B = lab[..., 0][sel], lab[..., 1][sel], lab[..., 2][sel]
    hab, _, _ = np.histogram2d(A, B, bins=8, range=[[0, 256], [0, 256]])
    hl, _ = np.histogram(L, bins=8, range=[0, 256])
    hab = hab.ravel() / max(hab.sum(), 1)
    hl = hl / max(hl.sum(), 1)
    return {"blur": blur, "garment_area": area, "touches_frame": touches, "face_found": bool(len(faces)),
            "face_area": face_area, "colour": np.concatenate([hab, hl]).astype(np.float32)}


def colour_overlap(c1: np.ndarray, c2: np.ndarray) -> tuple[float, float]:
    """Bhattacharyya coefficient of the a*b* part (64) and the L* part (8)."""
    return float(np.sqrt(c1[:64] * c2[:64]).sum()), float(np.sqrt(c1[64:] * c2[64:]).sum())


def pair_features(f1, f2, c1, c2) -> np.ndarray:
    ab, l = colour_overlap(c1, c2)
    return np.array([float(f1 @ f2), ab, l, ab * l], dtype=np.float32)


def usability_score(blur: float, area: float, touches: float) -> float:
    """0..1: sharp, large garment, not cut by the frame (touches_frame counts the 4 borders holding garment)."""
    s_blur = min(1.0, max(0.0, math.log10(blur + 1.0) / 2.7))     # ~500 variance -> 1
    s_area = min(1.0, area / 0.35)
    s_cut = 1.0 - 0.5 * min(touches, 1.0)
    return float(0.45 * s_blur + 0.35 * s_area + 0.20 * s_cut)


# ---------------------------------------------------------------------------------------------
# backbone + model bundle
# ---------------------------------------------------------------------------------------------

_CACHE: dict = {}


def load_bundle(model_dir: str | Path | None = None) -> dict:
    import joblib
    p = Path(model_dir) if model_dir else MODEL_DIR
    key = ("bundle", str(p))
    if key not in _CACHE:
        _CACHE[key] = joblib.load(p / "view_clf.joblib")
    return _CACHE[key]


class ImageEmbedder:
    """Frozen image-embedding backbone ('siglip2', 'clipL' or 'marqo'); L2-normalised float32 output."""

    def __init__(self, key: str, device: str = "auto"):
        import torch
        self.torch = torch
        self.key = key
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.half = device == "cuda"
        name = HF_NAMES[key]
        if key == "marqo":
            import open_clip
            self.model, _, self.pre = open_clip.create_model_and_transforms(name)
        else:
            from transformers import AutoModel, AutoProcessor
            self.model = AutoModel.from_pretrained(name, torch_dtype=torch.float16 if self.half else torch.float32)
            self.proc = AutoProcessor.from_pretrained(name)
        self.model.eval().to(device)
        if self.half and key == "marqo":
            self.model.half()

    def encode(self, pil_images: list, bs: int = 16) -> np.ndarray:
        torch = self.torch
        outs = []
        dt = torch.float16 if self.half else torch.float32
        for i in range(0, len(pil_images), bs):
            batch = [pad_square(x) for x in pil_images[i:i + bs]]
            with torch.no_grad():
                if self.key == "marqo":
                    x = torch.stack([self.pre(b) for b in batch]).to(self.device).to(dt)
                    f = self.model.encode_image(x)
                else:
                    px = self.proc(images=batch, return_tensors="pt")["pixel_values"].to(self.device).to(dt)
                    f = self.model.get_image_features(pixel_values=px)
            f = f.float()
            f = f / f.norm(dim=-1, keepdim=True)
            outs.append(f.cpu().numpy())
        return np.concatenate(outs, 0)

    def close(self):
        import gc
        del self.model
        gc.collect()
        if self.device == "cuda":
            self.torch.cuda.empty_cache()


def get_embedder(key: str, device: str = "auto", keep: bool = True) -> ImageEmbedder:
    ck = ("emb", key, device)
    if keep and ck in _CACHE:
        return _CACHE[ck]
    e = ImageEmbedder(key, device)
    if keep:
        _CACHE[ck] = e
    return e


# ---------------------------------------------------------------------------------------------
# set-level logic (pure numpy, works on cached features too)
# ---------------------------------------------------------------------------------------------


def _partitions(n: int):
    """All set partitions of range(n) as lists of label lists (restricted growth strings)."""
    def rec(i, labels, m):
        if i == n:
            yield list(labels)
            return
        for k in range(m + 1):
            labels.append(k)
            yield from rec(i + 1, labels, max(m, k + 1))
            labels.pop()
    yield from rec(0, [], 0)


def same_garment_subset(P: np.ndarray, rank_score: np.ndarray) -> list[int]:
    """Photos that belong to the main garment.

    Correlation clustering of the photos into groups: maximise the sum of (P_ij - 0.5) over pairs that share a
    group (exhaustive over all partitions for N <= 8, average-linkage merging above).  The main garment is the
    largest group; ties go to the group with the best rank_score (front-likeness x usability).  The rest are
    outliers.  P is the N x N matrix of 'same garment' probabilities.
    """
    n = len(P)
    if n == 1:
        return [0]
    W = P - 0.5
    np.fill_diagonal(W, 0.0)
    if n <= 8:
        best, best_val = None, -1e18
        for lab in _partitions(n):
            val = sum(W[i, j] for i in range(n) for j in range(i + 1, n) if lab[i] == lab[j])
            if val > best_val + 1e-12:
                best, best_val = lab, val
        groups = {}
        for i, l in enumerate(best):
            groups.setdefault(l, []).append(i)
        cl = list(groups.values())
    else:
        cl = [[i] for i in range(n)]
        while True:
            bm, bp = 0.5, None
            for x in range(len(cl)):
                for y in range(x + 1, len(cl)):
                    m = float(np.mean([P[i, j] for i in cl[x] for j in cl[y]]))
                    if m > bm:
                        bm, bp = m, (x, y)
            if bp is None:
                break
            x, y = bp
            cl[x] = cl[x] + cl[y]
            del cl[y]
    main = max(cl, key=lambda g: (len(g), float(sum(rank_score[g]))))
    return sorted(main)


def choose_front_back(pf: np.ndarray, pb: np.ndarray, usability: np.ndarray, allowed: list[int],
                      back_threshold: float = 0.5, usability_weight: float = 0.3):
    """Joint choice over different photos.  Returns (front_idx, back_idx or None, info)."""
    eps = 1e-4
    lf = np.log(np.clip(pf, eps, 1)) + usability_weight * usability
    lb = np.log(np.clip(pb, eps, 1)) + usability_weight * usability
    if len(allowed) == 1:
        return allowed[0], None, {"joint": False}
    best, bs = None, -1e18
    for i, j in itertools.permutations(allowed, 2):
        s = lf[i] + lb[j]
        if s > bs:
            best, bs = (i, j), s
    i, j = best
    # accept a back only if it is plausible; otherwise the front is the plain best front
    if pb[j] >= back_threshold:
        return i, j, {"joint": True, "joint_score": float(bs)}
    f = max(allowed, key=lambda k: lf[k])
    return f, None, {"joint": False, "best_back_prob": float(pb[j])}


def assemble(paths: list[str], view_probs: np.ndarray, pres_probs: np.ndarray, pres_classes: list[str],
             other_prob: np.ndarray, cues: list[dict], P: np.ndarray, params: dict, method: str) -> ViewAssignment:
    """Turn per-photo probabilities and the pair matrix into a ViewAssignment."""
    n = len(paths)
    back_thr = params.get("back_threshold", 0.5)
    uw = params.get("usability_weight", 0.3)
    other_thr = params.get("other_threshold", 0.6)
    usab = np.array([usability_score(c["blur"], c["garment_area"], c["touches_frame"]) for c in cues])
    photos = []
    for i, p in enumerate(paths):
        vp = dict(zip(VIEW_CLASSES, map(float, view_probs[i])))
        view = max(vp, key=vp.get)
        if other_prob[i] >= other_thr:
            view = "other"
        photos.append(PhotoInfo(path=p, view=view, view_probs=vp,
                                presentation=pres_classes[int(np.argmax(pres_probs[i]))] if len(pres_classes) else "unknown",
                                presentation_probs=dict(zip(pres_classes, map(float, pres_probs[i]))),
                                other_prob=float(other_prob[i]), blur=cues[i]["blur"],
                                garment_area=cues[i]["garment_area"], touches_frame=cues[i]["touches_frame"],
                                face_found=bool(cues[i]["face_found"]), usability=float(usab[i])))
    va = ViewAssignment(photos=photos, method=method)
    garment_like = [i for i in range(n) if photos[i].view != "other"]
    if not garment_like:                      # everything looks like a chart: fall back to all photos
        garment_like = list(range(n))
        va.notes.append("all photos look like non-garment pages; treating all as garment photos")
    # same-garment set among the garment-like photos
    rank = view_probs[:, 0] * (0.5 + usab)
    if n >= 2:
        sub = np.array(garment_like)
        Psub = P[np.ix_(sub, sub)]
        keep_local = same_garment_subset(Psub, rank[sub])
        keep = [int(sub[k]) for k in keep_local]
        va.pair_same_prob = np.round(P, 4).tolist()
    else:
        keep = garment_like
    for i in range(n):
        if i in garment_like and i not in keep:
            photos[i].is_outlier = True
            photos[i].role = "outlier"
        if n >= 2:
            others = [j for j in keep if j != i]
            photos[i].same_garment_score = float(np.mean([P[i, j] for j in others])) if others else 1.0
    if n == 1 and photos[0].view not in ("front",):
        va.notes.append(f"single photo looks like a {photos[0].view} view ({photos[0].view_probs.get(photos[0].view, 0):.2f}); used as the front as requested")
    fi, bi, info = choose_front_back(view_probs[:, 0], view_probs[:, 1], usab, keep, back_thr, uw)
    photos[fi].role = "front"
    va.front = paths[fi]
    if bi is not None:
        photos[bi].role = "back"
        va.back = paths[bi]
    for i in range(n):
        ph = photos[i]
        if ph.role in ("front", "back", "outlier"):
            continue
        if ph.view == "other":
            ph.role = "other"
        elif ph.view == "side":
            ph.role = "side"
        elif ph.view == "additional":
            ph.role = "detail"
        elif ph.view == "front":
            ph.role = "extra_front"
        elif ph.view == "back":
            ph.role = "extra_back"
        else:
            ph.role = "extra_front"
    va.sides = [p.path for p in photos if p.role == "side"]
    va.details = [p.path for p in photos if p.role == "detail"]
    va.others = [p.path for p in photos if p.role == "other"]
    va.outliers = [p.path for p in photos if p.role == "outlier"]
    if n >= 2 and info.get("joint") is False and info.get("best_back_prob") is not None:
        va.notes.append(f"no back view accepted (best back probability {info['best_back_prob']:.2f} < {back_thr})")
    return va


DEFAULT_PARAMS = {"back_threshold": 0.5, "usability_weight": 0.3, "other_threshold": 0.6}


def assign_views(image_paths: list, model_dir: str | Path | None = None, device: str = "auto",
                 params: Optional[dict] = None) -> ViewAssignment:
    """Assign front/back/side/detail/other and presentation to 1..N unlabelled photos of one garment.

    image_paths: list of file paths (any order, any names).  Never raises for model problems: on failure the
    first photo is returned as front with method 'fallback_first_image' and the reason in `notes`.
    """
    paths = [str(p) for p in image_paths]
    if not paths:
        raise ValueError("assign_views needs at least one image path")
    prm = dict(DEFAULT_PARAMS)
    if params:
        prm.update(params)
    try:
        bundle = load_bundle(model_dir)
        for k in ("back_threshold", "usability_weight", "other_threshold"):
            if params is None or k not in params:
                prm[k] = bundle.get("params", {}).get(k, prm[k])
        emb = get_embedder(bundle["backbone"], device)
        pil = [Image.open(p).convert("RGB") for p in paths]
        feats = emb.encode(pil)
        cues = [image_cues(np.asarray(im)) for im in pil]
        view_probs = bundle["view_model"].predict_proba(feats)
        order = list(bundle["view_model"].classes_)
        view_probs = view_probs[:, [order.index(c) for c in VIEW_CLASSES]]
        pres_classes = ["flat", "person"]
        pres_probs = presentation_probability(feats, bundle)
        other_prob = other_probability(feats, bundle)
        n = len(paths)
        P = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                x = pair_features(feats[i], feats[j], cues[i]["colour"], cues[j]["colour"])
                P[i, j] = P[j, i] = float(bundle["same_model"].predict_proba(x[None])[0, 1])
        return assemble(paths, view_probs, pres_probs, pres_classes, other_prob, cues, P, prm, "trained:" + bundle["name"])
    except Exception as e:  # noqa: BLE001 - never break the pipeline over view selection
        pil_ok = []
        for p in paths:
            try:
                im = np.asarray(Image.open(p).convert("RGB"))
                c = image_cues(im)
                pil_ok.append(PhotoInfo(path=p, blur=c["blur"], garment_area=c["garment_area"],
                                        touches_frame=c["touches_frame"], face_found=c["face_found"]))
            except Exception:  # noqa: BLE001
                pil_ok.append(PhotoInfo(path=p))
        for k, ph in enumerate(pil_ok):
            ph.role = "front" if k == 0 else "unassigned"
            ph.view = "front" if k == 0 else "additional"
        return ViewAssignment(photos=pil_ok, front=paths[0], method="fallback_first_image",
                              notes=[f"view model unavailable: {type(e).__name__}: {e}"])


def presentation_probability(feats: np.ndarray, bundle: dict, temperature: float = 100.0) -> np.ndarray:
    """N x 2 [flat, person]: mean of the trained logistic regression and the zero-shot prompt probabilities
    (mannequin prompts count as 'person' side; weight bundle['pres_zs_weight'], default 0.5)."""
    m = bundle["pres_model"]
    order = list(m.classes_)
    p = m.predict_proba(feats)[:, [order.index("flat"), order.index("person")]]
    T = bundle.get("zs_pres")
    w = float(bundle.get("pres_zs_weight", 0.5))
    if T and w > 0:
        M = np.stack([T["flat"], T["mannequin"], T["person"]])
        z = temperature * feats @ M.T
        z = z - z.max(1, keepdims=True)
        e = np.exp(z)
        e /= e.sum(1, keepdims=True)
        zs = np.stack([e[:, 0], e[:, 1] + e[:, 2]], 1)
        p = (1 - w) * p + w * zs
    return p


def other_probability(feats: np.ndarray, bundle: dict, temperature: float = 100.0) -> np.ndarray:
    """Zero-shot P(photo is a size chart / label / packaging) with the stored text embeddings."""
    T = bundle.get("zs_text")          # dict: class -> unit vector (mean of the prompt ensemble)
    if not T:
        return np.zeros(len(feats))
    names = list(T)
    M = np.stack([T[k] for k in names])
    z = temperature * feats @ M.T
    z = z - z.max(1, keepdims=True)
    pr = np.exp(z)
    pr /= pr.sum(1, keepdims=True)
    return pr[:, names.index("other")]


def list_images(folder: str | Path) -> list[str]:
    return [str(p) for p in sorted(Path(folder).iterdir()) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Assign views to 1..N photos of one garment")
    ap.add_argument("inputs", nargs="+", help="a folder or image files")
    ap.add_argument("--out", default=None, help="write view_assignment.json here")
    a = ap.parse_args(argv)
    paths: list[str] = []
    for x in a.inputs:
        paths += list_images(x) if Path(x).is_dir() else [x]
    va = assign_views(paths)
    print(json.dumps({k: v for k, v in va.to_dict().items() if k not in ("photos", "pair_same_prob")}, indent=2))
    for p in va.photos:
        print(f"{Path(p.path).name:40s} view={p.view:10s} pres={p.presentation:7s} role={p.role:12s} usab={p.usability:.2f} same={p.same_garment_score:.2f}")
    if a.out:
        write_view_assignment_json(va, a.out)


if __name__ == "__main__":
    main()
