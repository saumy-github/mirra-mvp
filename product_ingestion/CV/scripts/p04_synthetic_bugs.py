"""P04: reproduce the colour bugs B1-B3 on synthetic T-shirts, before (v0) and after (v1).

Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p04_synthetic_bugs.py
Writes out/p04_colour/synthetic/results.json and results.md (no files are overwritten
if a different --tag is used).
"""
from __future__ import annotations
import argparse, json, sys, traceback, warnings
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[0]))
import step_03_0_colour_extraction as ce  # noqa: E402
warnings.filterwarnings("ignore")

H, W = 240, 240


def tee_mask():
    m = np.zeros((H, W), np.uint8)
    pts = np.array([[70, 20], [170, 20], [225, 70], [195, 100], [175, 85], [175, 225], [65, 225], [65, 85], [45, 100], [15, 70]], np.int32)
    cv2.fillPoly(m, [pts], 255)
    return m > 0


def rgba(canvas, mask, noise=3.0, seed=0):
    rng = np.random.default_rng(seed)
    img = canvas.astype(np.float32)
    if noise:
        img += rng.normal(0, noise, img.shape)
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    out[..., 3] = mask.astype(np.uint8) * 255
    return out


def solid(c):
    return np.tile(np.array(c, np.float32), (H, W, 1))


def cases():
    m = tee_mask()
    out = {}
    for name, c in [("tan", (210, 180, 140)), ("coral", (240, 128, 110)), ("pink", (230, 150, 170)), ("brown", (120, 80, 50))]:
        out[f"B1_{name}_tee"] = (rgba(solid(c), m), dict(true=[(c, 1.0)]))
    # white tee with a shadow (folds) on 20 % of it
    cv = solid((240, 240, 240)); sh = m.copy(); sh[:, :105] = False; sh[:150, :] = False
    cv[sh] = (196, 196, 196)
    out["B2_white_tee_with_shadow"] = (rgba(cv, m), dict(true=[((240, 240, 240), 0.88), ((196, 196, 196), 0.12)], base=(240, 240, 240)))
    # black tee with a small red print
    cv = solid((18, 18, 20)); pr = np.zeros((H, W), bool); pr[100:130, 95:145] = True
    cv[pr] = (200, 30, 40)
    out["B2_black_tee_red_print"] = (rgba(cv, m), dict(true=[((18, 18, 20), 0.93), ((200, 30, 40), 0.07)], base=(18, 18, 20)))
    # B3 flat single colour, zero noise
    out["B3_flat_single_colour"] = (rgba(solid((100, 150, 200)), m, noise=0), dict(true=[((100, 150, 200), 1.0)], base=(100, 150, 200)))
    out["B3_flat_two_colours"] = (rgba(np.where((np.arange(H)[:, None, None] < 120), solid((250, 250, 250)), solid((20, 60, 55))), m, noise=0),
                                  dict(true=[((250, 250, 250), 0.5), ((20, 60, 55), 0.5)]))
    # colour block (the c_003 case): white upper, dark teal lower
    cv = np.where((np.arange(H)[:, None, None] < 110), solid((231, 231, 241)), solid((27, 53, 49)))
    out["Multi_colour_block_white_teal"] = (rgba(cv, m), dict(true=[((231, 231, 241), 0.4), ((27, 53, 49), 0.6)]))
    # navy tee with white print and skin-coloured arms leaking into the mask (should be removed, fabric kept)
    cv = solid((39, 40, 60)); pr = np.zeros((H, W), bool); pr[100:125, 80:160] = True; cv[pr] = (246, 246, 246)
    skin = np.zeros((H, W), bool); skin[60:110, 8:50] = True; skin[60:110, 190:232] = True
    cv[skin] = (224, 172, 140)
    mm = m | skin
    out["B1_navy_tee_white_print_skin_arms"] = (rgba(cv, mm), dict(true=[((39, 40, 60), 0.8), ((246, 246, 246), 0.08)], base=(39, 40, 60), skin_px=int(skin.sum())))
    return out


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def de(a, b):
    la = cv2.cvtColor(np.array([[a]], np.float32) / 255.0, cv2.COLOR_RGB2LAB)[0, 0]
    lb = cv2.cvtColor(np.array([[b]], np.float32) / 255.0, cv2.COLOR_RGB2LAB)[0, 0]
    return float(ce._de2000(la, lb)[0])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="run_01"); a = ap.parse_args()
    out_dir = ROOT / "out" / "p04_colour" / "synthetic" / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, (img, info) in cases().items():
        cv2.imwrite(str(out_dir / f"{name}.png"), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
        row = {}
        for method in ("v0", "v1"):
            try:
                r, ok = ce.extract_colours(img, method=method)
                if not r.success:
                    row[method] = dict(error=r.message, success=False, skin_removed=r.skin_pixels_removed)
                    continue
                d = dict(success=True, base=r.base_colour_hex, k=r.k_used, skin_removed=r.skin_pixels_removed,
                         palette=[(p.hex_code, round(p.percentage, 1), p.role) for p in r.palette])
                if "base" in info:
                    d["base_de"] = round(de(hex2rgb(r.base_colour_hex), info["base"]), 2)
                else:
                    d["base_de"] = round(de(hex2rgb(r.base_colour_hex), info["true"][0][0]), 2)
                # every true colour must have a close palette colour
                d["worst_true_colour_de"] = round(max(min(de(hex2rgb(p.hex_code), t) for p in r.palette) for t, _ in info["true"]), 2)
                row[method] = d
            except Exception as e:  # noqa: BLE001
                row[method] = dict(success=False, crash=f"{type(e).__name__}: {e}")
        res[name] = row
        print(name, json.dumps(row))
    (out_dir / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    lines = ["| case | v0 base | v0 note | v1 base | v1 palette |", "|---|---|---|---|---|"]
    for n, r in res.items():
        v0, v1 = r["v0"], r["v1"]
        v0b = v0.get("base", "-"); v0n = v0.get("crash") or v0.get("error") or f"k={v0['k']} dE={v0['base_de']} skin={v0['skin_removed']}"
        v1p = ", ".join(f"{h} {s}% {ro}" for h, s, ro in v1.get("palette", [])) or str(v1)
        lines.append(f"| {n} | {v0b} | {v0n} | {v1.get('base', '-')} (dE {v1.get('base_de', '-')}) | {v1p} |")
    (out_dir / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
