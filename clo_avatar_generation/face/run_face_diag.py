#!/usr/bin/env python3
"""
Mirra face pipeline — full diagnostic run.
Usage (from repo root):
    python clo_avatar_generation/face/run_face_diag.py
"""

from __future__ import annotations

import io
import json
import sys
import traceback
import zipfile
from pathlib import Path

import cv2
import numpy as np

# ── repo paths ─────────────────────────────────────────────────────────────────
_THIS    = Path(__file__).resolve()
REPO     = _THIS.parents[2]
FACE_DIR = _THIS.parent
INPUT    = REPO / "clo_avatar_generation" / "input"
OUT_DIR  = REPO / "output" / "face_diag"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO))

USER_ID    = "u_001"
FRONT_PH   = INPUT / "face" / USER_ID / "front.jpg"
LEFT_PH    = INPUT / "face" / USER_ID / "left.jpg"
RIGHT_PH   = INPUT / "face" / USER_ID / "right.jpg"
SOURCE_AVT = INPUT / "base-1.avt"
OUTPUT_AVT = OUT_DIR / f"{USER_ID}_face.avt"
UV_JSON    = FACE_DIR / "templates" / "base-1-face-uv.json"
SPRITES_DIR = FACE_DIR / "sprites"

SEP = "=" * 62


# ── warp index constants (mirrors warp.py exactly) ────────────────────────────
_BASE_WARP_RAW: list[int] = [
    338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
    70, 107, 300, 336,
    33, 133, 159, 145, 362, 263, 386, 374,
    4, 6, 168,
    61, 291, 17,
    152,
    116, 345,
]
_EYE_BROW: set[int] = {70, 107, 300, 336, 33, 133, 159, 145, 362, 263, 386, 374}
_BAD_UV: dict[int, str] = {
    0:  "mouth-center — UV projects to x=1983 (far right)",
    10: "forehead     — UV projects to x=1940 (far right)",
}

_seen: set[int] = set()
BASE_WARP: list[int] = [i for i in _BASE_WARP_RAW if not (i in _seen or _seen.add(i))]

# Region membership (for coloring and zone checks)
_OVAL  = {338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
           152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109}
_BROW  = {70, 107, 300, 336}
_EYE   = {33, 133, 159, 145, 362, 263, 386, 374}
_NOSE  = {4, 6, 168}
_MOUTH = {61, 291, 17}
_CHEEK = {116, 345}

_REGION_COLOR = {
    "oval":  (255, 60, 60),   # blue-ish (BGR)
    "brow":  (0, 165, 255),   # orange
    "eye":   (0, 255, 255),   # yellow
    "nose":  (0, 255, 0),     # green
    "mouth": (0, 200, 255),   # gold
    "cheek": (255, 100, 0),   # teal
}

def _region(idx: int) -> str:
    if idx in _BROW:  return "brow"
    if idx in _EYE:   return "eye"
    if idx in _NOSE:  return "nose"
    if idx in _MOUTH: return "mouth"
    if idx in _CHEEK: return "cheek"
    if idx in _OVAL:  return "oval"
    return "other"


# ── anatomical zones (pixel coords in 2048×2048 face texture) ─────────────────
# Derived from observed UV positions in base-1-face-uv.json.
# Each dict: "y": (lo, hi), "x": (lo, hi), "members": set of landmark indices
_ZONES: dict[str, dict] = {
    "brow":   {"y": (380, 620),  "x": (640,  1450), "members": _BROW},
    "eye":    {"y": (560, 820),  "x": (580,  1480), "members": _EYE},
    "nose":   {"y": (600, 840),  "x": (830,  1200), "members": _NOSE},
    "mouth":  {"y": (820, 990),  "x": (790,  1270), "members": _MOUTH},
    "cheek":  {"y": (620, 900),  "x": (480,  1550), "members": _CHEEK},
    "oval":   {"y": (296, 1150), "x": (300,  1940), "members": _OVAL},
}

