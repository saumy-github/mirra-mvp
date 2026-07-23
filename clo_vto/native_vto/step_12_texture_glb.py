"""Step 12: Inject texture/color into the exported simulation GLB.

CLO exports a grey, untextured GLB after simulation.  This step reads it with
pygltflib, injects the per-panel texture atlases (and base color as fallback)
from the product-ingestion artifacts, and writes a self-contained
``simulation_textured.glb`` to ctx.output_dir.

Design decisions
----------------
* **Cross-platform**: uses pathlib throughout; forward-slash paths only when
  talking to CLO (not needed here).
* **Self-contained output**: images are embedded as base64 data URIs inside the
  GLB binary buffer — no external PNG files needed to view the result.
* **Graceful degradation**: every failure mode returns True so the pipeline is
  never blocked by this cosmetic step.
* **Pillow-resize**: textures are scaled to the nearest power-of-2 dimensions
  (max 1024 px) for GPU-upload compatibility and file-size control.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Optional

# ── Deferred imports (pygltflib / Pillow may not be installed) ──────────────
# We import at module level so missing packages surface as a clear message
# in run(), not as an ImportError at pipeline startup.
try:
    from pygltflib import (
        GLTF2,
        Image as GltfImage,
        PbrMetallicRoughness,
        Sampler,
        Texture,
        TextureInfo,
    )
    _PYGLTFLIB_OK = True
except ImportError:
    _PYGLTFLIB_OK = False

try:
    from PIL import Image as PilImage
    _PILLOW_OK = True
except ImportError:
    _PILLOW_OK = False


# ── Constants ────────────────────────────────────────────────────────────────

# Max texture dimension (power of 2).  Larger textures are downscaled.
_MAX_TEX_DIM = 1024

# Panel name -> substrings to match against GLB material names (case-insensitive).
# Checked in order; first match wins.  Falls back to index order if no match.
_PANEL_KEYWORDS: dict[str, list[str]] = {
    "front_panel":  ["front", "f_panel", "body_f"],
    "back_panel":   ["back",  "b_panel", "body_b"],
    "sleeve_left":  ["left",  "sleeve_l", "sl", "arm_l"],
    "sleeve_right": ["right", "sleeve_r", "sr", "arm_r"],
}

# Index-order fallback when name-matching fails (CLO default export order).
_INDEX_TO_PANEL = ["front_panel", "back_panel", "sleeve_left", "sleeve_right"]


# ── Private helpers ──────────────────────────────────────────────────────────

def _load_base_color(colors_json: Optional[Path]) -> Optional[tuple[int, int, int]]:
    """Return (r, g, b) from colors.json, or None.

    Supports:
      1. base_colour_hex / base_color_hex  (hex string, primary format)
      2. palette[0].rgb                    (direct RGB list)
      3. base_color.rgb                    (legacy)
    """
    if not colors_json or not colors_json.exists():
        return None
    try:
        data = json.loads(colors_json.read_text(encoding="utf-8"))

        hex_val = data.get("base_colour_hex") or data.get("base_color_hex")
        if hex_val:
            h = str(hex_val).lstrip("#")
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

        palette = data.get("palette", [])
        if palette:
            rgb = palette[0].get("rgb")
            if rgb and len(rgb) >= 3:
                return (int(rgb[0]), int(rgb[1]), int(rgb[2]))

        rgb = data.get("base_color", {}).get("rgb")
        if rgb and len(rgb) >= 3:
            return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception:
        pass
    return None


def _nearest_pot(n: int) -> int:
    """Return the nearest power-of-two <= n (minimum 1)."""
    if n <= 0:
        return 1
    pot = 1
    while pot * 2 <= n:
        pot *= 2
    return pot


def _png_to_bytes(image_path: Path, max_dim: int = _MAX_TEX_DIM) -> Optional[bytes]:
    """Load image via Pillow, resize to POT dims capped at max_dim, return PNG bytes.

    Returns None if Pillow is unavailable or the file cannot be read.
    """
    if not _PILLOW_OK:
        # Without Pillow, read raw bytes and hope the PNG is a valid size.
        try:
            return image_path.read_bytes()
        except Exception:
            return None
    try:
        img = PilImage.open(image_path).convert("RGBA")
        w, h = img.size
        new_w = min(_nearest_pot(w), max_dim)
        new_h = min(_nearest_pot(h), max_dim)
        if (new_w, new_h) != (w, h):
            img = img.resize((new_w, new_h), PilImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return buf.getvalue()
    except Exception:
        return None


def _embed_image(gltf: "GLTF2", png_bytes: bytes) -> int:
    """Embed PNG bytes as a base64 data URI image in the GLTF; return image index."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    img = GltfImage()
    img.uri = data_uri
    img.mimeType = "image/png"
    gltf.images.append(img)
    return len(gltf.images) - 1


