"""Step 8: Assign fabric, color, and texture to each pattern piece.

Application order per piece:
  a. set_fabric(index, fabric_index=0)         — assigns base fabric preset
  b. set_fabric_color(index, r, g, b)          — overrides diffuse color from colors.json
  c. set_fabric_texture(index, texture_path)   — applies per-panel texture atlas (if present)
  d. set_fabric_graphic(front_panel only, ...) — overlays logo/print (if design present)

Color and texture are gracefully skipped when the artifact files are absent so
the pipeline still runs even without a full product-ingestion output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .helpers import print_result


# Pattern names in the order they appear in the pipeline.
_PIECES = ["front_panel", "back_panel", "sleeve_left", "sleeve_right"]


def _load_base_color(colors_json: Path) -> Optional[tuple[int, int, int]]:
    """Return (r, g, b) from colors.json, or None.

    Tries keys in this order:
      1. base_colour_hex / base_color_hex  (hex string, product_ingestion format)
      2. palette[0].rgb                    (direct RGB list)
      3. base_color.rgb                    (legacy format)
    """
    if not colors_json.exists():
        return None
    try:
        data = json.loads(colors_json.read_text(encoding="utf-8"))

        # 1. Hex string (primary format from colour_extraction.py)
        hex_val = data.get("base_colour_hex") or data.get("base_color_hex")
        if hex_val:
            h = str(hex_val).lstrip("#")
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

        # 2. palette[0].rgb
        palette = data.get("palette", [])
        if palette:
            rgb = palette[0].get("rgb")
            if rgb and len(rgb) >= 3:
                return (int(rgb[0]), int(rgb[1]), int(rgb[2]))

        # 3. Legacy base_color.rgb
        rgb = data.get("base_color", {}).get("rgb")
        if rgb and len(rgb) >= 3:
            return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception:
        pass
    return None


def _load_design_type(colors_json: Path) -> str:
    """Return design_type from extraction_metadata.json (logo/text/pattern/'')."""
    meta_path = colors_json.parent / "extraction_metadata.json"
    if not meta_path.exists():
        return ""
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return str(data.get("design_type", ""))
    except Exception:
        return ""


def _drain(client, label: str, timeout: int = 15) -> bool:
    """Wait for the CLO queue to drain.  Logs a clear message on timeout/error and
    returns False so the caller can decide whether to abort or continue."""
    try:
        client.wait_for_queue(timeout=timeout)
        return True
    except TimeoutError as exc:
        # Pull the last known queue status out of the exception message for context.
        print(f"  [WARN] Queue drain timed out after {timeout}s at '{label}'")
        print(f"         Last status: {exc}")
        print(f"         CLO may still be processing — continuing pipeline anyway.")
        return False
    except Exception as exc:
        print(f"  [WARN] Unexpected error waiting for queue at '{label}': {exc}")
        print(f"         Continuing pipeline anyway.")
        return False


def run(ctx):
    print("\n[8] Applying fabric, color, and texture ...")

    # --- Resolve piece → CLO index mapping ---
    if ctx.piece_to_index:
        piece_indices = {
            p: ctx.piece_to_index[p]
            for p in _PIECES
            if p in ctx.piece_to_index
        }
    else:
        piece_indices = {p: i for i, p in enumerate(_PIECES)}

    # --- Step a: Assign base fabric preset to all pieces ---
    for piece, idx in piece_indices.items():
        print_result(ctx.client.set_fabric(idx, fabric_index=0), f"fabric preset {piece}")

    fabric_ok = _drain(ctx.client, "fabric preset assignment", timeout=15)
    if not fabric_ok:
        print("  [WARN] Fabric preset drain failed — color/texture steps may also be affected.")

    # --- Locate artifact paths ---
    # patterns_dir is typically …/panels/dxf; image_info lives two levels up.
    image_info_dir: Path = ctx.patterns_dir.parent.parent / "image_info"
    colors_json = getattr(ctx, "colors_json_path", None) or image_info_dir / "colors.json"
    textures_dir = getattr(ctx, "textures_dir", None) or ctx.patterns_dir.parent / "textures"
    graphic_path = getattr(ctx, "graphic_diffuse_path", None) or image_info_dir / "graphic_diffuse.png"

    print(f"  [DEBUG] colors_json path: {colors_json} (exists={Path(colors_json).exists()})")
    print(f"  [DEBUG] textures_dir:     {textures_dir} (exists={Path(textures_dir).exists()})")
    print(f"  [DEBUG] graphic_path:     {graphic_path} (exists={Path(graphic_path).exists()})")

    # --- Step b: Apply extracted base color ---
    # Phase 1 fix: color is now dispatched via PostMessage/QueuedConnection so it
    # no longer deadlocks CLO's main thread. reset_fabric_status clears the counters
    # before this batch; wait_for_fabric polls until the CAPI call completes.
    base_rgb = _load_base_color(Path(colors_json))
    if base_rgb is not None:
        r, g, b = base_rgb
        ctx.client.reset_fabric_status()
        for piece, idx in piece_indices.items():
            print_result(ctx.client.set_fabric_color(idx, r, g, b), f"color {piece}")
        color_ok = ctx.client.wait_for_fabric(timeout=10)
        if not color_ok:
            print(f"  [WARN] Color dispatch did not confirm — check /fabric-status for details.")
    else:
        print("  No colors.json found — skipping color application.")

    # --- Step c: Apply per-panel texture atlas ---
    # Phase 1 fix: texture dispatch is now async via PostMessage/QueuedConnection.
    # reset_fabric_status clears counters; wait_for_fabric polls until all done.
    textures_dir = Path(textures_dir)
    found_textures = [
        (piece, textures_dir / f"{piece}_texture.png")
        for piece in _PIECES
        if (textures_dir / f"{piece}_texture.png").exists()
    ]
    if found_textures:
        ctx.client.reset_fabric_status()
        for piece, tex_path in found_textures:
            if piece in piece_indices:
                print_result(
                    ctx.client.set_fabric_texture(piece_indices[piece], str(tex_path)),
                    f"texture {piece}",
                )
        tex_ok = ctx.client.wait_for_fabric(timeout=20)
        if not tex_ok:
            print("  [WARN] Texture dispatch did not confirm — check /fabric-status for details.")
    else:
        print("  No panel textures found — skipping texture atlas application.")

    # --- Step d: Apply graphic/logo overlay to front panel only ---
    graphic_path = Path(graphic_path)
    design_type = _load_design_type(Path(colors_json))
    print(f"  [DEBUG] design_type='{design_type}', graphic exists={graphic_path.exists()}")
    if (
        graphic_path.exists()
        and design_type in ("logo", "text")
        and "front_panel" in piece_indices
    ):
        front_idx = piece_indices["front_panel"]
        print(f"  Applying graphic overlay (type={design_type}) to front_panel ...")
        print_result(
            ctx.client.set_fabric_graphic(
                front_idx,
                str(graphic_path),
                u=0.5,
                v=0.35,
                scale=1.0,
            ),
            "graphic front_panel",
        )
        _drain(ctx.client, "graphic overlay", timeout=15)
    elif design_type == "pattern":
        print("  Design type is 'pattern' — already covered by texture atlas; skipping graphic overlay.")
    else:
        print("  No graphic diffuse found or non-logo design — skipping graphic overlay.")

    # Step 8 is cosmetic — never block the pipeline even if color/texture failed.
    return True