def _in_zone(idx: int, x: int, y: int) -> tuple[str, bool]:
    """Return (zone_name, is_ok). 'oval' used as fallback for oval landmarks."""
    for zname, zinfo in _ZONES.items():
        if idx in zinfo["members"]:
            xl, xh = zinfo["x"]
            yl, yh = zinfo["y"]
            return zname, (xl <= x <= xh and yl <= y <= yh)
    return "?", True  # unzoned landmarks pass by default


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Run the pipeline
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 1 — Pipeline Run")
print(SEP)
print(f"  front : {FRONT_PH}")
print(f"  left  : {LEFT_PH}")
print(f"  right : {RIGHT_PH}")
print(f"  avt   : {SOURCE_AVT}")
print(f"  out   : {OUTPUT_AVT}")

result: dict | None = None
pipeline_error: Exception | None = None

try:
    from clo_avatar_generation.face.run_face import run as face_run
    print("\n  [running...]\n")
    result = face_run(
        front_photo=FRONT_PH,
        source_avt=SOURCE_AVT,
        output_avt=OUTPUT_AVT,
        left_photo=LEFT_PH,
        right_photo=RIGHT_PH,
    )
    if result.get("success"):
        print(f"  Pipeline:        SUCCESS")
        print(f"  Photos used:     {result['photos_used']}")
        print(f"  Face bbox (px):  {result.get('face_bbox', 'n/a')}")
        print(f"  Hair colorized:  {result.get('hair_colorized')}")
        mr = result.get("morph_result", {})
        print(f"\n  morph.py:")
        print(f"    success:         {mr.get('success')}")
        if mr.get("success"):
            print(f"    verts displaced: {mr['vertices_displaced']:,} / {mr['vertices_total']:,}")
            print(f"    max disp (mm):   {mr['max_displacement_mm']}")
            mv = mr.get("mesh_validation", {})
            print(f"    mesh valid:      {mv.get('valid')}  watertight={mv.get('watertight')}")
        else:
            print(f"    reason:          {mr.get('reason', 'unknown')}")
    else:
        print(f"  Pipeline:        FAILED — {result.get('reason')}")
except Exception as exc:
    pipeline_error = exc
    print(f"  Pipeline:        EXCEPTION")
    traceback.print_exc()

# AVT validation
print(f"\n  Output AVT check:")
avt_valid = False
if OUTPUT_AVT.exists():
    try:
        raw = OUTPUT_AVT.read_bytes()
        zs  = raw.find(b"PK\x03\x04")
        with zipfile.ZipFile(io.BytesIO(raw[zs:]), "r") as z:
            members = z.namelist()
        avt_valid = "MV2_Jinho_01_face.jpg" in members
        print(f"    exists:         YES  ({OUTPUT_AVT.stat().st_size/1024:.0f} KB)")
        print(f"    valid ZIP:      YES  ({len(members)} members)")
        print(f"    face.jpg in it: {'YES' if avt_valid else 'NO'}")
    except Exception as e:
        print(f"    read error:     {e}")
else:
    print(f"    exists:         NO")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Landmark audit: draw all warp landmarks on the atlas
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 2 — Landmark Audit (drawing on face texture atlas)")
print(SEP)

uv      = json.loads(UV_JSON.read_text(encoding="utf-8"))
uv_w, uv_h = uv["texture_size"]
all_px  = uv["all_478_landmark_pixels"]
oval_px = uv["face_oval_pixels"]

# Load base face texture
raw_avt = SOURCE_AVT.read_bytes()
zs_avt  = raw_avt.find(b"PK\x03\x04")
with zipfile.ZipFile(io.BytesIO(raw_avt[zs_avt:]), "r") as zf:
    base_tex = cv2.imdecode(
        np.frombuffer(zf.read("MV2_Jinho_01_face.jpg"), np.uint8),
        cv2.IMREAD_COLOR,
    )