def _ensure_sampler(gltf: "GLTF2") -> int:
    """Ensure a default linear-repeat sampler exists; return its index."""
    if not gltf.samplers:
        s = Sampler()
        s.magFilter = 9729   # GL_LINEAR
        s.minFilter = 9987   # GL_LINEAR_MIPMAP_LINEAR
        s.wrapS = 10497      # GL_REPEAT
        s.wrapT = 10497
        gltf.samplers.append(s)
    return 0


def _embed_texture(gltf: "GLTF2", png_bytes: bytes) -> int:
    """Embed PNG, register a Texture node, return texture index."""
    img_idx = _embed_image(gltf, png_bytes)
    sampler_idx = _ensure_sampler(gltf)
    tex = Texture()
    tex.source = img_idx
    tex.sampler = sampler_idx
    gltf.textures.append(tex)
    return len(gltf.textures) - 1


def _apply_texture(material, tex_idx: int) -> None:
    """Set baseColorTexture on a material's PBR block."""
    pbr = material.pbrMetallicRoughness
    if pbr is None:
        pbr = PbrMetallicRoughness()
        material.pbrMetallicRoughness = pbr
    info = TextureInfo()
    info.index = tex_idx
    pbr.baseColorTexture = info
    # White tint so the texture is not tinted by an existing factor.
    pbr.baseColorFactor = [1.0, 1.0, 1.0, 1.0]


def _apply_color(material, r: int, g: int, b: int) -> None:
    """Set baseColorFactor on a material's PBR block; remove any existing texture."""
    pbr = material.pbrMetallicRoughness
    if pbr is None:
        pbr = PbrMetallicRoughness()
        material.pbrMetallicRoughness = pbr
    pbr.baseColorFactor = [r / 255.0, g / 255.0, b / 255.0, 1.0]
    pbr.baseColorTexture = None


def _match_panel(material_name: str, index: int) -> str:
    """Map a GLB material name to a pipeline panel key.

    Strategy:
      1. Substring match against _PANEL_KEYWORDS (case-insensitive).
      2. Index-order fallback for numeric / opaque material names.
      3. Ultimate fallback: front_panel.
    """
    name_lower = (material_name or "").lower()
    for panel, keywords in _PANEL_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return panel
    if 0 <= index < len(_INDEX_TO_PANEL):
        return _INDEX_TO_PANEL[index]
    return "front_panel"


# ── Public step entry point ──────────────────────────────────────────────────

