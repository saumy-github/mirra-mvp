"""P15b: one-pass patch of product_ingestion/cv_design_regions.py (adds v4_relabel, text-in-graphic and split-text fixes).
Kept for the record; the patched file is the source of truth. Idempotent (does nothing if already patched).

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15b_patch_lib.py
"""
from pathlib import Path

p = Path("product_ingestion/cv_design_regions.py")
s = p.read_text(encoding="utf-8")
if "v4_relabel" in s:
    raise SystemExit("already patched")


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:60], s.count(old))
    s = s.replace(old, new)


# 1. docstring
rep('''Main entry point:  detect_regions(rgb, mask, method="v2_combo") -> list[dict]
''', '''Main entry point:  detect_regions(rgb, mask, method="v4_relabel") -> list[dict]

Methods built on the v3 flow (P05 + P15b):
  v3_combo   colour + OCR + Hough + colour blocks + cleaned Grounding DINO, priority NMS (P05 default, unchanged)
  v3_fix     v3_combo + two P15b fixes: (a) a text box inside a graphic box is kept (captions under prints),
             (b) an OCR box that holds two text lines of very different glyph height is split in two
  v4_nofix   v3_combo + zero-shot SigLIP 2 relabelling of every non-colour-block region (padded crop, single
             prompt; a "plain" prediction drops the region)
  v4_relabel v3_fix + the SigLIP 2 relabelling   (pipeline default)
''')

# 2. nms_priority: text-in-graphic option
rep('''def nms_priority(regs: list, iou_thr: float = 0.5, contain_thr: float = 0.85) -> list:
    """Class-agnostic NMS with a source priority (hough > ocr > text_cc > gdino > colour > sam2).
    colour_block regions are exempt (they describe the fabric, not a print)."""''',
    '''def nms_priority(regs: list, iou_thr: float = 0.5, contain_thr: float = 0.85, keep_text_in_graphic: bool = False) -> list:
    """Class-agnostic NMS with a source priority (hough > ocr > text_cc > gdino > colour > sam2).
    colour_block regions are exempt (they describe the fabric, not a print).
    keep_text_in_graphic (P15b fix a): a text box that merely lies inside a bigger non-text box (a caption under
    a print) is not suppressed by containment; only real overlap (IoU) suppresses it."""''')
rep('''    out = []
    for r in rest:
        if any(_box_iou(r["box"], k["box"]) > iou_thr or _contain(r["box"], k["box"]) > contain_thr for k in out):
            continue
        out.append(r)
    return out + keep_blocks''',
    '''    out = []
    for r in rest:
        def _hit(k):
            if _box_iou(r["box"], k["box"]) > iou_thr:
                return True
            if keep_text_in_graphic and r.get("type") == "text" and k.get("type") != "text":
                return False
            return _contain(r["box"], k["box"]) > contain_thr
        if any(_hit(k) for k in out):
            continue
        out.append(r)
    return out + keep_blocks''')

