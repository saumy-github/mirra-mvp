"""
OBJ head geometry morphing from MediaPipe face measurements.

Activates the geometry pass: measures the user's face from their photos,
compares against the base avatar's measurements from its frontal render,
and displaces OBJ vertices to match the user's jaw width, cheek width,
nose shape and depth.

OBJ scale: millimetres (CLO3D default export).
  Y range ≈ 1644–1903mm (chin → forehead)
  X range ≈ ±92mm
  Z range ≈ -98 to +124mm (back → nose tip)

Usage:
  from clo_avatar_generation.face.morph import apply_morph
  result = apply_morph(
      obj_path     = Path('input/base_head.obj'),
      render_path  = Path('/tmp/face_textured_render.jpg'),
      user_photos  = {'front': front, 'left': left, 'right': right},
      output_path  = Path('/tmp/morphed_head.obj'),
  )
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import trimesh
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .detect import _ensure_model, _MODEL_PATH, FACE_OVAL_INDICES


# ── Structural anchor landmark indices ───────────────────────────────────────
_ANCHORS = {
    "jaw_left":  234, "jaw_right":  454, "chin":      152,
    "cheek_l":   116, "cheek_r":    345,
    "nose_tip":    4, "nose_base":    6,
    "brow_l":     70, "brow_r":     300,
    "mouth_l":    61, "mouth_r":    291,
}

# Ratio clamp — prevents extreme deformations
_RATIO_MIN, _RATIO_MAX = 0.75, 1.35

# Max displacement per vertex (mm) — displacements exceeding this are scaled back
_MAX_DISP_MM = 12.0

# Z-axis baseline estimates for frontal avatar render (normalized by face height)
_BASE_JAW_DEPTH   = 0.18
_BASE_CHEEK_DEPTH = 0.14
_BASE_NOSE_DEPTH  = 0.10

# OBJ section to morph (only face vertices displaced)
_FACE_MATERIAL = "face"


# ── MediaPipe helpers ─────────────────────────────────────────────────────────

def _detect_landmarks(image_path: Path) -> dict | None:
    """Run MediaPipe on an image. Returns landmarks dict or None."""
    _ensure_model()
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    h, w = img.shape[:2]
    rgb     = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(_MODEL_PATH)),
        num_faces=1, min_face_detection_confidence=0.2, min_face_presence_confidence=0.2,
    )
    with vision.FaceLandmarker.create_from_options(options) as det:
        result = det.detect(mp_img)
    if not result.face_landmarks:
        return None
    lm  = result.face_landmarks[0]
    px  = [(int(round(l.x * w)), int(round(l.y * h))) for l in lm]
    return {"landmarks_px": px, "image_size": [w, h], "detected": True}


def _dist(lm: list[tuple[int, int]], a: int, b: int) -> float:
    ax, ay = lm[a]; bx, by = lm[b]
    return float(np.sqrt((ax - bx)**2 + (ay - by)**2))


def _face_height(lm: list[tuple[int, int]]) -> float:
    """Distance from forehead (10) to chin (152) — normalization denominator."""
    return max(_dist(lm, 10, 152), 1.0)


# ── Measurement extraction ────────────────────────────────────────────────────

def _measure_front(lm: list[tuple[int, int]]) -> dict[str, float]:
    fh = _face_height(lm)
    return {
        "face_width":   _dist(lm, 234, 454) / fh,
        "jaw_width":    _dist(lm, 172, 397) / fh,
        "cheek_width":  _dist(lm, 116, 345) / fh,
        "nose_width":   _dist(lm, 129, 358) / fh,
        "nose_length":  _dist(lm,   6,   4) / fh,
        "eye_dist":     _dist(lm,  33, 263) / fh,
        "mouth_width":  _dist(lm,  61, 291) / fh,
    }


def _measure_side(lm: list[tuple[int, int]], side: str) -> dict[str, float]:
    """Extract Z-proxy depth measurements from a 45° photo."""
    fh = _face_height(lm)
    if side == "left":
        return {
            "jaw_depth":   _dist(lm, 234, 152) / fh,
            "cheek_depth": _dist(lm, 116, 234) / fh,
            "nose_depth":  _dist(lm,   1,   4) / fh,
        }
    else:  # right
        return {
            "jaw_depth":   _dist(lm, 454, 152) / fh,
            "cheek_depth": _dist(lm, 345, 454) / fh,
            "nose_depth":  _dist(lm,   1,   4) / fh,
        }


# ── OBJ parsing ───────────────────────────────────────────────────────────────

def _parse_face_vertices(obj_path: Path) -> tuple[np.ndarray, set[int]]:
    """Return all vertices and the set of vertex indices used by the face material."""
    lines = obj_path.read_text(encoding="utf-8", errors="replace").splitlines()
    all_v: list[list[float]] = []
    face_vi: set[int] = set()
    in_face = False
    for l in lines:
        p = l.split()
        if not p: continue
        if p[0] == "v":
            all_v.append([float(p[1]), float(p[2]), float(p[3])])
        elif p[0] == "usemtl":
            in_face = (p[1] == _FACE_MATERIAL)
        elif p[0] == "f" and in_face:
            for tok in p[1:]:
                face_vi.add(int(tok.split("/")[0]) - 1)
    return np.array(all_v, dtype=np.float64), face_vi


def _write_morphed_obj(obj_path: Path, output_path: Path, new_verts: np.ndarray) -> None:
    """Write a new OBJ replacing only vertex positions, keeping all other lines."""
    lines = obj_path.read_text(encoding="utf-8", errors="replace").splitlines()
    vi = 0
    out_lines = []
    for l in lines:
        p = l.split()
        if p and p[0] == "v":
            x, y, z = new_verts[vi]
            out_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vi += 1
        else:
            out_lines.append(l)
    output_path.write_text("\n".join(out_lines), encoding="utf-8")


# ── Zone-based vertex displacement ────────────────────────────────────────────

def _quadratic_weight(dist: float, radius: float) -> float:
    if dist >= radius or radius <= 0:
        return 0.0
    t = dist / radius
    return (1.0 - t) ** 2


def _apply_displacements(
    verts: np.ndarray,
    face_vi: set[int],
    ratios: dict[str, float],
) -> tuple[np.ndarray, int, float]:
    """
    Apply zone-based vertex displacement.

    Zones are defined in normalised coordinates (0–1 per axis relative to
    the face bounding box). All displacement radii are in mm.

    Returns: (displaced_verts, n_displaced, max_displacement_mm)
    """
    fv = verts[list(face_vi)]
    # Bounding box of face section
    mn, mx = fv.min(0), fv.max(0)
    span   = mx - mn
    center = (mn + mx) / 2.0

    def norm(v: np.ndarray) -> np.ndarray:
        return (v - mn) / np.where(span > 0, span, 1.0)

    displaced   = verts.copy()
    n_displaced = 0
    max_disp    = 0.0

    for vi in face_vi:
        v       = verts[vi]
        nv      = norm(v)               # 0–1 per axis relative to face bbox
        nx, ny, nz = nv[0], nv[1], nv[2]

        delta = np.zeros(3, dtype=np.float64)

        # ── JAW zone: lower 25% of face height ──────────────────────────
        if ny < 0.25:
            jaw_center   = np.array([center[0], mn[1] + span[1]*0.12, center[2]])
            d            = np.linalg.norm(v - jaw_center)
            radius_mm    = span[1] * 0.18           # ~18% of face height
            w            = _quadratic_weight(d, radius_mm)
            if w > 0:
                delta[0] += (v[0] - center[0]) * (ratios["jaw_width"]  - 1.0) * w
                delta[2] += (v[2] - center[2]) * (ratios["jaw_depth"]  - 1.0) * w

        # ── CHEEK zone: mid-face sides ────────────────────────────────────
        if 0.30 <= ny <= 0.70 and (nx < 0.30 or nx > 0.70):
            side_x = mn[0] + span[0]*(0.15 if nx < 0.30 else 0.85)
            cheek_c  = np.array([side_x, mn[1] + span[1]*0.50, center[2]])
            d        = np.linalg.norm(v - cheek_c)
            radius_mm = span[0] * 0.40
            w         = _quadratic_weight(d, radius_mm)
            if w > 0:
                delta[0] += (v[0] - center[0]) * (ratios["cheek_width"] - 1.0) * w
                delta[2] += (v[2] - center[2]) * (ratios["cheek_depth"] - 1.0) * w

        # ── NOSE zone: front-protruding area ─────────────────────────────
        if nz > 0.65 and 0.30 <= nx <= 0.70 and 0.25 <= ny <= 0.60:
            nose_c   = np.array([center[0], mn[1] + span[1]*0.42, mx[2]])
            d        = np.linalg.norm(v - nose_c)
            radius_mm = span[2] * 0.35
            w         = _quadratic_weight(d, radius_mm)
            if w > 0:
                delta[0] += (v[0] - center[0]) * (ratios["nose_width"]  - 1.0) * w
                delta[2] += (v[2] - center[2]) * (ratios["nose_depth"]  - 1.0) * w

        if np.any(delta != 0):
            disp_mm = float(np.linalg.norm(delta))
            if disp_mm > _MAX_DISP_MM:
                delta = delta * (_MAX_DISP_MM / disp_mm)
                disp_mm = _MAX_DISP_MM
            displaced[vi] = v + delta
            n_displaced += 1
            max_disp = max(max_disp, disp_mm)

    return displaced, n_displaced, max_disp


# ── Laplacian smoothing (direct OBJ topology) ─────────────────────────────────
# Trimesh reindexes/deduplicates vertices on load, so its vertex count differs
# from our OBJ vertex count and face_vi indices go out of bounds. We build the
# adjacency directly from the OBJ face lines to avoid the mismatch.

def _laplacian_smooth(obj_path: Path, displaced_verts: np.ndarray, face_vi: set[int], iterations: int = 5) -> np.ndarray:
    """Smooth displaced face vertices using OBJ face-topology adjacency."""
    try:
        # Build neighbour set for each face vertex from OBJ face lines
        adj: dict[int, set[int]] = {vi: set() for vi in face_vi}
        lines    = obj_path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_face  = False
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "usemtl":
                in_face = (parts[1] == _FACE_MATERIAL)
            elif parts[0] == "f" and in_face:
                face_verts = [int(t.split("/")[0]) - 1 for t in parts[1:]]
                for vi in face_verts:
                    if vi in adj:
                        for vj in face_verts:
                            if vj != vi:
                                adj[vi].add(vj)

        result = displaced_verts.copy()
        lamb   = 0.4
        for _ in range(iterations):
            updated = result.copy()
            for vi, nbrs in adj.items():
                if not nbrs:
                    continue
                avg = result[list(nbrs)].mean(axis=0)
                updated[vi] = result[vi] * (1.0 - lamb) + avg * lamb
            result = updated

        print(f"  [morph] Laplacian smooth OK ({iterations} iters, {len(adj)} verts)")
        return result
    except Exception as e:
        print(f"  [morph] Laplacian smooth failed ({e}), skipping")
        return displaced_verts


# ── Mesh validation ───────────────────────────────────────────────────────────

def _validate_mesh(obj_path: Path, new_verts: np.ndarray) -> dict:
    try:
        mesh = trimesh.load(str(obj_path), force="mesh", process=False)
        mesh.vertices = new_verts
        return {
            "watertight":          bool(mesh.is_watertight),
            "winding_consistent":  bool(mesh.is_winding_consistent),
            "valid":               True,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ── Public API ────────────────────────────────────────────────────────────────

def apply_morph(
    obj_path: Path,
    render_path: Path | None,
    user_photos: dict[str, Path],
    output_path: Path,
) -> dict:
    """
    Full geometry morph pipeline.

    Args:
        obj_path     : base avatar head OBJ (millimetres)
        render_path  : frontal texture render of the base avatar
                       (regenerated from OBJ if None or missing)
        user_photos  : {'front': Path, 'left': Path, 'right': Path}
        output_path  : destination for morphed OBJ

    Returns calibration + validation report dict.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Step 1: base avatar landmarks from render ─────────────────────────
    if render_path is None or not render_path.exists():
        print("  [morph] Render not found — regenerating from OBJ...")
        render_path = _regenerate_render(obj_path)

    base_data = _detect_landmarks(render_path)
    if base_data is None:
        return {"success": False, "reason": "MediaPipe could not detect face on base avatar render"}

    base_lm = base_data["landmarks_px"]
    base_m  = _measure_front(base_lm)

    # ── Step 2: user face measurements ───────────────────────────────────
    front_data = _detect_landmarks(user_photos["front"])
    if front_data is None:
        return {"success": False, "reason": "No face detected in front photo"}

    front_lm = front_data["landmarks_px"]
    user_m   = _measure_front(front_lm)

    # Z-depth from side photos
    left_depth  = {"jaw_depth": _BASE_JAW_DEPTH, "cheek_depth": _BASE_CHEEK_DEPTH, "nose_depth": _BASE_NOSE_DEPTH}
    right_depth = {"jaw_depth": _BASE_JAW_DEPTH, "cheek_depth": _BASE_CHEEK_DEPTH, "nose_depth": _BASE_NOSE_DEPTH}

    if "left" in user_photos and user_photos["left"] is not None:
        ld = _detect_landmarks(user_photos["left"])
        if ld: left_depth = _measure_side(ld["landmarks_px"], "left")

    if "right" in user_photos and user_photos["right"] is not None:
        rd = _detect_landmarks(user_photos["right"])
        if rd: right_depth = _measure_side(rd["landmarks_px"], "right")

    avg_jaw_depth   = (left_depth["jaw_depth"]   + right_depth["jaw_depth"])   / 2
    avg_cheek_depth = (left_depth["cheek_depth"] + right_depth["cheek_depth"]) / 2
    avg_nose_depth  = (left_depth["nose_depth"]  + right_depth["nose_depth"])  / 2

    # ── Step 3+4: displacement ratios (clamped) ───────────────────────────
    def ratio(user_val: float, base_val: float) -> float:
        r = user_val / max(base_val, 1e-6)
        return float(np.clip(r, _RATIO_MIN, _RATIO_MAX))

    ratios = {
        "face_width":   ratio(user_m["face_width"],   base_m["face_width"]),
        "jaw_width":    ratio(user_m["jaw_width"],     base_m["jaw_width"]),
        "cheek_width":  ratio(user_m["cheek_width"],   base_m["cheek_width"]),
        "nose_width":   ratio(user_m["nose_width"],    base_m["nose_width"]),
        "jaw_depth":    ratio(avg_jaw_depth,   _BASE_JAW_DEPTH),
        "cheek_depth":  ratio(avg_cheek_depth, _BASE_CHEEK_DEPTH),
        "nose_depth":   ratio(avg_nose_depth,  _BASE_NOSE_DEPTH),
    }

    # ── Step 5: apply vertex displacements ───────────────────────────────
    verts, face_vi = _parse_face_vertices(obj_path)
    n_total        = len(verts)
    displaced, n_disp, max_disp = _apply_displacements(verts, face_vi, ratios)

    # ── Step 6: smooth + validate ─────────────────────────────────────────
    smoothed = _laplacian_smooth(obj_path, displaced, face_vi, iterations=5)
    mesh_check = _validate_mesh(obj_path, smoothed)

    # ── Step 7: save morphed OBJ ──────────────────────────────────────────
    _write_morphed_obj(obj_path, output_path, smoothed)

    # ── Step 8: calibration report ───────────────────────────────────────
    report = {
        "success": True,
        "input_obj":  str(obj_path),
        "output_obj": str(output_path),
        "base_measurements":  {k: round(v, 4) for k, v in base_m.items()},
        "user_measurements":  {k: round(v, 4) for k, v in user_m.items()},
        "ratios_applied":     {k: round(v, 4) for k, v in ratios.items()},
        "vertices_total":     n_total,
        "vertices_displaced": n_disp,
        "max_displacement_mm": round(max_disp, 2),
        "mesh_validation":    mesh_check,
    }

    _print_report(report)
    return report


