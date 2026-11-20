"""P04: run every colour method on the 5 Mirra photos and score them with evaluate.py.

Masks:  oracle = reference garment masks (isolates colour quality)
        v0     = the v0 segmentation (product_ingestion/output/<cloth>/s_001/001/image_info/base_garment.png)
Writes  out/p04_colour/<run_tag>/methods/<mask>__<method>/<cloth>/{palette.json, base_colour.json, regions.json, region_map.png}
        and timing.json; then (with --eval) calls evaluate.py for every folder (label p04_<mask>__<method>).

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_run_methods.py --masks oracle v0 --eval
"""
from __future__ import annotations
import argparse, glob, json, subprocess, sys, time, warnings
from pathlib import Path
import cv2, numpy as np

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "product_ingestion"))
import step_03_0_colour_extraction as ce  # noqa: E402

OUT = ROOT / "out" / "p04_colour"
PY = REPO / ".venv" / "Scripts" / "python.exe"
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]
NON_GARMENT_PERSON = [1, 2, 3, 11, 12, 13, 14, 15]  # parser labels: hat, hair, sunglasses, face, legs, arms (skin and head)

METHODS = {
    "v0": dict(method="v0"),
    "v1_default": dict(),   # extract_colours(rgba) with no options: the new default
    # skin handling (K-means, merge 5)
    "k_noskin": dict(cluster="kmeans", skin="none"),
    "k_hsv": dict(cluster="kmeans", skin="hsv"),
    "k_ycrcb": dict(cluster="kmeans", skin="ycrcb"),
    "k_auto": dict(cluster="kmeans", skin="auto"),
    "k_parser": dict(cluster="kmeans", skin="mask", _parser=True),
    # clustering (skin auto)
    "kmedoids_auto": dict(cluster="kmedoids", skin="auto"),
    "gmm_auto": dict(cluster="gmm", skin="auto"),
    "meanshift_auto": dict(cluster="meanshift", skin="auto"),
    # merging ablation
    "kmeans_nomerge": dict(cluster="kmeans", skin="auto", merge_de=0.01),
    "gmm_nomerge": dict(cluster="gmm", skin="auto", merge_de=0.01),
    "gmm_shade20": dict(cluster="gmm", skin="auto", shade_dl=20.0),
    # enhancement before clustering
    "gmm_greyworld": dict(cluster="gmm", skin="auto", wb="greyworld"),
    "gmm_clahe": dict(cluster="gmm", skin="auto", clahe=True),
    "meanshift_bw14": dict(cluster="meanshift", skin="auto", ms_bandwidth=14.0, min_share=0.02),
    "meanshift_bw10_min2": dict(cluster="meanshift", skin="auto", min_share=0.02),
    "meanshift_bw14_shade": dict(cluster="meanshift", skin="auto", ms_bandwidth=14.0, min_share=0.02, shade_dl=20.0),
    "kmedoids_min2": dict(cluster="kmedoids", skin="auto", min_share=0.02),
    "gmm_prepare": dict(cluster="gmm", skin="auto", wb="prepare"),
    "k_prepare": dict(cluster="kmeans", skin="auto", wb="prepare"),
    "gmm_parser": dict(cluster="gmm", skin="mask", _parser=True),
}


def load_photo(c, labels):
    e = labels[c]
    bgr = cv2.imread(e["image"], cv2.IMREAD_COLOR)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), e


def load_rgba(c, labels, mask_kind):
    rgb, e = load_photo(c, labels)
    if mask_kind == "oracle":
        m = cv2.imread(e["garment_mask"], cv2.IMREAD_GRAYSCALE)
        if m.shape != rgb.shape[:2]:
            m = cv2.resize(m, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
        a = np.dstack([rgb, (m > 127).astype(np.uint8) * 255])
    else:
        p = glob.glob(str(REPO / "product_ingestion" / "output" / c / "*" / "*" / "image_info" / "base_garment.png"))[0]
        bgra = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        a = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA)
    return a


def parser_skin(c, shape):
    p = OUT / "parser_cache" / "mirra" / f"{c}.png"
    if not p.exists():
        return None
    lab = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if lab.shape != shape:
        lab = cv2.resize(lab, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return np.isin(lab, NON_GARMENT_PERSON)


def paint(lbl, palette, max_side=512):
    img = np.full(lbl.shape + (3,), 128, np.uint8)
    for k, p in enumerate(palette):
        img[lbl == k] = p.rgb
    s = max_side / max(img.shape[:2])
    if s < 1:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks", nargs="+", default=["oracle", "v0"])
    ap.add_argument("--methods", nargs="*", default=None)
    ap.add_argument("--tag", default="methods")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--label_suffix", default="")
    a = ap.parse_args()
    labels = json.loads((ROOT / "out" / "p00_baseline" / "reference" / "labels.json").read_text(encoding="utf-8"))["cloths"]
    names = a.methods or list(METHODS)
    timing = {}
    for mk in a.masks:
        imgs = {c: load_rgba(c, labels, mk) for c in CLOTHS}
        for name in names:
            cfg = dict(METHODS[name])
            use_parser = cfg.pop("_parser", False)
            method = cfg.pop("method", "v1")
            folder = OUT / a.tag / f"{mk}__{name}"
            for c in CLOTHS:
                d = folder / c
                d.mkdir(parents=True, exist_ok=True)
                kw = dict(cfg)
                if use_parser:
                    kw["skin_mask"] = parser_skin(c, imgs[c].shape[:2])
                    if kw["skin_mask"] is None:
                        kw["skin"] = "none"
                t0 = time.time()
                try:
                    r, _ = ce.extract_colours(imgs[c].copy(), method=method, **kw)
                except Exception as ex:  # noqa: BLE001
                    r = ce.ColourResult(success=False, message=f"{type(ex).__name__}: {ex}")
                dt = time.time() - t0
                timing[f"{mk}__{name}/{c}"] = round(dt, 2)
                if not r.success:
                    (d / "error.txt").write_text(r.message, encoding="utf-8")
                    print("FAIL", mk, name, c, r.message)
                    continue
                pal = [{"hex": p.hex_code, "share": round(p.percentage / 100, 5), "role": p.role or "cluster"} for p in r.palette]
                (d / "palette.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
                (d / "base_colour.json").write_text(json.dumps({"hex": r.base_colour_hex}), encoding="utf-8")
                (d / "regions.json").write_text(json.dumps({"skin_pixels_removed": r.skin_pixels_removed, "k_used": r.k_used,
                                                           **r.extra_json()}, indent=1), encoding="utf-8")
                if r.label_map is not None:
                    cv2.imwrite(str(d / "region_map.png"), cv2.cvtColor(paint(r.label_map, r.palette), cv2.COLOR_RGB2BGR))
            print("done", mk, name, flush=True)
            if a.eval:
                subprocess.run([str(PY), str(HERE / "evaluate.py"), "--pred", str(folder), "--label", f"p04_{mk}__{name}{a.label_suffix}", "--plan", "p04"],
                               cwd=str(REPO), stdout=subprocess.DEVNULL)
    tp = OUT / a.tag / "timing.json"
    old = json.loads(tp.read_text()) if tp.exists() else {}
    old.update(timing)
    tp.write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
