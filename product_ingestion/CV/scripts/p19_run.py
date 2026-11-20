"""P19/P18 experiment: v0 (bbox homography) vs v1 (landmark affine / TPS) on 5 Mirra photos + VITON-HD flats.
Run from repo root:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p19_run.py [--viton 4]
Outputs: out/p19_panel_maps/<v0|v1_tps>/<cloth>/ (textures, metadata, figure, error maps), metrics.json, metrics.csv
"""
import sys, json, time, csv, io, contextlib, tempfile, shutil, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
import step_06_0_texture_projection as S6
import cv_texture_check as TC

ap = argparse.ArgumentParser()
ap.add_argument("--viton", type=int, default=4)
args = ap.parse_args()
np.random.seed(0)
L = s001_layouts()
photos = {}
for c, v in load_mirra().items():
    photos[c] = dict(rgb=v["rgb"], mask=v["mask"], view=v["label"]["view"], on_person=v["label"]["presentation"] == "on_person", src="mirra")
if args.viton:
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(str(CV / "data/vitonhd_test/data/train-00000-of-00002-d373a9018965c120.parquet"))
    b = next(pf.iter_batches(batch_size=args.viton, columns=["cloth", "cloth_mask"])).to_pylist()
    for i, row in enumerate(b):
        im = cv2.cvtColor(cv2.imdecode(np.frombuffer(row["cloth"]["bytes"], np.uint8), 1), cv2.COLOR_BGR2RGB)
        mk = cv2.imdecode(np.frombuffer(row["cloth_mask"]["bytes"], np.uint8), 0)
        photos[f"viton_{i}"] = dict(rgb=im, mask=(mk > 127).astype(np.uint8) * 255, view="front", on_person=False, src="vitonhd_test")


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def run_v1(p, out_dir, warp):
    isf = p["view"] == "front"
    rgba = np.dstack([p["rgb"], p["mask"]])
    return quiet(S6.project_textures, rgba, L, out_dir, method="v1", garment_mask=p["mask"], view=p["view"],
                 on_person=p["on_person"], warp=warp)


rows, full = [], {}
for name, p in photos.items():
    full[name] = {}
    figs = {}
    # ---- v0
    d0 = OUT / "v0" / name; d0.mkdir(parents=True, exist_ok=True)
    t = time.time()
    r0 = quiet(S6.project_textures, np.dstack([p["rgb"], p["mask"]]), L, d0, method="v0")
    t0 = time.time() - t
    rec0 = TC.reproject_v0(p["rgb"], p["mask"] > 0, L, d0)
    m0 = TC.metrics(rec0["ref"], rec0["recon"], rec0["mask"], rec0["ok"])
    # ---- v1 tps (saved) and affine (temp)
    d1 = OUT / "v1_tps" / name; d1.mkdir(parents=True, exist_ok=True)
    t = time.time(); r1 = run_v1(p, d1, "tps"); t1 = time.time() - t
    tmp = Path(tempfile.mkdtemp(prefix="p19aff_"))
    ra = run_v1(p, tmp, "affine")
    res = {}
    for tag, rr in (("v1_tps", r1), ("v1_affine", ra)):
        rc = TC.reproject_v1(rr)
        vn = list(rc)[0]
        rec = rc[vn]
        m = TC.metrics(rec["ref"], rec["recon"], rec["mask"], rec["ok"])
        res[tag] = (rec, m, rr)
        if tag == "v1_affine":
            pass
    # silhouette iou for affine uses temp textures -> computed already inside reproject
    allm = {"v0": (rec0, m0, r0), **res}
    for tag, (rec, m, rr) in allm.items():
        sil = rec["sil_iou"]
        fillf = None
        if tag != "v0":
            pcs = rr.projection_metadata["pieces"]
            fillf = {k: v["filled_fraction"] for k, v in pcs.items()}
        entry = {k: v for k, v in m.items() if not k.startswith("_")}
        entry["silhouette_iou"] = sil
        entry["filled_fraction"] = fillf
        full[name][tag] = entry
        rows.append(dict(photo=name, method=tag, dE_mean=m["dE_mean"], dE_median=m["dE_median"], dE_p95=m["dE_p95"], ssim=m["ssim"],
                         covered_share=m["covered_share"], sil_iou_body=sil.get("front_panel", sil.get("back_panel")),
                         sil_iou_sleeves=(round(float(np.mean([v for k, v in sil.items() if "sleeve" in k])), 4) if any("sleeve" in k for k in sil) else None)))
    # ---- figures: photo | err v0 | err v1 ; flat previews
    ph = p["rgb"]
    ph_s = 420 / ph.shape[0]
    def sc(im):
        return cv2.resize(im, None, fx=ph_s, fy=ph_s, interpolation=cv2.INTER_AREA)
    e0 = TC.error_map_image(rec0["ref"], rec0["mask"], m0["_dE_map"]) if m0.get("_dE_map") is not None else ph
    rec1, m1, _ = res["v1_tps"]
    e1 = TC.error_map_image(rec1["ref"], rec1["mask"], m1["_dE_map"]) if m1.get("_dE_map") is not None else ph
    r1c = np.where(rec1["ok"][..., None], rec1["recon"], 0).astype(np.uint8)
    r0c = np.where(rec0["ok"][..., None], rec0["recon"], 0).astype(np.uint8)
    top = np.hstack([sc(ph), sc(r0c), sc(e0), sc(r1c) if r1c.shape == ph.shape else sc(cv2.resize(r1c, (ph.shape[1], ph.shape[0]))),
                     sc(e1) if e1.shape == ph.shape else sc(cv2.resize(e1, (ph.shape[1], ph.shape[0])))])
    f0 = TC.flat_preview(d0, L, d0 / "flat_preview.jpg", height=420)
    f1 = TC.flat_preview(d1, L, d1 / "flat_preview.jpg", height=420)
    W = max(top.shape[1], f0.shape[1], f1.shape[1])
    pad = lambda a: np.pad(a, ((0, 0), (0, W - a.shape[1]), (0, 0)), constant_values=255)
    fig = np.vstack([pad(top), pad(f0), pad(f1)])
    figp = OUT / f"fig_{name}.jpg"
    cv2.imwrite(str(figp), fig[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 72])
    cv2.imwrite(str(d1 / "reproj_error_map.jpg"), e1[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
    cv2.imwrite(str(d0 / "reproj_error_map.jpg"), e0[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
    cv2.imwrite(str(d1 / "reprojected_photo.jpg"), r1c[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 80])
    shutil.copy(figp, d1 / "side_by_side.jpg")
    shutil.rmtree(tmp, ignore_errors=True)
    print(name, {r["method"]: (r["dE_mean"], r["ssim"], r["covered_share"], r["sil_iou_body"]) for r in rows if r["photo"] == name}, f"v0 {t0:.1f}s v1 {t1:.1f}s", flush=True)

json.dump(full, open(OUT / "metrics.json", "w"), indent=1)
with open(OUT / "metrics.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("done")
