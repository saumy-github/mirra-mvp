"""
Face pipeline diagnostics — run after pipeline to validate alignment.

Generates 4 diagnostic outputs:
  /tmp/debug_uv_landmarks.png   — landmark overlay + Delaunay mesh on UV texture
  /tmp/debug_warp_heatmap.png   — per-landmark alignment error heatmap
  /tmp/debug_side_by_side.png   — front photo | output texture | 50% blend
  (stdout)                      — per-region accuracy report + summary

Usage:
  python -m clo_avatar_generation.face.diagnose
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from scipy.spatial import Delaunay

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO   = Path(__file__).parents[2]
_FACE   = Path(__file__).parent
_MODELS = _FACE / "models" / "face_landmarker.task"
_TPL    = _FACE / "templates" / "base-1-face-uv.json"
_FRONT  = _REPO / "clo_avatar_generation" / "input" / "face" / "u_001" / "front.jpg"
_BASE   = _REPO / "clo_avatar_generation" / "input" / "base-1.avt"
_OUT    = _REPO / "clo_avatar_generation" / "output" / "face_test.avt"

# ── Landmark colour groups ─────────────────────────────────────────────────────
_OVAL   = [10,338,297,332,284,251,389,356,454,323,361,288,
           397,365,379,378,400,377,152,148,176,149,150,136,
           172,58,132,93,234,127,162,21,54,103,67,109]
_NOSE   = [4,6,168,1,5,129,358]
_MOUTH  = [61,291,0,17,13,14]
_EYE    = [33,133,145,362,263,374]
_BROW   = [70,107,300,336]
_REJECT = [159,386]

# Region groups for accuracy report
_REGIONS: dict[str, list[int]] = {
    "Forehead" : [10, 338, 297, 332, 284],
    "Eye-L"    : [33, 133, 145, 70, 107],
    "Eye-R"    : [362, 263, 374, 300, 336],
    "Nose"     : [1, 4, 5, 6, 129, 358],
    "Mouth"    : [61, 291, 13, 14, 17],
    "Jaw"      : [234, 454, 152, 172, 397],
}

# All indices in the warp (must match warp.py)
_WARP_BASE = [
    10,338,297,332,284,251,389,356,454,323,361,288,
    397,365,379,378,400,377,152,148,176,149,150,136,
    172,58,132,93,234,127,162,21,54,103,67,109,
    70,107,300,336,
    33,133,145,362,263,374,
    4,6,168,
    61,291,0,17,
    152,116,345,
]
seen: set[int] = set()
_WARP_INDICES = [i for i in _WARP_BASE if not (i in seen or seen.add(i))]
del seen


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_tex(avt: Path, name: str) -> np.ndarray:
    raw = avt.read_bytes()
    zs  = raw.find(b"PK\x03\x04")
    with zipfile.ZipFile(io.BytesIO(raw[zs:]), "r") as z:
        return cv2.imdecode(np.frombuffer(z.read(name), np.uint8), cv2.IMREAD_COLOR)


def _detect(img: np.ndarray) -> list[tuple[int, int]] | None:
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    opts = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(_MODELS)),
        num_faces=1, min_face_detection_confidence=0.2, min_face_presence_confidence=0.2,
    )
    with vision.FaceLandmarker.create_from_options(opts) as det:
        res = det.detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = img.shape[:2]
    return [(int(l.x * w), int(l.y * h)) for l in res.face_landmarks[0]]


def _draw_dot(img, pt, color, r=10):
    cv2.circle(img, pt, r, color, -1)
    cv2.circle(img, pt, r, (0,0,0), 1)


# ── Diagnostic 1 — Landmark overlay + Delaunay mesh ──────────────────────────

def diag1_uv_landmarks(uv_all_px, uv_w, uv_h, base_tex):
    canvas = base_tex.copy()

    # Draw Delaunay mesh in white at low opacity
    valid_warp = [i for i in _WARP_INDICES if i not in _REJECT]
    pts = np.array([uv_all_px[i] for i in valid_warp], dtype=np.float32)
    tri = Delaunay(pts)
    overlay = canvas.copy()
    for simplex in tri.simplices:
        verts = pts[simplex].astype(np.int32)
        cv2.polylines(overlay, [verts], isClosed=True, color=(255,255,255), thickness=1)
    canvas = cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0)

    # Colour groups
    groups = [
        (_OVAL,   (255,  80,  80), "oval"),    # blue-ish
        (_NOSE,   ( 60, 200,  60), "nose"),    # green
        (_MOUTH,  ( 60, 200,  60), "mouth"),   # green
        (_EYE,    ( 30, 220, 220), "eye"),     # yellow
        (_BROW,   ( 30, 140, 240), "brow"),    # orange
        (_REJECT, (  0,   0, 255), "reject"),  # red
    ]
    for idxs, color, _ in groups:
        for idx in idxs:
            if idx >= len(uv_all_px): continue
            pt = tuple(uv_all_px[idx])
            _draw_dot(canvas, pt, color, r=12)
            cv2.putText(canvas, str(idx), (pt[0]+6, pt[1]-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)

    # Legend
    legend = [
        ((255, 80,  80), "Oval anchors"),
        (( 60,200,  60), "Nose/Mouth"),
        (( 30,220, 220), "Eye landmarks (new)"),
        (( 30,140, 240), "Brow landmarks (new)"),
        ((  0,  0, 255), "Rejected (out of bounds)"),
    ]
    for i, (col, label) in enumerate(legend):
        y = 50 + i * 35
        cv2.circle(canvas, (30, y), 10, col, -1)
        cv2.putText(canvas, label, (50, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

    cv2.imwrite("/tmp/debug_uv_landmarks.png", canvas)
    print("Diag 1 saved → /tmp/debug_uv_landmarks.png")


# ── Diagnostic 2 — Warp accuracy heatmap ─────────────────────────────────────

def diag2_warp_heatmap(uv_all_px, uv_w, uv_h, base_tex, output_lm):
    if output_lm is None:
        print("Diag 2 SKIPPED — MediaPipe could not detect face on output texture")
        return None

    errors: dict[int, float] = {}
    for idx in _WARP_INDICES:
        if idx >= len(uv_all_px) or idx >= len(output_lm): continue
        tpl = np.array(uv_all_px[idx], dtype=np.float32)
        out = np.array(output_lm[idx], dtype=np.float32)
        errors[idx] = float(np.linalg.norm(out - tpl))

    canvas = base_tex.copy()
    for idx, err in errors.items():
        pt  = tuple(uv_all_px[idx])
        if   err <  5: color = (  0, 200,   0)   # green
        elif err < 15: color = (  0, 200, 220)   # yellow
        else:          color = (  0,   0, 255)   # red
        _draw_dot(canvas, pt, color, r=10)
        cv2.putText(canvas, f"{err:.0f}", (pt[0]+6, pt[1]-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)

    # Legend
    for i, (col, label) in enumerate([
        ((0,200,0),   "< 5px good"),
        ((0,200,220), "5-15px ok"),
        ((0,0,255),   "> 15px fix"),
    ]):
        y = 50 + i*35
        cv2.circle(canvas, (30,y), 10, col, -1)
        cv2.putText(canvas, label, (50,y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

    cv2.imwrite("/tmp/debug_warp_heatmap.png", canvas)
    print("Diag 2 saved → /tmp/debug_warp_heatmap.png")

    # Top 5 worst
    sorted_err = sorted(errors.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 5 worst-aligned landmarks:")
    for idx, err in sorted_err[:5]:
        print(f"  idx {idx:3d}  {err:6.1f}px")

    return errors


# ── Diagnostic 3 — Side by side ───────────────────────────────────────────────

def diag3_side_by_side(front_img, output_tex, front_lm, uv_all_px):
    SIZE = 512

    # Col 1: front photo + dots
    col1 = cv2.resize(front_img.copy(), (SIZE, SIZE))
    if front_lm:
        h0, w0 = front_img.shape[:2]
        sx, sy = SIZE/w0, SIZE/h0
        for idxs, color in [(_OVAL,(255,80,80)),(_EYE,(30,220,220)),
                             (_BROW,(30,140,240)),(_NOSE,(60,200,60)),(_MOUTH,(60,200,60))]:
            for idx in idxs:
                if idx >= len(front_lm): continue
                x = int(front_lm[idx][0]*sx); y = int(front_lm[idx][1]*sy)
                cv2.circle(col1, (x,y), 5, color, -1)

    # Col 2: output face texture
    col2 = cv2.resize(output_tex, (SIZE, SIZE))

    # Col 3: 50% blend overlay
    col3 = cv2.addWeighted(col1, 0.5, col2, 0.5, 0)

    out = np.hstack([col1, col2, col3])
    labels = ["Front photo + landmarks", "Output UV texture", "50% blend (alignment check)"]
    for i, label in enumerate(labels):
        cv2.putText(out, label, (i*SIZE + 10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    cv2.imwrite("/tmp/debug_side_by_side.png", out)
    print("Diag 3 saved → /tmp/debug_side_by_side.png")


# ── Diagnostic 4 — Region accuracy report ────────────────────────────────────

def diag4_region_report(errors: dict[int, float] | None):
    if errors is None:
        print("Diag 4 SKIPPED — no error data")
        return

    print("\n── Region Accuracy Report ──────────────────────────────")
    worst_region = ("", 0.0)
    for region, idxs in _REGIONS.items():
        vals = [errors[i] for i in idxs if i in errors]
        if not vals:
            print(f"  {region:<12s}  no data")
            continue
        avg = np.mean(vals)
        flag = " ⚠ NEEDS ATTENTION" if avg > 15 else ""
        print(f"  {region:<12s}  {avg:6.1f}px avg  (n={len(vals)}){flag}")
        if avg > worst_region[1]:
            worst_region = (region, avg)

    all_errs = list(errors.values())
    n   = len(all_errs)
    n_g = sum(1 for e in all_errs if e <  5)
    n_y = sum(1 for e in all_errs if  5 <= e < 15)
    n_r = sum(1 for e in all_errs if e >= 15)
    match_pct = max(0, 100 - np.mean(all_errs) * 2)

    print(f"\n── Summary ─────────────────────────────────────────────")
    print(f"  Total landmarks in warp : {n}")
    print(f"  < 5px  (good)           : {n_g:3d}  ({n_g/n*100:.0f}%)")
    print(f"  5-15px (acceptable)     : {n_y:3d}  ({n_y/n*100:.0f}%)")
    print(f"  > 15px (needs fix)      : {n_r:3d}  ({n_r/n*100:.0f}%)")
    print(f"  Worst region            : {worst_region[0]} ({worst_region[1]:.1f}px)")
    print(f"  Estimated face match %%  : {match_pct:.0f}%%")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_diagnostics():
    print("Loading UV template and textures...")
    uv       = json.loads(_TPL.read_text(encoding="utf-8"))
    uv_w, uv_h = uv["texture_size"]
    uv_all_px  = uv["all_478_landmark_pixels"]

    base_tex   = _read_tex(_BASE, "MV2_Jinho_01_face.jpg")
    front_img  = cv2.imread(str(_FRONT))

    output_tex = None
    if _OUT.exists():
        output_tex = _read_tex(_OUT, "MV2_Jinho_01_face.jpg")
    else:
        print(f"WARNING: {_OUT} not found — run the pipeline first")

    # Detect landmarks on front photo
    print("Detecting landmarks on front photo...")
    front_lm = _detect(front_img) if front_img is not None else None

    # Detect landmarks on output texture (for accuracy measurement)
    output_lm = None
    if output_tex is not None:
        print("Detecting landmarks on output texture...")
        output_lm = _detect(output_tex)
        if output_lm is None:
            print("  NOTE: MediaPipe could not detect face on output texture (will skip Diag 2+4)")

    print("\n── Running diagnostics ─────────────────────────────────")

    diag1_uv_landmarks(uv_all_px, uv_w, uv_h, base_tex)

    errors = diag2_warp_heatmap(uv_all_px, uv_w, uv_h, base_tex, output_lm)

    if output_tex is not None:
        diag3_side_by_side(front_img, output_tex, front_lm, uv_all_px)

    diag4_region_report(errors)

    print("\nDone. Open:")
    print("  /tmp/debug_uv_landmarks.png")
    print("  /tmp/debug_warp_heatmap.png")
    print("  /tmp/debug_side_by_side.png")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(_REPO))
    run_diagnostics()
