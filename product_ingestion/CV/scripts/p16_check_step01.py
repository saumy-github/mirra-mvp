"""P16: smoke tests of the changed step files and of the zero-shot 'other' (size chart / label) check.
Run: .venv/Scripts/python.exe product_ingestion/CV/scripts/p16_check_step01.py
Writes out/p16_multiview/check_step01.json and synthetic/ (two generated test pages)."""
import json, sys, gc
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from p16_common import OUT, FEAT, loadf
from gpu_lock import gpu_lock
import multi_view as mv
import step_01_0_view_selection as s0

res = {}
syn = OUT / "synthetic"; syn.mkdir(exist_ok=True)
# synthetic size chart and label page (generated here, not photos)
im = Image.new("RGB", (480, 480), "white"); d = ImageDraw.Draw(im)
d.text((20, 15), "SIZE CHART (cm)", fill="black")
for r, row in enumerate([["Size", "Chest", "Length", "Sleeve"], ["S", "92", "68", "20"], ["M", "98", "70", "21"], ["L", "104", "72", "22"], ["XL", "110", "74", "23"]]):
    for c, t in enumerate(row):
        d.text((30 + c * 110, 60 + r * 40), t, fill="black")
    d.line((20, 80 + r * 40, 460, 80 + r * 40), fill="gray")
im.save(syn / "size_chart.png")
im = Image.new("RGB", (300, 400), (235, 235, 235)); d = ImageDraw.Draw(im)
d.rectangle((60, 60, 240, 340), fill="white", outline="black")
for k, t in enumerate(["100% COTTON", "SIZE M", "MACHINE WASH 30C", "MADE IN INDIA", "DO NOT BLEACH"]):
    d.text((75, 90 + k * 45), t, fill="black")
im.save(syn / "care_label.png")

with gpu_lock("p16"):
    b = mv.load_bundle()
    emb = mv.get_embedder(b["backbone"])
    f = emb.encode([Image.open(syn / "size_chart.png"), Image.open(syn / "care_label.png")])
    res["other_prob_size_chart_label"] = [float(x) for x in mv.other_probability(f, b)]
    # single photo: no model needed
    sel = s0.select_primary_image(HERE.parents[1] / "input" / "c_001")
    res["single_photo"] = {"selected": str(sel.selected_image), "reason": sel.selection_reason}
    # multi photo folder from the test sets
    ts = sorted((OUT / "testsets").glob("set_*"))
    outs = []
    for d_ in ts[:3]:
        folder = d_
        sel = s0.select_primary_image(folder)
        va = s0.select_views(folder)
        outs.append({"set": d_.name, "reason": sel.selection_reason, "selected": Path(sel.selected_image).name,
                     "views": [(v.filename, v.label) for v in sel.views], "assignment_front": Path(va.front).name,
                     "assignment_back": Path(va.back).name if va.back else None})
    res["multi_photo"] = outs
    # router API (trained) keeps the RoutingResult type
    from step_01_1_garment_router import GarmentRouter
    rr = GarmentRouter(method="trained").route_images(str(ts[0]))
    res["router_trained"] = {"best_front": Path(rr.best_front).name, "best_back": Path(rr.best_back).name if rr.best_back else None,
                             "n_scores": len(rr.all_scores)}
    for k in list(mv._CACHE):
        if k[0] == "emb":
            mv._CACHE[k].close(); del mv._CACHE[k]
    gc.collect()
# v0 path still selectable (expected to fail to load CLIP on torch 2.4.1 and fall back)
try:
    sel0 = s0.select_primary_image(ts[0], method="v0")
    res["v0_multi"] = {"selected": Path(sel0.selected_image).name, "reason": sel0.selection_reason}
except Exception as e:  # noqa: BLE001
    res["v0_multi"] = {"error": repr(e)[:300]}
sel_skip = s0.select_primary_image(ts[0], skip_clip=True)
res["skip_clip"] = {"selected": Path(sel_skip.selected_image).name, "reason": sel_skip.selection_reason}
# false positives of the 'other' check on real garment photos
Xte = loadf(FEAT / "siglip2_inshop_test.npy")
po = mv.other_probability(Xte, b)
res["other_false_positive_rate_inshop_test"] = float((po >= 0.6).mean())
Xm = loadf(FEAT / "siglip2_mirra.npy")
res["other_prob_mirra"] = [float(x) for x in mv.other_probability(Xm, b)]
(OUT / "check_step01.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