def _print_report(r: dict) -> None:
    bm, um, ra = r["base_measurements"], r["user_measurements"], r["ratios_applied"]
    print("\n── Morph Calibration Report ────────────────────────────────")
    print(f"  {'Measurement':<16s}  {'Base':>8s}  {'User':>8s}  {'Ratio':>8s}")
    print(f"  {'-'*50}")
    for key in ["face_width", "jaw_width", "cheek_width", "nose_width"]:
        b = bm.get(key, 0); u = um.get(key, 0); rv = ra.get(key, 1)
        flag = " ←" if abs(rv - 1.0) > 0.15 else ""
        print(f"  {key:<16s}  {b:8.4f}  {u:8.4f}  {rv:8.4f}{flag}")
    print(f"  {'jaw_depth':<16s}  {'~0.180':>8s}  {'(45°)':>8s}  {ra.get('jaw_depth',1):8.4f}")
    print(f"  {'cheek_depth':<16s}  {'~0.140':>8s}  {'(45°)':>8s}  {ra.get('cheek_depth',1):8.4f}")
    print(f"  {'nose_depth':<16s}  {'~0.100':>8s}  {'(45°)':>8s}  {ra.get('nose_depth',1):8.4f}")
    print(f"\n  Vertices displaced: {r['vertices_displaced']:,} / {r['vertices_total']:,}")
    print(f"  Max displacement  : {r['max_displacement_mm']:.1f}mm", end="")
    if r['max_displacement_mm'] >= _MAX_DISP_MM:
        print("  ⚠ hit cap")
    else:
        print()
    mv = r["mesh_validation"]
    print(f"  Mesh valid        : {mv.get('valid')}  watertight={mv.get('watertight')}  winding={mv.get('winding_consistent')}")
    print(f"  Output OBJ        : {r['output_obj']}")