# 3. split + labeller code, inserted before the top-level section
rep('''# ───────────────────────────── top-level ─────────────────────────────
''', '''# ───────────────────────────── P15b fix b: split merged text lines ─────────────────────────────

def split_text_lines(P: Prep, regs: list, small_frac: float = 0.5, min_small: int = 2, pad_frac: float = 0.01) -> list:
    """An OCR / text box that holds two lines of very different glyph size (a big word and a small script line)
    is split into one box per line.  Inside the box the ink (deltaE2000 > 12 from the local fabric) is cut into
    connected pieces; pieces shorter than `small_frac` of the tallest piece form the small line.  A split needs
    >= `min_small` small pieces laid out like a text line (wider than 1.4x its height) that are tiny compared with
    the big line; otherwise the box is returned unchanged.  Both new boxes are the tight boxes of their ink."""
    out = []
    ink_all = (P.dev > 12.0) & P.inner
    H, W = ink_all.shape
    for r in regs:
        if r.get("type") != "text" or r.get("source") not in ("ocr", "text_cc"):
            out.append(r)
            continue
        x0, y0, x1, y1 = [int(round(v)) for v in r["box"]]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < 8 or y1 - y0 < 8:
            out.append(r)
            continue
        n, cc, st, _ = cv2.connectedComponentsWithStats(ink_all[y0:y1, x0:x1].astype(np.uint8))
        comps = [st[i] for i in range(1, n) if st[i, 4] >= 2]
        if len(comps) < min_small + 1:
            out.append(r)
            continue
        hmax = max(int(c[3]) for c in comps)
        big = [c for c in comps if c[3] >= small_frac * hmax]
        small = [c for c in comps if c[3] < small_frac * hmax]

        def tight(cs):
            xa = min(int(c[0]) for c in cs)
            ya = min(int(c[1]) for c in cs)
            xb = max(int(c[0] + c[2]) for c in cs)
            yb = max(int(c[1] + c[3]) for c in cs)
            return xa, ya, xb, yb

        if len(small) < min_small or not big:
            out.append(r)
            continue
        sb, bb = tight(small), tight(big)
        sw, sh = sb[2] - sb[0], max(1, sb[3] - sb[1])
        big_area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        if sw < 1.4 * sh or sw * sh > 0.25 * big_area:
            out.append(r)
            continue
        pad = max(1, int(round(pad_frac * P.diag)))
        for b in (bb, sb):
            out.append({**r, "box": [max(0, x0 + b[0] - pad), max(0, y0 + b[1] - pad), min(W, x0 + b[2] + pad), min(H, y0 + b[3] + pad)]})
    return out


# ───────────────────────────── P15b: zero-shot relabelling (SigLIP 2) ─────────────────────────────

RELABEL_MODEL = "google/siglip2-base-patch16-224"
RELABEL_DEVICE = None          # None = cuda when available, else cpu.  The CALLER guards the GPU (gpu_lock).
RELABEL_PAD = 0.15
RELABEL_CLASSES = ["text", "graphic", "logo", "stripes", "pattern", "plain"]
RELABEL_PROMPTS = {
    "text": "a t-shirt with text",
    "graphic": "a t-shirt with a graphic print",
    "logo": "a t-shirt with a small logo",
    "stripes": "a t-shirt with stripes",
    "pattern": "a t-shirt with an all-over pattern",
    "plain": "a plain t-shirt",
}
_LABELLER = None


class _Labeller:
    """Zero-shot region typer: SigLIP 2 (base, patch16-224), one prompt per class, loaded once and reused."""

    def __init__(self, device: str | None = None):
        import torch
        from transformers import AutoModel, AutoProcessor
        self.torch = torch
        self.dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.proc = AutoProcessor.from_pretrained(RELABEL_MODEL)
        self.model = AutoModel.from_pretrained(
            RELABEL_MODEL, torch_dtype=torch.float16 if self.dev == "cuda" else torch.float32).to(self.dev).eval()
        self.text = None
        self._text_feats()

    def _to_cpu(self):
        self.dev = "cpu"
        self.model = self.model.float().to("cpu")
        self.text = None

    def _text_feats(self):
        torch = self.torch
        with torch.no_grad():
            t = self.proc(text=[RELABEL_PROMPTS[c] for c in RELABEL_CLASSES], padding="max_length", max_length=64,
                          return_tensors="pt").to(self.dev)
            f = self.model.get_text_features(**t)
        self.text = torch.nn.functional.normalize(f.float(), dim=-1)

    def probs(self, crop_rgb: np.ndarray) -> np.ndarray:
        from PIL import Image
        torch = self.torch
        for attempt in (0, 1):
            try:
                if self.text is None:
                    self._text_feats()
                with torch.no_grad():
                    inp = self.proc(images=Image.fromarray(crop_rgb), return_tensors="pt").to(self.dev)
                    inp = {k: v.half() if (self.dev == "cuda" and v.dtype == torch.float32) else v for k, v in inp.items()}
                    f = torch.nn.functional.normalize(self.model.get_image_features(**inp).float(), dim=-1)
                    return torch.softmax((f @ self.text.T).squeeze(0) * 100, -1).cpu().numpy()
            except RuntimeError:          # e.g. CUDA out of memory: finish on the CPU
                if attempt == 1 or self.dev == "cpu":
                    raise
                self._to_cpu()


def get_labeller() -> "_Labeller":
    """The shared SigLIP 2 labeller (loaded lazily, once)."""
    global _LABELLER
    if _LABELLER is None:
        try:
            _LABELLER = _Labeller(RELABEL_DEVICE)
        except RuntimeError:              # CUDA unavailable / out of memory at load time: CPU fallback
            _LABELLER = _Labeller("cpu")
    return _LABELLER


def release_labeller() -> None:
    """Free the labeller and its GPU memory (call before leaving the caller's gpu_lock)."""
    global _LABELLER
    import gc
    _LABELLER = None
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def _crop_padded(rgb: np.ndarray, box, pad: float = RELABEL_PAD) -> np.ndarray:
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    xa, xb = max(0, int(x0 - pad * bw)), min(w, int(x1 + pad * bw))
    ya, yb = max(0, int(y0 - pad * bh)), min(h, int(y1 + pad * bh))
    return rgb[ya:max(yb, ya + 1), xa:max(xb, xa + 1)]


def relabel_regions(rgb: np.ndarray, regs: list, labeller: "_Labeller | None" = None) -> list:
    """Re-type every region (boxes in the pixels of `rgb`) with the zero-shot labeller; colour_block regions keep
    their type; a region predicted "plain" is dropped.  Falls back to the input regions if the model is unavailable."""
    if not any(r["type"] != "colour_block" for r in regs):
        return regs
    try:
        L = labeller or get_labeller()
    except Exception as exc:  # noqa: BLE001  - model missing: keep the rule-based types
        import warnings
        warnings.warn(f"relabelling skipped ({type(exc).__name__}: {exc})")
        return regs
    out = []
    for r in regs:
        if r["type"] == "colour_block":
            out.append(r)
            continue
        p = L.probs(_crop_padded(rgb, r["box"]))
        t = RELABEL_CLASSES[int(p.argmax())]
        if t == "plain":
            continue
        out.append({**r, "type": t, "source": r.get("source", "") + "+siglip2"})
    return out


# ───────────────────────────── top-level ─────────────────────────────
''')

