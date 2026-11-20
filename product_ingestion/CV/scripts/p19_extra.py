"""P19 extras: (a) two-photo path (c_004 front + c_002 back, different shirts - path test only),
(b) c_003 colour-block boundary position in the front texture (v0 vs v1), (c) metadata sample."""
import sys, json, io, contextlib; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
import step_06_0_texture_projection as S6
import cv_texture_check as TC
L = s001_layouts(); d = load_mirra()
q = lambda f, *a, **k: (lambda b: (contextlib.redirect_stdout(b).__enter__(), f(*a, **k))[1])(io.StringIO())
def quiet(f, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a, **k)
# (a)
out = OUT / "v1_tps" / "pair_c004front_c002back"; out.mkdir(parents=True, exist_ok=True)
f, b = d["c_004"], d["c_002"]
r = quiet(S6.project_textures, np.dstack([f["rgb"], f["mask"]]), L, out, method="v1", garment_mask=f["mask"], back_rgba=np.dstack([b["rgb"], b["mask"]]), back_mask=b["mask"], view="front")
TC.flat_preview(out, L, out / "flat_preview.jpg", height=420)
pc = r.projection_metadata["pieces"]
print("pair:", r.method, {k: (v["texture_size_px"], v["source"], v["assumptions"][:1]) for k, v in pc.items()})
# (b) colour boundary c_003: row where the centre-column lightness crosses the mid between white and teal
v = d["c_003"]
def boundary(tex_path, label):
    t = np.array(__import__("PIL.Image", fromlist=["x"]).open(tex_path).convert("RGBA"))
    a = t[:, :, 3] > 127
    h, w = a.shape
    cols = slice(int(w * 0.4), int(w * 0.6))
    L_ = cv2.cvtColor(t[:, :, :3], cv2.COLOR_RGB2GRAY)[:, cols].astype(float)
    A = a[:, cols]
    prof = np.array([L_[i][A[i]].mean() if A[i].any() else np.nan for i in range(h)])
    top = np.nanmedian(prof[int(h * 0.15):int(h * 0.3)]); bot = np.nanmedian(prof[int(h * 0.8):int(h * 0.95)])
    # last row (from top) where a 15-row mean is brighter than the middle value = end of white/stripe band
    mid = 0.5 * (top + bot)
    sm = np.convolve(np.nan_to_num(prof, nan=bot), np.ones(15) / 15, "same")
    idx = np.where(sm > mid)[0]
    rb = int(idx.max()) if len(idx) else -1
    return dict(label=label, top_gray=round(top, 1), bottom_gray=round(bot, 1), boundary_row=rb, boundary_frac_of_panel_height=round(rb / h, 3), size=[w, h])
res = [boundary(OUT / "v0/c_003/front_panel_texture.png", "v0 front"), boundary(OUT / "v1_tps/c_003/front_panel_texture.png", "v1 front"),
       boundary(OUT / "v1_tps/c_003/back_panel_texture.png", "v1 back (print-free from front)")]
# photo reference: boundary row in the photo, expressed from photo top
m = v["mask"] > 0; g = cv2.cvtColor(v["rgb"], cv2.COLOR_RGB2GRAY).astype(float)
cs = slice(int(v["rgb"].shape[1] * 0.4), int(v["rgb"].shape[1] * 0.6))
prof = np.array([g[i, cs][m[i, cs]].mean() if m[i, cs].any() else np.nan for i in range(g.shape[0])])
H = g.shape[0]; top = np.nanmedian(prof[int(H * .15):int(H * .3)]); bot = np.nanmedian(prof[int(H * .8):int(H * .95)]); mid = .5 * (top + bot)
sm = np.convolve(np.nan_to_num(prof, nan=bot), np.ones(15) / 15, "same"); rb = int(np.where(sm > mid)[0].max())
res.append(dict(label="photo (fraction of photo height; photo is cropped top and bottom)", boundary_row=rb, boundary_frac_of_panel_height=round(rb / H, 3), size=list(v["rgb"].shape[1::-1])))
json.dump(res, open(OUT / "c003_colour_boundary.json", "w"), indent=1)
for x in res: print(x)
# (c) metadata sample
m1 = json.load(open(OUT / "v1_tps/c_003/texture_projection_metadata.json"))
s = {k: (v if k != "pieces" else {p: {kk: (vv if kk != "panel_polygon_px" else f"[{len(vv)} points]") for kk, vv in pv.items()} for p, pv in v.items()}) for k, v in m1.items()}
json.dump(s, open(OUT / "metadata_sample_c_003.json", "w"), indent=1)