def _regenerate_render(obj_path: Path) -> Path:
    """Regenerate the frontal textured render if /tmp/face_textured_render.jpg is missing."""
    import io as _io
    out = Path("/tmp/face_textured_render.jpg")
    avt = obj_path.parents[1] / "input" / "base-1.avt"
    if not avt.exists():
        return out

    raw = avt.read_bytes()
    zs  = raw.find(b"PK\x03\x04")
    with zipfile.ZipFile(_io.BytesIO(raw[zs:]), "r") as z:
        face_tex = cv2.imdecode(np.frombuffer(z.read("MV2_Jinho_01_face.jpg"), np.uint8), cv2.IMREAD_COLOR)
        eye_tex  = cv2.imdecode(np.frombuffer(z.read("MV2_Jinho_01_eye.jpg"),  np.uint8), cv2.IMREAD_COLOR)

    lines = obj_path.read_text(encoding="utf-8", errors="replace").splitlines()
    all_v, all_uv = [], []
    for l in lines:
        p = l.split()
        if not p: continue
        if p[0] == "v":  all_v.append([float(p[1]), float(p[2]), float(p[3])])
        elif p[0] == "vt": all_uv.append([float(p[1]), float(p[2])])
    verts = np.array(all_v, dtype=np.float32)
    uvs   = np.array(all_uv, dtype=np.float32)

    def parse_sec(mat):
        vi_l, ti_l = [], []
        active = False
        for l in lines:
            p = l.split()
            if not p: continue
            if p[0] == "usemtl": active = (p[1] == mat)
            elif p[0] == "f" and active:
                for tok in p[1:]:
                    sub = tok.split("/")
                    vi_l.append(int(sub[0]) - 1)
                    ti_l.append(int(sub[1]) - 1)
        n = (len(vi_l)//3)*3
        return (np.array(vi_l[:n]).reshape(-1,3), np.array(ti_l[:n]).reshape(-1,3)) if vi_l else (None, None)

    f_vi, f_ti = parse_sec("face")
    e_vi, e_ti = parse_sec("eye")

    ufi = np.unique(f_vi) if f_vi is not None else np.array([])
    fv  = verts[ufi] if len(ufi) else verts
    x_mn, x_mx = fv[:,0].min(), fv[:,0].max()
    y_mn, y_mx = fv[:,1].min(), fv[:,1].max()
    RSIZE, pad = 1024, 0.1

    # Aspect-correct projection: scale both axes by the same factor so the
    # rendered face has the correct width/height ratio. Without this, a face
    # that is 184mm wide × 259mm tall would render as a square (both axes
    # independently scaled to RSIZE), inflating face_width from ~0.71 to ~1.04
    # and pushing every morph ratio to the 0.75 lower clamp.
    x_range   = x_mx - x_mn
    y_range   = y_mx - y_mn
    max_range = max(x_range, y_range)
    effective = RSIZE * (1.0 - 2.0 * pad)
    scale     = effective / max_range
    x_off     = RSIZE * pad + (max_range - x_range) * scale / 2.0
    y_off     = RSIZE * pad + (max_range - y_range) * scale / 2.0

    def proj(v):
        px = int(scale * (v[0] - x_mn) + x_off)
        py = int(scale * (y_mx - v[1]) + y_off)
        return max(0, min(RSIZE - 1, px)), max(0, min(RSIZE - 1, py))

    render = np.ones((RSIZE,RSIZE,3),dtype=np.uint8)*180
    z_buf  = np.full((RSIZE,RSIZE),-np.inf)

    def render_mesh(tri_v, tri_t, tex):
        if tri_v is None: return
        th, tw = tex.shape[:2]
        for tv, tt in zip(tri_v, tri_t):
            dst = np.array([proj(verts[vi]) for vi in tv], dtype=np.float32)
            src = np.array([[uvs[ti][0]*tw,(1-uvs[ti][1])*th] for ti in tt], dtype=np.float32)
            v1  = dst[1]-dst[0]; v2 = dst[2]-dst[0]
            if (v1[0]*v2[1]-v1[1]*v2[0]) < 0: continue
            M = cv2.getAffineTransform(src, dst)
            w = cv2.warpAffine(tex, M, (RSIZE,RSIZE))
            msk = np.zeros((RSIZE,RSIZE),dtype=np.uint8)
            cv2.fillConvexPoly(msk, dst.astype(np.int32), 255)
            zv = verts[tv,2].mean()
            upd = (msk>0) & (zv>=z_buf)
            render[upd] = w[upd]; z_buf[upd] = zv

    render_mesh(f_vi, f_ti, face_tex)
    render_mesh(e_vi, e_ti, eye_tex)
    cv2.imwrite(str(out), render)
    return out