# 4. METHODS tuple
rep('''METHODS = ("v3_combo", "b_classical",''', '''METHODS = ("v4_relabel", "v4_nofix", "v3_fix", "v3_combo", "b_classical",''')

# 5. detect_regions: flow
rep('''    P = prep or prepare(rgb, mask)
    cache = cache if cache is not None else {}''', '''    v3_flow = method in ("v3_combo", "v3_fix", "v4_nofix", "v4_relabel")
    fixes = method in ("v3_fix", "v4_relabel")          # P15b fixes (text in graphic, split merged text lines)
    relabel = method in ("v4_nofix", "v4_relabel")      # P15b zero-shot SigLIP 2 relabelling
    P = prep or prepare(rgb, mask)
    cache = cache if cache is not None else {}''')
rep('''    elif method == "v3_combo":
        stripes = propose_stripes(P)''', '''    elif v3_flow:
        stripes = propose_stripes(P)''')
rep('''        regs += list(text) + list(stripes) + list(colour) + propose_blocks(P)
        if per["periodic"] and P.info["dev_cov"] > 0.35 and not stripes:''', '''        if fixes:
            text = split_text_lines(P, list(text))
        regs += list(text) + list(stripes) + list(colour) + propose_blocks(P)
        if per["periodic"] and P.info["dev_cov"] > 0.35 and not stripes:''')
rep('''    if method == "v3_combo":
        for r in regs:
            r.setdefault("type", "any")
        if plain:
            regs = [r for r in regs if r["type"] == "colour_block"]
        regs = nms_priority(regs)''', '''    if v3_flow:
        for r in regs:
            r.setdefault("type", "any")
        if plain:
            regs = [r for r in regs if r["type"] == "colour_block"]
        regs = nms_priority(regs, keep_text_in_graphic=fixes)''')
rep('''    regs = _finish(P, regs, D)
    return to_original(P, regs, keep_mask=False)''', '''    regs = _finish(P, regs, D)
    res = to_original(P, regs, keep_mask=False)
    if relabel:
        res = relabel_regions(rgb, res)
    return res''')
p.write_text(s, encoding="utf-8")
print("patched")