def run(ctx) -> bool:
    """Inject texture/color into the exported simulation GLB.

    Reads ctx.glb_path (set by step_11), injects per-panel textures from
    ctx.textures_dir and base color from ctx.colors_json_path, and writes
    ctx.output_dir/simulation_textured.glb.

    Always returns True — never blocks the pipeline.
    """
    print("\n[12] GLB texture injection ...")

    # ── Guard: dependencies ───────────────────────────────────────────────────
    if not _PYGLTFLIB_OK:
        print("  [SKIP] pygltflib not installed.")
        print("         Run:  pip install pygltflib")
        return True

    if not _PILLOW_OK:
        print("  [WARN] Pillow not installed — textures embedded without resize.")
        print("         Run:  pip install Pillow")

    # ── Guard: skip flag ──────────────────────────────────────────────────────
    if getattr(ctx, "skip_glb_postprocess", False):
        print("  [SKIP] skip_glb_postprocess=True")
        return True

    # ── Guard: source GLB ─────────────────────────────────────────────────────
    glb_path: Optional[Path] = getattr(ctx, "glb_path", None)
    if not glb_path or not glb_path.exists():
        print("  [SKIP] No GLB available (ctx.glb_path not set or file missing).")
        print("         step_11 may not have exported — check CLO window.")
        return True

    size_mb = glb_path.stat().st_size / (1024 * 1024)
    print(f"  source_glb   : {glb_path}  ({size_mb:.1f} MB)")

    # ── Resolve artifact paths ─────────────────────────────────────────────────
    colors_json: Optional[Path] = getattr(ctx, "colors_json_path", None)
    textures_dir: Optional[Path] = getattr(ctx, "textures_dir", None)

    print(f"  colors_json  : {colors_json}  "
          f"({'EXISTS' if colors_json and colors_json.exists() else 'MISSING'})")
    print(f"  textures_dir : {textures_dir}  "
          f"({'EXISTS' if textures_dir and textures_dir.exists() else 'MISSING'})")

    base_color = _load_base_color(colors_json)
    if base_color:
        print(f"  base_color   : RGB{base_color}")

    # Pre-load per-panel PNG bytes (None if file missing or unreadable).
    panel_png: dict[str, Optional[bytes]] = {}
    if textures_dir and textures_dir.exists():
        for panel in _PANEL_KEYWORDS:
            tex_file = textures_dir / f"{panel}_texture.png"
            if tex_file.exists():
                png_bytes = _png_to_bytes(tex_file)
                panel_png[panel] = png_bytes
                status = f"loaded ({len(png_bytes):,} B)" if png_bytes else "load FAILED"
                print(f"    texture [{panel}]: {tex_file.name}  [{status}]")

    # ── Load GLB ──────────────────────────────────────────────────────────────
    try:
        gltf = GLTF2().load(str(glb_path))
    except Exception as exc:
        print(f"  [ERROR] Could not parse GLB: {exc}")
        return True

    if not gltf.materials:
        print("  [WARN] GLB has no materials — nothing to inject.")
        return True

    print(f"  materials    : {len(gltf.materials)} found")
    print("  " + "─" * 52)

    # ── Per-material injection ─────────────────────────────────────────────────
    for i, material in enumerate(gltf.materials):
        mat_name = getattr(material, "name", None) or f"Material_{i}"
        panel = _match_panel(mat_name, i)
        png_bytes = panel_png.get(panel)

        if png_bytes:
            tex_idx = _embed_texture(gltf, png_bytes)
            _apply_texture(material, tex_idx)
            print(f"  [{i}] {mat_name!r:30s} -> {panel}: texture injected OK")
        elif base_color:
            r, g, b = base_color
            _apply_color(material, r, g, b)
            print(f"  [{i}] {mat_name!r:30s} -> {panel}: base color RGB{base_color} OK")
        else:
            print(f"  [{i}] {mat_name!r:30s} -> {panel}: no texture or color (left grey)")

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = ctx.output_dir / "simulation_textured.glb"
    try:
        gltf.save(str(out_path))
    except Exception as exc:
        print(f"  [ERROR] Failed to write textured GLB: {exc}")
        return True

    out_mb = out_path.stat().st_size / (1024 * 1024)
    print("  " + "─" * 52)
    print(f"  Output -> {out_path}  ({out_mb:.1f} MB)")

    ctx.textured_glb_path = out_path
    return True
