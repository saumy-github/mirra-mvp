"""P04: colour-name accuracy on a fixed random subset of Fashion Product Images (small, 60x80 px).

Subset: out/p04_colour/fpi_subset (built by p04_build_fpi_subset.py, seed 0, articleType in Tshirts/Tops/Shirts/Sweatshirts).
Garment masks (the dataset has none):
  bg      photo background is (nearly) uniform: colour = median of the 1-px border; background = pixels within dE76 < 8 of it
          that are connected to the border; the garment is the rest, largest component, holes filled, 1-px erosion.
          (Models in the photo are NOT removed by this mask: arms, face and trousers leak in.)
  parser  SegFormer clothes parser label 4 (Upper-clothes) from out/p04_colour/parser_cache/fpi_labels.npz, bg mask as fallback
          when the parser finds < 3 % of the image.
Colour names: hand-made name -> sRGB prototype table below (the dataset's baseColour vocabulary), nearest by CIEDE2000.
Metrics per method: top1 = name of base_colour_hex equals the label; any = name of any palette colour with share >= 5 % equals the
label; each "strict" (same name) and "family" (name in the same family: White~Off White~Cream, Grey~Grey Melange~Charcoal~Silver,
Blue~Navy Blue, Red~Maroon~Burgundy, Pink~Magenta, Brown~Beige~Khaki~Rust...). Label "Multi" is excluded.

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_fpi_eval.py [--workers 3] [--limit N]
Writes out/p04_colour/fpi_eval/{summary.csv, per_image_<method>.csv}.
"""
from __future__ import annotations
import argparse, json, sys, time, warnings
from multiprocessing import Pool
from pathlib import Path
import cv2, numpy as np, pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "product_ingestion"))
OUT = ROOT / "out" / "p04_colour"

PROTO = {  # name -> typical sRGB
    "Black": (25, 25, 25), "White": (245, 245, 245), "Off White": (238, 232, 215), "Cream": (245, 235, 200),
    "Beige": (222, 200, 165), "Grey": (140, 140, 140), "Grey Melange": (175, 175, 175), "Charcoal": (65, 65, 70),
    "Silver": (192, 192, 192), "Red": (200, 25, 40), "Maroon": (110, 20, 35), "Burgundy": (100, 20, 50),
    "Rust": (170, 70, 30), "Orange": (240, 130, 30), "Peach": (250, 190, 160), "Yellow": (245, 215, 40),
    "Mustard": (210, 165, 30), "Khaki": (190, 175, 120), "Olive": (110, 115, 45), "Lime Green": (160, 210, 50),
    "Green": (40, 140, 60), "Sea Green": (60, 150, 120), "Teal": (20, 110, 115), "Turquoise Blue": (60, 200, 200),
    "Blue": (40, 100, 200), "Navy Blue": (25, 35, 80), "Lavender": (190, 170, 220), "Purple": (110, 40, 140),
    "Magenta": (200, 30, 140), "Pink": (240, 150, 180), "Brown": (110, 70, 40), "Tan": (200, 160, 110),
}
FAMILY = {"White": "white", "Off White": "white", "Cream": "white", "Grey": "grey", "Grey Melange": "grey", "Charcoal": "grey",
          "Silver": "grey", "Blue": "blue", "Navy Blue": "blue", "Red": "red", "Maroon": "red", "Burgundy": "red",
          "Pink": "pink", "Magenta": "pink", "Brown": "brown", "Beige": "brown", "Khaki": "brown", "Rust": "brown", "Tan": "brown",
          "Green": "green", "Sea Green": "green", "Lime Green": "green", "Olive": "green", "Teal": "teal", "Turquoise Blue": "teal"}
NAMES = list(PROTO)


def _lab(rgb):
    return cv2.cvtColor(np.array([[rgb]], np.float32) / 255.0, cv2.COLOR_RGB2LAB)[0, 0].astype(np.float64)


PROTO_LAB = np.array([_lab(PROTO[n]) for n in NAMES])


def name_of(hexc: str) -> str:
    import step_03_0_colour_extraction as ce
    rgb = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    d = ce._de2000(np.repeat(_lab(rgb)[None], len(NAMES), 0), PROTO_LAB)
    return NAMES[int(d.argmin())]


def fam(n):
    return FAMILY.get(n, n)