if base_tex.shape[:2] != (uv_h, uv_w):
    base_tex = cv2.resize(base_tex, (uv_w, uv_h))

atlas = base_tex.copy()

# Draw oval boundary for reference
oval_pts = np.array(oval_px, dtype=np.int32)
cv2.polylines(atlas, [oval_pts], isClosed=True, color=(100, 100, 100), thickness=2)

# Draw active warp landmarks
for idx in BASE_WARP:
    x, y   = all_px[idx]
    reg    = _region(idx)
    col    = _REGION_COLOR.get(reg, (255, 255, 255))
    cv2.circle(atlas, (x, y), 10, col, -1)
    cv2.putText(atlas, str(idx), (x + 12, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

# Draw bad landmarks (excluded) in red with X
for idx, reason in _BAD_UV.items():
    x, y = all_px[idx]
    cv2.circle(atlas, (x, y), 12, (0, 0, 220), 2)
    cv2.drawMarker(atlas, (x, y), (0, 0, 220), cv2.MARKER_TILTED_CROSS, 22, 2)
    cv2.putText(atlas, f"BAD:{idx}", (x + 14, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 220), 1, cv2.LINE_AA)

# Legend
legends = [
    ("oval",  _REGION_COLOR["oval"]),
    ("brow",  _REGION_COLOR["brow"]),
    ("eye",   _REGION_COLOR["eye"]),
    ("nose",  _REGION_COLOR["nose"]),
    ("mouth", _REGION_COLOR["mouth"]),
    ("cheek", _REGION_COLOR["cheek"]),
    ("BAD (excluded)", (0, 0, 220)),
]
ly = 40
for label, col in legends:
    cv2.rectangle(atlas, (12, ly - 14), (36, ly + 8), col, -1)
    cv2.putText(atlas, label, (42, ly + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1, cv2.LINE_AA)
    ly += 34

out_lm = OUT_DIR / "debug_all_landmarks.png"
cv2.imwrite(str(out_lm), atlas)
print(f"  Saved: {out_lm}")
print(f"  Total active warp landmarks: {len(BASE_WARP)}")
print(f"  Bad UV (excluded): {list(_BAD_UV.keys())}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Anatomical sanity check
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 3 — Anatomical Sanity Check")
print(SEP)
print(f"\n  {'IDX':>4}  {'REGION':<6}  {'ZONE':<6}  {'X':>5}  {'Y':>5}  STATUS")
print(f"  {'-' * 50}")

suspicious: list[int] = []
n_checked = n_ok = 0

for idx in BASE_WARP:
    x, y       = all_px[idx]
    reg        = _region(idx)
    zone, ok   = _in_zone(idx, x, y)
    if zone == "?":
        continue
    n_checked += 1
    flag = "✅" if ok else "❌  SUSPICIOUS"
    if ok:
        n_ok += 1
    else:
        suspicious.append(idx)
    print(f"  {idx:>4}  {reg:<6}  {zone:<6}  {x:>5}  {y:>5}  {flag}")

pct = int(100 * n_ok / n_checked) if n_checked else 0
print(f"\n  Zone-checked: {n_checked} landmarks")
print(f"  Passing:      {n_ok} / {n_checked} ({pct}%)")
if suspicious:
    print(f"  Suspicious:   {suspicious}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Side-by-side debug image
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 4 — Side-by-Side Debug Image")
print(SEP)

TARGET_H = 1024

def _resize_h(img: np.ndarray, h: int) -> np.ndarray:
    ratio = h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * ratio), h))

# Col 1: front photo with warp landmarks overlaid
col1_ok = False
col1    = np.zeros((TARGET_H, TARGET_H, 3), dtype=np.uint8)
try:
    from clo_avatar_generation.face.detect import detect
    front_img = cv2.imread(str(FRONT_PH))
    front_lm  = detect(FRONT_PH)
    if front_lm["detected"]:
        ph, pw = front_img.shape[:2]
        for idx in BASE_WARP:
            if idx < len(front_lm["landmarks_px"]):
                fx, fy = front_lm["landmarks_px"][idx]
                reg = _region(idx)
                col = _REGION_COLOR.get(reg, (255, 255, 255))
                cv2.circle(front_img, (fx, fy), max(3, pw // 150), col, -1)
        col1    = _resize_h(front_img, TARGET_H)
        col1_ok = True
        print(f"  Col1 (front + landmarks): OK  ({pw}x{ph})")
    else:
        print("  Col1: MediaPipe detected no face in front photo")
except Exception as e:
    print(f"  Col1 error: {e}")

# Col 2: output face texture from patched AVT
col2_ok = False
col2    = np.zeros((TARGET_H, TARGET_H, 3), dtype=np.uint8)
if OUTPUT_AVT.exists():
    try:
        raw2 = OUTPUT_AVT.read_bytes()
        zs2  = raw2.find(b"PK\x03\x04")
        with zipfile.ZipFile(io.BytesIO(raw2[zs2:]), "r") as zf2:
            out_tex = cv2.imdecode(
                np.frombuffer(zf2.read("MV2_Jinho_01_face.jpg"), np.uint8),
                cv2.IMREAD_COLOR,
            )
        col2    = _resize_h(out_tex, TARGET_H)
        col2_ok = True
        print(f"  Col2 (output face tex): OK  ({out_tex.shape[1]}x{out_tex.shape[0]})")
    except Exception as e:
        print(f"  Col2 error: {e}")
else:
    print("  Col2: output AVT not found — showing blank")

# Col 3: 50% blend of col1 face photo region and col2 face texture
# Both resized to same width before blending
target_w = max(col1.shape[1], col2.shape[1], TARGET_H)
c1r = cv2.resize(col1, (target_w, TARGET_H))
c2r = cv2.resize(col2, (target_w, TARGET_H))
col3 = cv2.addWeighted(c1r, 0.5, c2r, 0.5, 0)

# Add column labels
def _label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 36), (20, 20, 20), -1)
    cv2.putText(out, text, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2, cv2.LINE_AA)
    return out

c1r = _label(c1r, "Col 1 — front + landmarks")
c2r = _label(c2r, "Col 2 — output face texture")
c3r = _label(col3, "Col 3 — 50% blend")

side_by_side = np.hstack([c1r, c2r, c3r])
out_sbs = OUT_DIR / "debug_side_by_side.png"
cv2.imwrite(str(out_sbs), side_by_side)
print(f"  Saved: {out_sbs}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Final summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 5 — Final Summary")
print(SEP)

sprite_files = sorted(SPRITES_DIR.iterdir()) if SPRITES_DIR.exists() else []
beard_sprites = [f for f in sprite_files if "beard" in f.name.lower()]
hair_sprites  = [f for f in sprite_files if "hair"  in f.name.lower()]

morph_ok = result.get("morph_result", {}).get("success") if result else False

print(f"""
  Landmarks in warp:             {len(BASE_WARP)}
  Bad UV landmarks (excluded):   {list(_BAD_UV.keys())}
  Zone-checked landmarks:        {n_checked}
  Passing zone check:            {n_ok} / {n_checked} ({pct}%)
  Suspicious landmarks:          {len(suspicious)} → {suspicious if suspicious else 'none'}

  Pipeline ran successfully:     {'YES' if result and result.get('success') else 'NO'}
  morph.py ran successfully:     {'YES' if morph_ok else 'NO'}
  beard.py sprites found:        {'YES — ' + str(beard_sprites) if beard_sprites else 'NO (0 files)'}
  hair.py sprites found:         {'YES — ' + str(hair_sprites)  if hair_sprites  else 'NO (0 files)'}
  Output .avt valid:             {'YES' if avt_valid else 'NO'}

  Debug outputs:
    {out_lm}
    {out_sbs}
""")

if pipeline_error:
    print(f"  PIPELINE EXCEPTION: {pipeline_error}")

print(SEP)
