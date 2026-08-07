"""Top-level face personalization pipeline: photos + .avt → personalized .avt."""

from __future__ import annotations

import json
from pathlib import Path

import cv2

from .avt_face import extract_base_texture, patch
from .beard import composite_beard
from .detect import detect
from .grade import apply_color_grade
from .hair import build_personalized_hair
from .morph import apply_morph
from .project import project_face

_OBJ_PATH    = Path(__file__).parents[1] / "input" / "base_head.obj"
_RENDER_PATH = Path("/tmp/face_textured_render.jpg")


def run(
    front_photo: Path,
    source_avt: Path,
    output_avt: Path,
    left_photo: Path | None = None,
    right_photo: Path | None = None,
    avatar_name: str = "base-1",
) -> dict:
    """
    Full face personalization pipeline — 1, 2 or 3 photos.

    Photo conventions:
        front_photo : user facing camera straight on
        left_photo  : user turned ~45° to THEIR left (camera sees right cheek)
        right_photo : user turned ~45° to THEIR right (camera sees left cheek)

    Pipeline:
        1. detect      — MediaPipe 478 landmarks for each available photo
        2. project     — homography-warp actual photo pixels → CLO UV atlas
        3. beard       — jaw-contour beard sprite composite (MediaPipe)
        4. grade       — sat +15%, hue +5°, brightness −8%, bilateral filter
        5. hair_tex    — colorize avatar hair_main.jpg (MediaPipe)
        6. morph       — geometry morph via MediaPipe-driven mesh deformation
        7. patch       — swap face.jpg + hair_main.jpg inside .avt zip

    Args:
        front_photo : required — front-facing photo
        source_avt  : body-morphed avatar from step 11
        output_avt  : destination for personalized avatar
        left_photo  : optional — user looking 45° left
        right_photo : optional — user looking 45° right
        avatar_name : drives UV template lookup (default: base-1)

    Returns dict with success, output paths, and per-step metadata.
    """
    output_avt.parent.mkdir(parents=True, exist_ok=True)
    run_dir = output_avt.parent

    front_photo = Path(front_photo)

    # ── 1. Detect landmarks for each available photo ───────────────────────
    front_img = cv2.imread(str(front_photo))
    left_img  = cv2.imread(str(left_photo))  if left_photo  else None
    right_img = cv2.imread(str(right_photo)) if right_photo else None

    front_lm = detect(front_photo)
    left_lm  = detect(left_photo)  if left_photo  else None
    right_lm = detect(right_photo) if right_photo else None
    n_photos = sum(1 for p in (front_photo, left_photo, right_photo) if p is not None)

    # ── 2. Project actual photo pixels into the CLO UV atlas ───────────────
    uv_template_path = Path(__file__).parent / "templates" / f"{avatar_name}-face-uv.json"
    uv_data    = json.loads(uv_template_path.read_text(encoding="utf-8"))
    uv_all_px  = uv_data["all_478_landmark_pixels"]
    uv_oval_px = uv_data["face_oval_pixels"]

    clo_atlas = extract_base_texture(source_avt)
    proj = project_face(
        front_photo=front_img,
        front_landmarks=front_lm,
        clo_atlas=clo_atlas,
        clo_uv_map=uv_data,
        left_photo=left_img,
        left_landmarks=left_lm,
        right_photo=right_img,
        right_landmarks=right_lm,
        output_dir=str(run_dir / "face_project"),
    )
    if not proj["success"]:
        return {
            "success": False,
            "reason": f"Face projection failed: {proj.get('error')}",
            "stage": proj.get("stage"),
        }

    blended   = proj["atlas"]
    face_mask = proj["face_mask"]

    # ── 3. Beard + grade (MediaPipe for jaw region only) ───────────────────
    blended = composite_beard(
        blended_uv=blended,
        photo_path=front_photo,
        landmarks=front_lm,
        uv_all_px=uv_all_px,
        uv_oval_px=uv_oval_px,
    )
    blended = apply_color_grade(blended, face_mask)

    # ── 4. Hair texture colorization ───────────────────────────────────────
    hair_texture = build_personalized_hair(
        photo_path=front_photo,
        landmarks=front_lm,
        source_avt=source_avt,
    )

    # ── 5. Geometry morph (if base OBJ available) ─────────────────────────
    morph_result: dict = {"success": False, "reason": "base_head.obj not found"}
    morphed_obj: Path | None = None
    if _OBJ_PATH.exists():
        morphed_obj = run_dir / "morphed_head.obj"
        morph_result = apply_morph(
            obj_path    = _OBJ_PATH,
            render_path = _RENDER_PATH,
            user_photos = {
                "front": front_photo,
                "left":  left_photo,
                "right": right_photo,
            },
            output_path = morphed_obj,
        )
        if not morph_result.get("success"):
            morph_result["morphed_obj"] = None
            morphed_obj = None

    # ── 6. Patch .avt ─────────────────────────────────────────────────────
    patch_result = patch(source_avt, blended, output_avt, hair_texture=hair_texture)

    return {
        "success": True,
        "morph_result": morph_result,
        "morphed_obj": str(morphed_obj) if morphed_obj else None,
        "photos_used": n_photos,
        "front_photo": str(front_photo),
        "left_photo": str(left_photo) if left_photo else None,
        "right_photo": str(right_photo) if right_photo else None,
        "source_avt": str(source_avt),
        "output_avt": str(output_avt),
        "control_points": proj.get("control_points"),
        "inliers": proj.get("inliers"),
        "reprojection_error_mean": proj.get("reprojection_error_mean"),
        "l_drift": proj.get("l_drift"),
        "hair_colorized": hair_texture is not None,
        "patch_result": patch_result,
    }
