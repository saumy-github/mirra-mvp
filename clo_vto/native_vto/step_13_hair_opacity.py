"""Step 13: give the avatar's hair its opacity back in the simulation GLB.

CLO exports hair materials as ``alphaMode = BLEND`` with **three-channel JPEG** base
colour textures. glTF reads opacity from the base colour's fourth channel, so BLEND over a
texture with no alpha channel is fully opaque: every strand card renders as a solid
rectangle and the shopper sees a helmet rather than hair. Measured 2026-11-10, see
``.agent/clo-avatar-vto/master-plan-26_11_10.md`` Part 3.

The missing channel is already in the avatar's ``.avt`` - ``hair_main_alpha.jpg`` and
``hair_cap_alpha.jpg``, the same maps CLO itself honours on import. This step composes
them into the exported textures' alpha channel. No Blender, no DCC round trip; the data
was there all along and only the channel layout was wrong.

Design decisions, inherited from step_12 deliberately
-----------------------------------------------------
* **Never blocks.** Every failure path returns True. A shopper losing their hairstyle is a
  cosmetic regression; a shopper losing their try-on is not. This runs after simulation, so
  the cloth solver, collision and the seam system never see it.
* **Materials, not images.** Hair textures are found by walking the hair *materials* to
  their base colour. Guessing from image size would let a hair normal map of the same
  dimensions be mistaken for an albedo, which produces a file that loads fine and looks
  wrong.
* **Content matching.** CLO exports every image unnamed, so which albedo is ``hair_main``
  and which is ``hair_cap`` is decided by comparing what they look like.
* **Downscaled by default.** PNG is the only alpha-capable format every glTF viewer reads,
  and it is lossless, so the textures grow. Hair is already the largest thing in the
  export; 1024 square costs nothing visible and keeps the file near its original size.
"""

from __future__ import annotations

import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

# Hair textures are soft and alpha-dominated; 1024 is indistinguishable from 2048 in a
# try-on render and keeps the GLB close to the size it was before this step.
HAIR_TEXTURE_SIZE = 1024

OUTPUT_NAME = "simulation_hair.glb"


def _source_glb(ctx) -> Path | None:
    """The newest GLB in the chain: step_12's textured output, else step_11's raw export."""
    for attribute in ("textured_glb_path", "glb_path"):
        value = getattr(ctx, attribute, None)
        if value and Path(value).exists():
            return Path(value)
    return None


def run(ctx) -> bool:
    if getattr(ctx, "skip_glb_postprocess", False):
        print("  [SKIP] GLB post-processing disabled (skip_glb_postprocess=True).")
        return True

    source = _source_glb(ctx)
    if source is None:
        print("  [SKIP] No GLB available (step 11/12 produced none).")
        return True

    avatar_path = Path(getattr(ctx, "avatar_path", "") or "")
    if avatar_path.suffix.lower() != ".avt":
        print(f"  [SKIP] Avatar is not a .avt ({avatar_path.name or 'unset'}); "
              "the hair alpha maps live in the container.")
        return True
    if not avatar_path.exists():
        print(f"  [SKIP] Avatar file not found: {avatar_path}")
        return True

    try:
        from face_fitting.export_glb import patch_hair_alpha
    except ImportError as exc:
        print(f"  [SKIP] Hair opacity unavailable ({exc}).")
        return True

    out_path = Path(ctx.output_dir) / OUTPUT_NAME
    try:
        report = patch_hair_alpha(source, avatar_path, out_path,
                                  lambda message: print(f"  {message}"),
                                  hair_texture_size=HAIR_TEXTURE_SIZE)
    except Exception as exc:  # noqa: BLE001 - cosmetic step, never blocks a try-on
        print(f"  [WARN] Hair opacity pass failed ({exc}); shipping the GLB without it.")
        return True

    for warning in report.warnings:
        print(f"  [WARN] {warning}")

    if report.glb is None or not out_path.exists():
        print("  [WARN] Hair opacity produced no file; shipping the previous GLB.")
        return True
    if not report.images_patched:
        print("  [SKIP] No hair textures matched; shipping the previous GLB unchanged.")
        return True

    # Only now does this become the shipped file. If anything above fell through, the
    # worker keeps using step_12's output and the shopper still gets their try-on.
    ctx.final_glb_path = out_path
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"  Hair opacity composed into {len(report.images_patched)} texture(s) "
          f"-> {out_path.name} ({size_mb:.1f} MB)")
    return True