def bg_mask(rgb):
    h, w = rgb.shape[:2]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bgc = np.median(border, 0)
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    d = np.linalg.norm(lab - _lab(tuple(bgc)).astype(np.float32), axis=-1)
    near = (d < 8).astype(np.uint8)
    n, cc = cv2.connectedComponents(near, connectivity=4)
    touch = set(np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))) - {0}
    bg = np.isin(cc, list(touch)) if touch else np.zeros_like(near, bool)
    g = (~bg).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(g, connectivity=8)
    if n > 1:
        g = (cc == 1 + int(st[1:, cv2.CC_STAT_AREA].argmax())).astype(np.uint8)
    cnts, _ = cv2.findContours(g, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(g)
    cv2.drawContours(filled, cnts, -1, 1, -1)
    er = cv2.erode(filled, np.ones((3, 3), np.uint8))
    return (er if er.sum() > 0.05 * er.size else filled).astype(bool)


# method name -> (mask kind, config for extract_colours)
METHODS = {
    "v0_bg": ("bg", dict(method="v0")),
    "v1_default_bg": ("bg", dict()),
    "v1_default_parsermask": ("parser", dict(skin="none")),
    "k_noskin_bg": ("bg", dict(cluster="kmeans", skin="none")),
    "k_hsv_bg": ("bg", dict(cluster="kmeans", skin="hsv")),
    "k_auto_bg": ("bg", dict(cluster="kmeans", skin="auto")),
    "k_parser_bg": ("bg", dict(cluster="kmeans", skin="mask", _parser=True)),
    "kmedoids_auto_bg": ("bg", dict(cluster="kmedoids", skin="auto")),
    "gmm_auto_bg": ("bg", dict(cluster="gmm", skin="auto")),
    "meanshift_auto_bg": ("bg", dict(cluster="meanshift", skin="auto")),
    "gmm_shade20_bg": ("bg", dict(cluster="gmm", skin="auto", shade_dl=20.0)),
    "gmm_parser_bg": ("bg", dict(cluster="gmm", skin="mask", _parser=True)),
    "meanshift_min2_bg": ("bg", dict(cluster="meanshift", skin="auto", min_share=0.02)),
    "meanshift_min2_parser_bg": ("bg", dict(cluster="meanshift", skin="mask", min_share=0.02, _parser=True)),
    "meanshift_min2_parsermask": ("parser", dict(cluster="meanshift", skin="none", min_share=0.02)),
    "v0_parsermask": ("parser", dict(method="v0")),
    "kmeans_parsermask": ("parser", dict(cluster="kmeans", skin="none")),
    "gmm_parsermask": ("parser", dict(cluster="gmm", skin="none")),
}

_G = {}


def _init():
    _G["labels"] = np.load(OUT / "parser_cache" / "fpi_labels.npz")


def work(args):
    iid, lab_name, methods = args
    import step_03_0_colour_extraction as ce
    rgb = cv2.cvtColor(cv2.imread(str(OUT / "fpi_subset" / "images" / f"{iid}.png")), cv2.COLOR_BGR2RGB)
    plab = _G["labels"][str(iid)]
    skin = np.isin(plab, [1, 2, 3, 11, 12, 13, 14, 15])
    bg = bg_mask(rgb)
    pm = plab == 4
    if pm.mean() < 0.03:
        pm = bg
    rows = []
    for m in methods:
        kind, cfg = METHODS[m]
        cfg = dict(cfg)
        use_parser = cfg.pop("_parser", False)
        method = cfg.pop("method", "v1")
        if use_parser:
            cfg["skin_mask"] = skin
        mask = bg if kind == "bg" else pm
        rgba = np.dstack([rgb, mask.astype(np.uint8) * 255])
        t0 = time.time()
        try:
            r, _ = ce.extract_colours(rgba, method=method, **cfg)
        except Exception as ex:  # noqa: BLE001
            r = ce.ColourResult(success=False, message=f"{type(ex).__name__}")
        dt = time.time() - t0
        if not r.success:
            rows.append(dict(id=iid, label=lab_name, method=m, ok=0, msg=r.message, t=dt))
            continue
        names = [(name_of(p.hex_code), p.percentage / 100) for p in r.palette]
        base = name_of(r.base_colour_hex)
        anyn = [n for n, s in names if s >= 0.05]
        rows.append(dict(id=iid, label=lab_name, method=m, ok=1, base=base, base_hex=r.base_colour_hex, n_colours=len(r.palette),
                         top1=int(base == lab_name), top1_fam=int(fam(base) == fam(lab_name)),
                         any=int(lab_name in anyn), any_fam=int(fam(lab_name) in {fam(n) for n in anyn}),
                         palette=json.dumps([(p.hex_code, round(p.percentage, 1)) for p in r.palette]), t=dt))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--methods", nargs="*", default=None)
    ap.add_argument("--tag", default="run_01")
    ap.add_argument("--stride", type=int, default=1, help="use every n-th image of the fixed subset")
    a = ap.parse_args()
    sub = pd.read_csv(OUT / "fpi_subset" / "labels.csv")
    sub = sub[sub.baseColour.isin(NAMES)]
    sub = sub.iloc[::a.stride]
    if a.limit:
        sub = sub.head(a.limit)
    methods = a.methods or list(METHODS)
    jobs = [(int(i), b, methods) for i, b in zip(sub.id, sub.baseColour)]
    out_dir = OUT / "fpi_eval" / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    if a.workers <= 1:        # serial: lowest memory, partial results saved every 25 images
        _init()
        for k, j in enumerate(jobs):
            rows += work(j)
            if k % 25 == 0:
                print(k, len(jobs), flush=True)
                pd.DataFrame(rows).to_csv(out_dir / "per_image_partial.csv", index=False)
    else:
        with Pool(a.workers, initializer=_init) as p:
            for k, r in enumerate(p.imap_unordered(work, jobs, chunksize=4)):
                rows += r
                if k % 50 == 0:
                    print(k, len(jobs), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "per_image.csv", index=False)
    ok = df[df.ok == 1]
    summ = df.groupby("method").agg(n=("id", "count"), failed=("ok", lambda s: int((s == 0).sum())), time_s=("t", "mean"))
    summ = summ.join(ok.groupby("method").agg(top1=("top1", "mean"), top1_family=("top1_fam", "mean"), any=("any", "mean"),
                                              any_family=("any_fam", "mean"), n_colours=("n_colours", "mean")))
    # failed images count as wrong
    for c in ("top1", "top1_family", "any", "any_family"):
        summ[c] = summ[c] * (summ.n - summ.failed) / summ.n
    summ.loc[methods].round(4).to_csv(out_dir / "summary.csv")
    print(summ.loc[methods].round(4).to_string())


if __name__ == "__main__":
    main()
