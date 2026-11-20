"""P16: multi-photo test sets from In-shop items and the metrics for them (shared by tuning and evaluation).

A set = all photos of one item with >= 2 photos (shuffled), plus (for about half of the sets) one photo of a
different item (the foreign photo).  Truth: front photos = 1_front/4_full, back = 3_back, side = 2_side.
"""
from __future__ import annotations

import numpy as np

from multi_view import assemble, VIEW_CLASSES


def build_sets(meta, indices, seed=0, foreign_frac=0.5, max_photos=8):
    """meta: list of dicts (item, view, fine); indices: usable photo indices.  Returns list of dicts."""
    rng = np.random.RandomState(seed)
    by_item = {}
    for i in indices:
        by_item.setdefault(meta[i]["item"], []).append(int(i))
    items = sorted(k for k, v in by_item.items() if len(v) >= 2)
    all_items = sorted(by_item)
    sets = []
    for k, it in enumerate(items):
        idx = list(by_item[it])
        rng.shuffle(idx)
        idx = idx[:max_photos]
        foreign = None
        if rng.rand() < foreign_frac:
            while True:
                other = all_items[rng.randint(len(all_items))]
                if other != it:
                    break
            foreign = int(rng.choice(by_item[other]))
            idx = idx + [foreign]
            rng.shuffle(idx)
        sets.append({"set_id": f"set_{k:03d}", "item": it, "indices": idx, "foreign": foreign})
    return sets


def truth_for(meta, s):
    idx = s["indices"]
    own = [i for i in idx if i != s["foreign"]]
    return {"front": [i for i in own if meta[i]["view"] == "front"],
            "back": [i for i in own if meta[i]["view"] == "back"],
            "side": [i for i in own if meta[i]["view"] == "side"]}


def score_assignment(meta, s, front_idx, back_idx, outlier_idx):
    """Returns dict of per-set booleans (None = not applicable)."""
    t = truth_for(meta, s)
    r = {"has_front": bool(t["front"]), "has_back": bool(t["back"]), "has_foreign": s["foreign"] is not None}
    r["front_ok"] = (front_idx in t["front"]) if t["front"] else None
    if t["back"]:
        r["back_ok"] = back_idx in t["back"]
        r["back_none_ok"] = None
    else:
        r["back_ok"] = None
        r["back_none_ok"] = back_idx is None          # no back in truth -> should report none
    if t["front"]:
        if t["back"]:
            r["pair_ok"] = (front_idx in t["front"]) and (back_idx in t["back"])
        else:
            r["pair_ok"] = (front_idx in t["front"]) and (back_idx is None)
    else:
        r["pair_ok"] = None
    out = set(outlier_idx)
    r["foreign_found"] = (s["foreign"] in out) if s["foreign"] is not None else None
    own = set(i for i in s["indices"] if i != s["foreign"])
    r["false_outliers"] = len(out & own)
    r["n_own"] = len(own)
    return r


def summarise(rows):
    def rate(key):
        v = [r[key] for r in rows if r[key] is not None]
        return (float(np.mean(v)) if v else float("nan")), len(v)
    out = {}
    for k in ("front_ok", "back_ok", "back_none_ok", "pair_ok", "foreign_found"):
        out[k], out[k + "_n"] = rate(k)
    fo = [r["false_outliers"] for r in rows]
    n_own = [r["n_own"] for r in rows]
    out["false_outlier_photo_rate"] = float(np.sum(fo) / np.sum(n_own))
    return out


def run_feature_level(meta, sets, view_probs, pair_prob_fn, cues, params, pres_probs=None, other_prob=None):
    """Assign views to every set from cached features.  view_probs: (n_photos_total, 4) rows aligned with meta.
    pair_prob_fn(i, j) -> same-garment probability for global photo indices; cues: dict of arrays."""
    rows = []
    for s in sets:
        idx = s["indices"]
        n = len(idx)
        P = np.eye(n)
        for a in range(n):
            for b in range(a + 1, n):
                P[a, b] = P[b, a] = pair_prob_fn(idx[a], idx[b])
        cl = [{"blur": cues["blur"][i], "garment_area": cues["area"][i], "touches_frame": cues["touches"][i],
               "face_found": bool(cues["face"][i])} for i in idx]
        paths = [str(i) for i in idx]
        pp = np.zeros((n, 0)) if pres_probs is None else pres_probs[idx]
        op = np.zeros(n) if other_prob is None else other_prob[idx]
        va = assemble(paths, view_probs[idx], pp, [] if pres_probs is None else ["flat", "person"], op, cl, P, params, "feature-level")
        f = int(va.front)
        b = int(va.back) if va.back is not None else None
        rows.append(score_assignment(meta, s, f, b, [int(x) for x in va.outliers]))
    return rows
