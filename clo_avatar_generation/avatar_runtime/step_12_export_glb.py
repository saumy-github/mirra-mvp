"""Step 12: export the saved avatar as GLB via the CLO plugin's /export endpoint,
then pack it into a real, self-contained binary .glb.

**Why packing is required, not optional** (supersedes the earlier assumption
in doc 05/11 that a JSON-embedded-vs-binary mismatch was "harmless in
practice"): live-tested 2026-08-08, both VS Code's 3D preview and CLO3D's
own glTF importer refuse the raw plugin export outright ("Invalid GLB
header") rather than sniffing content. Reading the plugin source
(`clo_workspace/windows/RestPlugin_windows.cpp`, the `cmd.type == "export"`
branch) explains why: CLO's `ExportGLTF` is always called with
`asGLB=false` — the requested `format` from the REST call is never actually
wired to that parameter — and with `asGLB=false` this SDK/CLO version
writes the **glTF-separate** layout: a small JSON file (named `.glb` by us,
but plain text) plus an external `.bin` mesh buffer plus ~25 external
texture image files, all sibling files in the run directory. Neither VS
Code nor CLO3D's importer will follow those external references when the
file is opened as a standalone `.glb` — they require one self-contained
binary file.

The plugin's own /export contract can't produce that today (see the C++
comment above `ExportGLTF(...)`: "Until CLO exposes a working binary-GLB
path, callers must treat this output as .gltf content, not .glb"). So this
step does the packing itself in Python, via `pygltflib` (already a hard
dependency — see requirements.txt, also used by
`clo_vto/native_vto/step_12_texture_glb.py` for the same library):
loads the raw JSON + external buffer/images CLO wrote, embeds the mesh
buffer as the GLB binary chunk and every image as a base64 data URI, and
writes a genuinely self-contained `result_avatar_packed.glb`. Verified by
round-tripping the packed file back through `GLTF2.load_binary()`.

Never blocks the pipeline: any failure here (raw export failed, or packing
failed) is logged and `ctx.avatar_glb_path` is left unset — the .avt/
measurements already succeeded via step_11, which is what actually matters
for Step 1. A missing GLB is preferable to silently shipping the known-
broken raw file downstream.
"""

from __future__ import annotations

from pathlib import Path

from .context import Step1Context

# 12-byte GLB header floor for the raw export - anything smaller is almost
# certainly an error response or an empty write, not real content.
_MIN_RAW_GLB_BYTES = 1024


def _pack_self_contained_glb(raw_path: Path, packed_path: Path, logger) -> bool:
    """Load CLO's raw glTF-separate export and re-save as one self-contained
    binary .glb. Returns False (never raises) on any failure so the caller
    can treat it as non-blocking."""
    try:
        from pygltflib import GLTF2, BufferFormat, ImageFormat
    except ImportError:
        logger.warning("GLB packing skipped: pygltflib not installed (see requirements.txt).")
        return False

    try:
        gltf = GLTF2().load_json(str(raw_path))
        gltf.convert_images(ImageFormat.DATAURI)
        gltf.convert_buffers(BufferFormat.BINARYBLOB)
        gltf.save(str(packed_path))
    except Exception as exc:
        logger.warning("GLB packing failed: %s", exc)
        return False

    # Round-trip the file we just wrote through the binary loader - the same
    # check a real consumer (CLO3D, three.js, <model-viewer>) will do -
    # rather than trusting that .save() produced something valid.
    try:
        GLTF2().load_binary(str(packed_path))
    except Exception as exc:
        logger.warning("GLB packing produced an unreadable file (round-trip check failed): %s", exc)
        return False

    return True


def run(ctx: Step1Context) -> bool:
    if not ctx.extracted_avatar_path:
        payload = {
            "exported": False,
            "reason": "No saved avatar to export from (step_11 did not produce one).",
        }
        ctx.log_json("export_glb", payload)
        ctx.logger.warning("Skipping GLB export: no saved avatar from step_11")
        return True

    run_dir = ctx.require_run_dir()
    raw_glb_path = run_dir / "result_avatar.glb"

    ctx.logger.info("Exporting raw avatar GLB (glTF-separate, CLO plugin limitation): %s", raw_glb_path)
    export_result = ctx.client.export_avatar_glb(raw_glb_path)
    if not export_result.get("success", False):
        payload = {
            "exported": False,
            "reason": export_result.get("error") or export_result.get("message") or "Export command rejected.",
            "export_result": export_result,
        }
        ctx.log_json("export_glb", payload)
        ctx.logger.warning("GLB export command failed: %s", payload["reason"])
        return True

    try:
        ctx.client.wait_for_queue(timeout=120)
    except TimeoutError as exc:
        ctx.logger.warning("Queue drain timed out during GLB export: %s — checking file anyway", exc)

    if not raw_glb_path.exists():
        payload = {"exported": False, "reason": f"Raw GLB not found at {raw_glb_path} after export."}
        ctx.log_json("export_glb", payload)
        ctx.logger.warning("GLB export: file missing after export (%s)", raw_glb_path)
        return True

    size_bytes = raw_glb_path.stat().st_size
    if size_bytes < _MIN_RAW_GLB_BYTES:
        payload = {
            "exported": False,
            "reason": f"Raw GLB exists but is suspiciously small ({size_bytes} B) - likely corrupt.",
        }
        ctx.log_json("export_glb", payload)
        ctx.logger.warning("GLB export: raw file too small (%d bytes)", size_bytes)
        return True

    ctx.logger.info("Raw GLB written (%d B) — packing into a self-contained binary .glb", size_bytes)
    packed_path = run_dir / "result_avatar_packed.glb"
    packed_ok = _pack_self_contained_glb(raw_glb_path, packed_path, ctx.logger)

    if not packed_ok:
        payload = {
            "exported": True,
            "packed": False,
            "raw_path": str(raw_glb_path),
            "reason": "Raw export succeeded but packing into a self-contained binary .glb failed - "
            "see warnings above. Raw glTF-separate files remain in the run dir for debugging but are "
            "not web/CLO-import-usable on their own.",
        }
        ctx.log_json("export_glb", payload)
        ctx.logger.warning("GLB packing failed - no usable GLB for this run.")
        return True

    packed_size = packed_path.stat().st_size
    ctx.avatar_glb_path = packed_path
    payload = {
        "exported": True,
        "packed": True,
        "raw_path": str(raw_glb_path),
        "raw_size_bytes": size_bytes,
        "packed_path": str(packed_path),
        "packed_size_bytes": packed_size,
    }
    ctx.log_json("export_glb", payload)
    ctx.logger.info(
        "GLB packed and verified: %s (%.1f MB, round-tripped through GLTF2.load_binary)",
        packed_path,
        packed_size / (1024 * 1024),
    )
    return True
