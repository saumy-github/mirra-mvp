"""Step 12: apply face personalization to the saved avatar (optional)."""

from __future__ import annotations

from .context import Step1Context
from ..face.run_face import run as run_face


def run(ctx: Step1Context) -> bool:
    if ctx.face_photo_path is None:
        ctx.warnings.append("step_12_apply_face: no face photo provided — skipped")
        return True

    if ctx.extracted_avatar_path is None:
        ctx.warnings.append("step_12_apply_face: no saved avatar to patch — skipped")
        return True

    run_dir    = ctx.require_run_dir()
    output_avt = run_dir / "result_avatar_face.avt"

    result = run_face(
        front_photo=ctx.face_photo_path,
        source_avt=ctx.extracted_avatar_path,
        output_avt=output_avt,
        left_photo=ctx.face_left_photo_path,
        right_photo=ctx.face_right_photo_path,
    )

    ctx.write_json("face_result.json", result)

    if result["success"]:
        ctx.face_avt_path = output_avt
        ctx.extracted_avatar_path = output_avt
        n = result.get("photos_used", 1)
        ctx.warnings.append(f"step_12_apply_face: completed ({n} photo{'s' if n>1 else ''})")
    else:
        ctx.warnings.append(f"step_12_apply_face: {result.get('reason', 'failed')}")

    return result["success"]
