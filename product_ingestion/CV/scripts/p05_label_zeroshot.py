"""P05: zero-shot region labelling on crops (SigLIP2 and Marqo-FashionSigLIP), compared with the rules.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_label_zeroshot.py --src try_01 --method v2_combo

Part A  type accuracy on the REFERENCE boxes (approximate labels): rules vs SigLIP2 vs FashionSigLIP
        (single prompt and prompt ensemble).  -> out/p05_design/<src>/zeroshot/ref_crops.json
Part B  relabels the regions of <method> with each zero-shot labeller (colour_block regions keep their type;
        regions the labeller calls "plain" are dropped) and saves them as methods/<method>_<labeller>/<cloth>/.
One model at a time, each inside gpu_lock("p05"), freed before the next.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "product_ingestion"))
from gpu_lock import gpu_lock  # noqa: E402
import cv_design_regions as cvd  # noqa: E402

CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
CLASSES = ["text", "graphic", "logo", "stripes", "pattern", "plain"]
SINGLE = {
    "text": "a t-shirt with text",
    "graphic": "a t-shirt with a graphic print",
    "logo": "a t-shirt with a small logo",
    "stripes": "a t-shirt with stripes",
    "pattern": "a t-shirt with an all-over pattern",
    "plain": "a plain t-shirt",
}
ENSEMBLE = {
    "text": ["a close-up photo of a t-shirt with printed text", "bold lettering printed on clothing", "words written on fabric"],
    "graphic": ["a graphic illustration printed on a t-shirt", "artwork or a picture printed on clothing", "a cartoon or photo print on a shirt"],
    "logo": ["a small logo on a t-shirt", "a small brand emblem on clothing", "a tiny badge on a shirt"],
    "stripes": ["horizontal stripes on fabric", "a striped pattern on a shirt", "parallel bands of colour on a garment"],
    "pattern": ["an all-over repeating pattern on fabric", "a floral or polka dot print fabric", "a repeating geometric print on clothing"],
    "plain": ["plain solid colour fabric", "a smooth plain cloth with soft folds", "an empty area of a plain t-shirt"],
}


def crop(rgb, box, pad=0.15):
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    x0, x1 = max(0, int(x0 - pad * bw)), min(w, int(x1 + pad * bw))
    y0, y1 = max(0, int(y0 - pad * bh)), min(h, int(y1 + pad * bh))
    return rgb[y0:y1, x0:x1]


def load():
    labels = json.loads((CV / "out/p00_baseline/reference/labels.json").read_text(encoding="utf-8"))["cloths"]
    data = {}
    for c in CLOTHS:
        e = labels[c]
        rgb = cv2.cvtColor(cv2.imread(e["image"], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        refs = [{"box": [d["box"][0] / 100 * w, d["box"][1] / 100 * h, d["box"][2] / 100 * w, d["box"][3] / 100 * h], "type": d["type"]}
                for d in e["designs"] if d["type"] != "colour_block"]
        data[c] = {"rgb": rgb, "refs": refs}
    return data


class Labeller:
    """Wraps one model: score(list of crops) -> (n, len(CLASSES)) probabilities for each prompt set."""

    def __init__(self, name):
        import torch
        self.name = name
        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        if name == "siglip2":
            from transformers import AutoModel, AutoProcessor
            self.proc = AutoProcessor.from_pretrained("google/siglip2-base-patch16-224")
            self.model = AutoModel.from_pretrained("google/siglip2-base-patch16-224", torch_dtype=torch.float16 if self.dev == "cuda" else torch.float32).to(self.dev).eval()
        else:
            import open_clip
            self.model, _, self.pre = open_clip.create_model_and_transforms("hf-hub:Marqo/marqo-fashionSigLIP")
            self.model = self.model.to(self.dev).eval()
            self.tok = open_clip.get_tokenizer("hf-hub:Marqo/marqo-fashionSigLIP")
        self.text_cache = {}

    def _text(self, prompts):
        torch = self.torch
        with torch.no_grad():
            if self.name == "siglip2":
                t = self.proc(text=prompts, padding="max_length", max_length=64, return_tensors="pt").to(self.dev)
                f = self.model.get_text_features(**t)
            else:
                f = self.model.encode_text(self.tok(prompts).to(self.dev))
        return torch.nn.functional.normalize(f.float(), dim=-1)

    def _img(self, im):
        torch = self.torch
        from PIL import Image
        pil = Image.fromarray(im)
        with torch.no_grad():
            if self.name == "siglip2":
                inp = self.proc(images=pil, return_tensors="pt").to(self.dev)
                inp = {k: v.half() if (self.dev == "cuda" and v.dtype == torch.float32) else v for k, v in inp.items()}
                f = self.model.get_image_features(**inp)
            else:
                f = self.model.encode_image(self.pre(pil).unsqueeze(0).to(self.dev))
        return torch.nn.functional.normalize(f.float(), dim=-1)

    def probs(self, im, mode):
        if mode not in self.text_cache:
            if mode == "single":
                T = self._text([SINGLE[c] for c in CLASSES])
            else:
                per = [self._text(ENSEMBLE[c]).mean(0) for c in CLASSES]
                T = self.torch.nn.functional.normalize(self.torch.stack(per), dim=-1)
            self.text_cache[mode] = T
        f = self._img(im)
        logits = (f @ self.text_cache[mode].T).squeeze(0) * 100
        return self.torch.softmax(logits, -1).cpu().numpy()

    def close(self):
        del self.model
        gc.collect()
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="try_01")
    ap.add_argument("--method", default="v2_combo")
    args = ap.parse_args()
    root = CV / "out/p05_design" / args.src
    data = load()
    # rules on reference boxes (need the dev mask of each photo)
    rule_pred = {}
    for c in CLOTHS:
        m = cv2.imread(str(CV / f"out/p00_baseline/reference/{c}/garment_mask.png"), cv2.IMREAD_UNCHANGED)
        m = m[..., -1] if m.ndim == 3 else m
        rgb = data[c]["rgb"]
        mask = cv2.resize(m, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST) > 127
        P = cvd.prepare(rgb, mask)
        cvd.propose_colour(P)
        D = P.info["dev_mask"]
        rule_pred[c] = [cvd.rule_label(P, [v * P.scale for v in r["box"]], D) for r in data[c]["refs"]]
    res = {"rules": {"pred": rule_pred}}
    # zero-shot
    methods_regions = {c: json.loads((root / "methods" / args.method / c / "design_regions.json").read_text(encoding="utf-8")) for c in CLOTHS}
    for name in ("siglip2", "fashionsiglip"):
        with gpu_lock("p05"):
            L = Labeller(name)
            for mode in ("single", "ensemble"):
                key = f"{name}_{mode}"
                res[key] = {"pred": {}, "probs": {}}
                for c in CLOTHS:
                    res[key]["pred"][c] = []
                    res[key]["probs"][c] = []
                    for r in data[c]["refs"]:
                        p = L.probs(crop(data[c]["rgb"], r["box"]), mode)
                        res[key]["pred"][c].append(CLASSES[int(p.argmax())])
                        res[key]["probs"][c].append([round(float(v), 3) for v in p])
                # Part B: relabel method regions
                for c in CLOTHS:
                    out = []
                    for r in methods_regions[c]:
                        if r["type"] == "colour_block":
                            out.append(r); continue
                        p = L.probs(crop(data[c]["rgb"], r["box"]), mode)
                        t = CLASSES[int(p.argmax())]
                        if t == "plain":
                            continue
                        out.append({**r, "type": t, "source": r.get("source", "") + f"+{key}"})
                    d = root / "methods" / f"{args.method}_{key}" / c
                    d.mkdir(parents=True, exist_ok=True)
                    (d / "design_regions.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
            L.close()
            del L
    # accuracy table on the reference boxes
    truth = {c: [r["type"] for r in data[c]["refs"]] for c in CLOTHS}
    acc = {}
    for key, v in res.items():
        ok = n = 0
        for c in CLOTHS:
            for p, t in zip(v["pred"][c], truth[c]):
                ok += int(p == t); n += 1
        acc[key] = {"correct": ok, "n": n, "accuracy": ok / n}
    res["truth"] = truth
    res["accuracy"] = acc
    d = root / "zeroshot"
    d.mkdir(exist_ok=True)
    (d / "ref_crops.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(acc, indent=1))
    print("truth", truth)
    for k in res:
        if k not in ("truth", "accuracy"):
            print(k, res[k]["pred"])


if __name__ == "__main__":
    main()
