"""P06: sleeve-length class accuracy of cv_shape on (a) the 5 Mirra photos (approximate reference labels) and
(b) Fashionpedia val garments with a sleeve-length attribute (street photos, garment polygon rasterised; categories
shirt/blouse, top/t-shirt/sweatshirt, sweater; mask must cover >= 3% of the image and not touch the left/right/bottom image edge
twice). Outputs stats/sleeve_eval_*.csv/json. Run from repo root."""
import json, csv, numpy as np, cv2, collections
from p06_common import *
CLS = ["sleeveless", "short", "elbow", "three_quarter", "long"]
ATTR = {156: "sleeveless", 157: "short", 158: "elbow", 159: "three_quarter", 160: "long"}
def conf(rows, key_t="true", key_p="pred"):
    M = np.zeros((5, 5), int)
    for r in rows: M[CLS.index(r[key_t]), CLS.index(r[key_p])] += 1
    return M
def summarize(rows):
    M = conf(rows); n = M.sum()
    acc = np.trace(M) / n if n else None
    w1 = sum(M[i, j] for i in range(5) for j in range(5) if abs(i - j) <= 1) / n if n else None
    maj = M.sum(1).max() / n if n else None
    return {"n": int(n), "accuracy": acc, "within_one_class": w1, "majority_baseline": maj, "confusion_rows_true_cols_pred": M.tolist(), "classes": CLS}
def main():
    lab = labels(); rows = []
    for c in CLOTHS:
        img, m = load_mirra(c); r = cv_shape.analyze_shape(m, c)
        t = lab[c]["sleeve"].replace("-", "_")
        rows.append({"id": c, "true": t, "pred": r["sleeve"]["class"], "ratio": r["sleeve"]["length_over_garment_length"], "presentation": lab[c]["presentation"], "view": lab[c]["view"]})
    with open(OUT / "stats" / "sleeve_eval_mirra.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    out = {"mirra": summarize(rows)}
    print(rows); print(out["mirra"])
    # Fashionpedia
    d = json.load(open(REPO / "product_ingestion/CV/data/fashionpedia/instances_attributes_val2020.json"))
    imsz = {im["id"]: (im["height"], im["width"]) for im in d["images"]}
    rng = np.random.RandomState(0)
    byimg = collections.defaultdict(list)
    for a in d["annotations"]:
        if a.get("iscrowd") or not isinstance(a["segmentation"], list): continue
        byimg[a["image_id"]].append(a)
    def raster(a, h, w):
        m = np.zeros((h, w), np.uint8)
        for poly in a["segmentation"]:
            p = np.array(poly, np.float32).reshape(-1, 2)
            if len(p) >= 3: cv2.fillPoly(m, [np.round(p).astype(np.int32)], 1)
        return m
    # sleeve-length attributes live on the SLEEVE part (category 31): label a garment (cat 0,1,2) by the sleeve parts inside it
    cand = []
    for iid, L in byimg.items():
        slv = [a for a in L if a["category_id"] == 31 and any(x in ATTR for x in a["attribute_ids"])]
        if not slv: continue
        for g in (a for a in L if a["category_id"] in (0, 1, 2)):
            cand.append((iid, g, slv))
    print("garments with sleeve parts", len(cand))
    rng.shuffle(cand)
    frows = []
    cnt = collections.Counter()
    for iid, g, slv in cand:
        h, w = imsz[iid]
        gm = raster(g, h, w)
        if gm.mean() < 0.03: continue
        labs = []
        for sp in slv:
            sm = raster(sp, h, w)
            if sm.sum() > 0 and (sm & gm).sum() / sm.sum() >= 0.5:
                labs += [ATTR[x] for x in sp["attribute_ids"] if x in ATTR]
        if not labs or len(set(labs)) != 1: continue
        t = labs[0]
        if cnt[t] >= 150: continue
        x, y, bw, bh = [int(v) for v in g["bbox"]]
        crop = gm[max(y - 4, 0):y + bh + 4, max(x - 4, 0):x + bw + 4]
        cr = cv_shape.analyze_shape(crop, str(g["id"]))
        if not cr["ok"]: continue
        cnt[t] += 1
        frows.append({"id": g["id"], "image_id": iid, "true": t, "pred": cr["sleeve"]["class"], "ratio": cr["sleeve"]["length_over_garment_length"],
                      "flags": "|".join(cr["flags"]), "cat": g["category_id"]})
    with open(OUT / "stats" / "sleeve_eval_fashionpedia.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(frows[0].keys())); w.writeheader(); w.writerows(frows)
    out["fashionpedia"] = summarize(frows)
    # ratio per true class
    out["fashionpedia_ratio_by_true_class"] = {t: {"n": len([r for r in frows if r["true"] == t]),
        "median": float(np.median([r["ratio"] for r in frows if r["true"] == t])) if any(r["true"] == t for r in frows) else None} for t in CLS}
    json.dump(out, open(OUT / "stats" / "sleeve_eval.json", "w"), indent=1)
    print(out["fashionpedia"]); print(out["fashionpedia_ratio_by_true_class"])
main()
