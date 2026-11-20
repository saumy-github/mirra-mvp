"""P07 shared helpers: Fashionpedia label mapping, annotation streaming, crop building.

Run nothing here directly; the p07_*.py scripts import it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

CV = Path(__file__).resolve().parents[1]
REPO = CV.parents[1]
OUT = CV / "out" / "p07_attributes"
DATA = CV / "data"
sys.path.insert(0, str(CV / "scripts"))

# ----------------------------------------------------------------- label maps
UPPER_CATS = {0, 1, 2, 3, 4, 5}          # shirt, top, sweater, cardigan, jacket, vest
PATTERN_CATS = UPPER_CATS | {9, 10}      # + coat, dress (pattern only)
SLEEVE_CATS = UPPER_CATS | {9, 10}       # garments that can carry sleeve parts
SLEEVE_PART, NECK_PART = 31, 33

# pattern attribute id -> fine name
PATTERN_FINE = {
    317: "plain", 318: "abstract", 319: "cartoon", 320: "text", 321: "camouflage",
    322: "check", 323: "dot", 324: "fair_isle", 325: "floral", 326: "geometric",
    327: "paisley", 328: "stripe", 329: "houndstooth", 330: "herringbone",
    331: "chevron", 332: "argyle", 339: "toile", 340: "plant",
    333: "animal", 334: "animal", 335: "animal", 336: "animal", 337: "animal", 338: "animal",
}
# fine -> merged class used for training (rare ones merged sensibly)
PATTERN_MERGE = {
    "plain": "plain", "stripe": "stripe", "floral": "floral", "plant": "floral",
    "toile": "floral", "check": "check", "houndstooth": "check", "dot": "dot",
    "geometric": "geometric", "chevron": "geometric", "argyle": "geometric",
    "herringbone": "geometric", "abstract": "abstract", "text": "text",
    "cartoon": "graphic", "camouflage": "other", "fair_isle": "other",
    "paisley": "other", "animal": "other",
}

SLEEVE_FINE = {156: "sleeveless", 157: "short", 158: "elbow", 159: "three_quarter", 160: "long"}
SLEEVE_ORDER = ["sleeveless", "short", "elbow", "three_quarter", "long"]
# 3-class merged version
SLEEVE_MERGE3 = {"sleeveless": "short_or_none", "short": "short_or_none", "elbow": "mid",
                 "three_quarter": "mid", "long": "long"}

NECK_FINE = {
    179: "collarless", 180: "asymmetric", 181: "crew", 182: "round", 183: "v", 184: "surplice",
    185: "oval", 186: "u", 187: "sweetheart", 188: "queen_anne", 189: "boat", 190: "scoop",
    191: "square", 192: "plunging", 193: "keyhole", 194: "halter", 195: "crossover",
    196: "choker", 197: "high", 198: "turtle", 199: "cowl", 200: "straight_across",
    201: "illusion", 202: "off_shoulder", 203: "one_shoulder",
}
NECK_MERGE = {
    "crew": "round_crew", "round": "round_crew", "oval": "round_crew",
    "scoop": "scoop_u", "u": "scoop_u",
    "v": "v_neck", "plunging": "v_neck", "surplice": "v_neck",
    "boat": "wide", "straight_across": "wide", "square": "wide", "off_shoulder": "wide",
    "queen_anne": "wide",
    "sweetheart": "sweetheart",
    "turtle": "high_neck", "high": "high_neck", "cowl": "high_neck", "choker": "high_neck",
    "halter": "halter", "collarless": "collarless",
    # asymmetric, one_shoulder, illusion, keyhole, crossover: dropped (too rare / ambiguous)
}

GROUP_CLASSES = {
    "pattern": ["plain", "stripe", "floral", "check", "dot", "geometric", "abstract", "text", "graphic", "other"],
    "sleeve": ["sleeveless", "short", "elbow", "three_quarter", "long"],
    "sleeve3": ["short_or_none", "mid", "long"],
    "neckline": ["round_crew", "scoop_u", "v_neck", "wide", "sweetheart", "high_neck", "halter", "collarless"],
}


# --------------------------------------------------------------- annotations
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def stream_coco(path, keep_seg_images: set | None = None, only_images: set | None = None, only_cats: set | None = None, want=("annotations", "images")):
    """Stream a huge Fashionpedia json without loading it whole.

    Returns (categories, attributes, annotations, images). Annotation segmentation is kept only for
    images in keep_seg_images (None = drop all). Images are returned as dict id -> record.
    """
    dec = json.JSONDecoder()
    cats = attrs = None
    anns, images = [], {}
    with open(path, "r", encoding="utf-8") as f:
        buf = f.read(1 << 22)
        pos = 0
        state = None
        eof = False

        def more():
            nonlocal buf, pos, eof
            chunk = f.read(1 << 24)
            if not chunk:
                eof = True
                return
            buf = buf[pos:] + chunk
            pos = 0

        def skip_ws():
            nonlocal pos
            while True:
                while pos < len(buf) and buf[pos] in " \n\r\t,":
                    pos += 1
                if pos < len(buf) or eof:
                    return
                more()

        def decode_value():
            nonlocal pos
            while True:
                skip_ws()
                try:
                    v, end = dec.raw_decode(buf, pos)
                    if end >= len(buf) and not eof:      # number at the buffer edge: need more
                        more()
                        continue
                    pos = end
                    return v
                except json.JSONDecodeError:
                    if eof:
                        raise
                    more()

        skip_ws()
        assert buf[pos] == "{"
        pos += 1
        while True:
            skip_ws()
            if buf[pos] == "}":
                break
            key = decode_value()
            skip_ws()
            while buf[pos] != ":":
                pos += 1
            pos += 1
            skip_ws()
            if key in ("annotations", "images"):
                assert buf[pos] == "["
                pos += 1
                while True:
                    skip_ws()
                    if buf[pos] == "]":
                        pos += 1
                        break
                    item = decode_value()
                    if key == "annotations":
                        if only_images is not None and item["image_id"] not in only_images:
                            continue
                        if only_cats is not None and item["category_id"] not in only_cats:
                            continue
                        if keep_seg_images is None or item["image_id"] not in keep_seg_images:
                            item.pop("segmentation", None)
                        anns.append(item)
                    else:
                        if only_images is None or item["id"] in only_images:
                            images[item["id"]] = item
            else:
                v = decode_value()
                if key == "categories":
                    cats = v
                elif key == "attributes":
                    attrs = v
    return cats, attrs, anns, images


# ------------------------------------------------------------------ rasters
def poly_mask(seg, h, w):
    """Rasterise a COCO polygon list (or return None for RLE/missing)."""
    if not isinstance(seg, list):
        return None
    m = np.zeros((h, w), np.uint8)
    for p in seg:
        if len(p) >= 6:
            cv2.fillPoly(m, [np.round(np.array(p, np.float32).reshape(-1, 2)).astype(np.int32)], 1)
    return m


def pad_square(img, fill=128):
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.full((s, s, 3), fill, np.uint8)
    y0, x0 = (s - h) // 2, (s - w) // 2
    out[y0:y0 + h, x0:x0 + w] = img
    return out


def crop_box(img, box, margin=0.05):
    h, w = img.shape[:2]
    x, y, bw, bh = box
    mx, my = bw * margin, bh * margin
    x0, y0 = int(max(0, x - mx)), int(max(0, y - my))
    x1, y1 = int(min(w, x + bw + mx)), int(min(h, y + bh + my))
    return img[y0:y1, x0:x1], (x0, y0, x1, y1)


def square_context_box(box, factor, w, h):
    x, y, bw, bh = box
    cx, cy = x + bw / 2, y + bh / 2
    s = max(bw, bh) * factor
    x0, y0 = int(max(0, cx - s / 2)), int(max(0, cy - s / 2))
    x1, y1 = int(min(w, cx + s / 2)), int(min(h, cy + s / 2))
    return x0, y0, x1, y1


def save_crop(arr_bgr, path, long_side=256):
    h, w = arr_bgr.shape[:2]
    s = long_side / max(h, w)
    if s < 1:
        arr_bgr = cv2.resize(arr_bgr, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), arr_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])


# -------------------------------------------------------- label derivation
def garment_pattern_label(ann):
    """Return (fine, merged, multi) or None if no pattern attribute."""
    fines = {PATTERN_FINE[a] for a in ann["attribute_ids"] if a in PATTERN_FINE}
    if not fines:
        return None
    nonplain = {f for f in fines if f != "plain"}
    use = nonplain or fines
    merged = {PATTERN_MERGE[f] for f in use}
    if len(merged) == 1:
        return sorted(use)[0] if len(use) == 1 else "+".join(sorted(use)), merged.pop(), False
    return "+".join(sorted(use)), "+".join(sorted(merged)), True


def assign_sleeves(garments, sleeves, h, w):
    """Map each sleeve part to the garment whose mask overlaps its mask most. Returns {garment_ann_id: [sleeve anns]}."""
    gm = {g["id"]: poly_mask(g.get("segmentation"), h, w) for g in garments}
    out = {g["id"]: [] for g in garments}
    for s in sleeves:
        sm = poly_mask(s.get("segmentation"), h, w)
        best, bs = None, 0.0
        for g in garments:
            if gm[g["id"]] is not None and sm is not None:
                ov = float((gm[g["id"]] & sm).sum()) / max(1.0, float(sm.sum()))
            else:
                gx, gy, gw, gh = g["bbox"]
                sx, sy, sw, sh = s["bbox"]
                ix = max(0, min(gx + gw, sx + sw) - max(gx, sx))
                iy = max(0, min(gy + gh, sy + sh) - max(gy, sy))
                ov = ix * iy / max(1.0, sw * sh)
            if ov > bs:
                best, bs = g["id"], ov
        if best is not None and bs >= 0.3:
            out[best].append(s)
    return out


def build_crops(images, anns_by_img, img_dir, split, out_root, log=print):
    """Create crops + manifest rows for pattern / sleeve / neckline groups."""
    rows = []
    n = 0
    for iid, anns in anns_by_img.items():
        rec = images[iid]
        p = Path(img_dir) / rec["file_name"]
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        garments = [a for a in anns if a["category_id"] in PATTERN_CATS and not a.get("iscrowd")]
        # --- pattern
        for g in garments:
            lab = garment_pattern_label(g)
            if lab is None or g["bbox"][2] < 40 or g["bbox"][3] < 40:
                continue
            fine, merged, multi = lab
            raw, (x0, y0, x1, y1) = crop_box(img, g["bbox"])
            cid = f"{split}_{g['id']}"
            save_crop(pad_square(raw), out_root / split / "pattern_raw" / f"{cid}.jpg")
            m = poly_mask(g.get("segmentation"), h, w)
            if m is not None and m.sum() > 100:
                mk = img.copy()
                mk[m == 0] = 128
                save_crop(pad_square(mk[y0:y1, x0:x1]), out_root / split / "pattern_mask" / f"{cid}.jpg")
                has_mask = 1
            else:
                save_crop(pad_square(raw), out_root / split / "pattern_mask" / f"{cid}.jpg")
                has_mask = 0
            rows.append(dict(split=split, group="pattern", crop_id=cid, image_id=iid, file=rec["file_name"],
                             ann_id=g["id"], cat=g["category_id"], label_fine=fine, label=merged,
                             multi=int(multi), has_mask=has_mask, w=raw.shape[1], h=raw.shape[0]))
        # --- sleeve (garment level)
        sleeves = [a for a in anns if a["category_id"] == SLEEVE_PART]
        sg = [g for g in garments if g["bbox"][2] >= 60 and g["bbox"][3] >= 60]
        if sleeves and sg:
            amap = assign_sleeves(sg, sleeves, h, w)
            for g in sg:
                ss = amap[g["id"]]
                labs = [SLEEVE_FINE[a] for s in ss for a in s["attribute_ids"] if a in SLEEVE_FINE]
                if not labs:
                    continue
                longest = max(labs, key=SLEEVE_ORDER.index)
                raw, _ = crop_box(img, g["bbox"])
                cid = f"{split}_{g['id']}"
                save_crop(pad_square(raw), out_root / split / "sleeve" / f"{cid}.jpg")
                rows.append(dict(split=split, group="sleeve", crop_id=cid, image_id=iid, file=rec["file_name"],
                                 ann_id=g["id"], cat=g["category_id"], label_fine=longest, label=longest,
                                 multi=int(len(set(labs)) > 1), has_mask=0, w=raw.shape[1], h=raw.shape[0]))
        # --- neckline (crop around the neckline part)
        for a in anns:
            if a["category_id"] != NECK_PART or a["bbox"][2] < 12 or a["bbox"][3] < 8:
                continue
            fines = [NECK_FINE[i] for i in a["attribute_ids"] if i in NECK_FINE]
            if len(fines) != 1:
                continue
            merged = NECK_MERGE.get(fines[0])
            if merged is None:
                continue
            x0, y0, x1, y1 = square_context_box(a["bbox"], 2.4, w, h)
            if x1 - x0 < 30 or y1 - y0 < 30:
                continue
            cid = f"{split}_{a['id']}"
            save_crop(pad_square(img[y0:y1, x0:x1]), out_root / split / "neckline" / f"{cid}.jpg")
            rows.append(dict(split=split, group="neckline", crop_id=cid, image_id=iid, file=rec["file_name"],
                             ann_id=a["id"], cat=a["category_id"], label_fine=fines[0], label=merged,
                             multi=0, has_mask=0, w=x1 - x0, h=y1 - y0))
        n += 1
        if n % 200 == 0:
            log(f"  {n} images processed, {len(rows)} crops")
    return rows


def crop_path(out_root, split, group, crop_id, variant=None):
    sub = {"pattern": f"pattern_{variant or 'mask'}", "sleeve": "sleeve", "neckline": "neckline"}[group]
    return Path(out_root) / split / sub / f"{crop_id}.jpg"
