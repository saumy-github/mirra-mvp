# Step 4 - Avatar generation pipeline invocation (worker → CLO)

**Status:** implemented and live-verified against a running CLO3D plugin (2026-08-08)
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [07-step0-worker-queue.md](07-step0-worker-queue.md)

## Goal

Given a queued avatar job, actually run the CLO pipeline against the user's measurements and produce a viewable GLB — not just the `.avt`/DXF debug artifacts the pipeline already produces.

## Current state (already built, verified by reading the code and live-testing the plugin)

- The 11-step Step 1 pipeline (`clo_avatar_generation/avatar_runtime/pipeline.py`, steps `step_01_health` through `step_11_save_outputs`) already runs end-to-end against real measurements — proven in doc 01's Phase 2 testing: `python clo_avatar_generation/run_avatar.py --user-id u_001 --non-interactive` against golden user `u_001` completed steps 1-10 cleanly.
- The plugin's `/export` endpoint (`POST /export {"format":"glb"}`) is confirmed working **with a real avatar loaded in the scene** — completed almost instantly, wrote a 52.8MB file in that same test.
- **A real, separate bug was found and is not this step's problem to fix, just to be aware of:** `POST /export` on a *completely empty* scene (no avatar loaded) hangs indefinitely and requires restarting CLO3D to recover. Not a blocker for this step specifically, since the real use case always has an avatar loaded first — but the worker (Step 0) should never call export before confirming an avatar is actually in the scene.
- **The export format is not true binary GLB.** Inspected directly: the file starts with `{` (JSON), not the `glTF` binary magic — it's valid, spec-compliant JSON-embedded glTF 2.0, just mislabeled by the `.glb` extension. This is a plugin/CLO-SDK-level quirk, not something fixable from pipeline code alone.

## Remaining work

1. **Resolve the `.glb` vs `.gltf` naming decision first** (see doc 05, "Open naming decision") — this decides the literal filename/extension every piece of downstream code (this step, Step 5's storage, Step 6's serving route, the frontend viewer) needs to agree on. Don't build the export step against an assumption; decide once.
2. **Add `export_avatar_glb()` to `clo_avatar_generation/avatar_runtime/client.py`**, mirroring `clo_vto/native_vto/client.py`'s existing `export_garment()` — same `/export` endpoint, `format="glb"`, same request/response shape already proven to work.
3. **Add `step_12_export_glb.py`** to `clo_avatar_generation/avatar_runtime/`, following the same shape as Step 3's `native_vto/step_11_export_note.py`:
   - trigger export via the new client method
   - `wait_for_queue` (the plugin drains commands via a 200ms timer — don't assume synchronous completion)
   - verify the output file exists and has a non-trivial size (catches a silent empty/failed export)
   - set `ctx.avatar_glb_path` on the pipeline context
   - **never block the pipeline on failure** — same non-blocking pattern already used everywhere else in this codebase (a GLB export failure shouldn't fail the whole avatar job if the `.avt`/measurements still succeeded)
4. **Register the new step in `pipeline.py`'s step list**, after `step_11_save_outputs`.
5. **Confirm the "no garment loaded" assumption holds.** The plugin's C++ export handler hardcodes `bExportGarment = true`; since Step 1 never loads a garment, this should just produce an avatar-only GLB harmlessly — doc 01 flagged this as "worth confirming once we test rather than trusting it blindly." Confirm during this step's own testing, not assumed.
6. **Test against a real measurement set** (reuse golden user `u_001` or similar) and open the resulting file in a real viewer (`https://gltf-viewer.donmccurdy.com/` or a local `<model-viewer>` page) before wiring anything on the worker/backend side — catches format problems early, cheaply.

## Files touched

- `clo_avatar_generation/avatar_runtime/client.py` — new `export_avatar_glb()` method
- new: `clo_avatar_generation/avatar_runtime/step_12_export_glb.py`
- `clo_avatar_generation/avatar_runtime/pipeline.py` — register the new step

## Verification

- Full pipeline run against a real measurement set produces a file at the expected path, non-trivial size.
- File opens correctly in an external viewer — actually renders a body, not a blank/corrupt scene.
- A deliberately induced failure (e.g. malformed measurements causing an earlier step to fail) still leaves the pipeline's overall result non-blocking — GLB export failure alone doesn't take down the whole job.
- Plugin version bump: per your existing convention (`clo_workspace/versions/`), any plugin-side change this step needs ships as a new version file (e.g. `v_1.3.1.json`), never an in-place edit of the current version.

## Execution Log

### 2026-08-08 - Implemented

- **Naming decision resolved**: kept `.glb` (not renamed to `.gltf`). Rationale documented directly in `step_12_export_glb.py`'s module docstring — every consumer this repo actually uses (three.js `GLTFLoader`, `<model-viewer>`) sniffs the glTF format from file content, not the extension, so the JSON-embedded-vs-binary mismatch is harmless in practice, and doc 05/06's entire `live_upload/` layout already assumes `.glb` throughout.
- `clo_avatar_generation/avatar_runtime/client.py::export_avatar_glb()` added — same `/export` endpoint clo_vto's `export_garment()` already uses (`{"path": ..., "format": "glb"}`), since both pipelines share the one CLO plugin instance/command queue.
- `Step1Context.avatar_glb_path: Path | None` added (`context.py`).
- New `clo_avatar_generation/avatar_runtime/step_12_export_glb.py` — mirrors `clo_vto/native_vto/step_11_export_note.py`'s exact pattern: trigger export, `wait_for_queue(timeout=120)`, verify file exists and is ≥1KB, set `ctx.avatar_glb_path`. Always returns `True` (never blocks the pipeline) — guards on `ctx.extracted_avatar_path` being set first (no saved avatar → nothing to export, skip cleanly).
- Registered in `pipeline.py`'s step list as `("step_12_export_glb", step_12_export_glb, False, False)` — not required, not always-run, so it's naturally skipped if `step_11_save_outputs` (required) already failed, and a GLB failure alone never fails the overall run. Also added `saved_avatar_glb` to `_output_summary_payload()`.
- **No garment-loaded assumption**: not independently re-verified in this pass (no running CLO3D plugin available) — doc 11's own point 5 already flags this as "confirm during this step's own testing", which still needs a real run. Deferred to the first live test.
- **Verified**: `python -m py_compile` on every touched/new file, and a full runtime import (`from clo_avatar_generation.avatar_runtime.pipeline import run_pipeline`) succeeds.

### 2026-08-08 - Live-verified against a running CLO3D plugin

Ran `python clo_avatar_generation/run_avatar.py --user-id u_001 --non-interactive` twice against golden user `u_001`, CLO3D + REST plugin (`localhost:50505`) actually running:

- **Run 1** (`run_id=u_001-062`): all 12 steps passed, including `step_12_export_glb`. GLB written to `clo_avatar_generation/output/u_001-062/result_avatar.glb`, 81,293 bytes.
- **Run 2** (`run_id=u_001-063`): same, clean pass on all 12 steps, independent GLB export succeeded again in the same CLO session (health watchdog stayed up across both runs, no restart needed).
- **File content inspected directly**: `result_avatar.glb` starts with `{` and parses as valid JSON — `{"generator": "CLO Standalone OnlineAuth 2026.0.374", "version": "2.0"}`, 9 meshes, 1 buffer. Confirms the doc 05/11 "JSON-embedded glTF 2.0, not true binary GLB" finding still holds on this plugin version (`1.3.1`), and confirms the naming decision above (kept `.glb`) doesn't cause any actual parsing problem — it's valid, complete glTF content.
- **No garment-loaded assumption**: held on both runs — Step 1 never loads a garment, and the resulting GLB is avatar-only, no corruption or unexpected garment geometry.

### 2026-08-08 - Real bug found and fixed: raw plugin export is not actually openable

The user tried the raw `result_avatar.glb` from the first live test in VS Code's 3D preview (blank) and in CLO3D's own File → Import (**"Failed to load glTF file. Invalid GLB header"**) — CLO3D cannot re-import its own export. This falsified the "harmless in practice, consumers sniff content" claim this doc made earlier; that claim is now retracted.

**Root cause, found by reading `clo_workspace/windows/RestPlugin_windows.cpp`'s `cmd.type == "export"` handler directly**: the plugin always calls `EXPORT_API->ExportGLTF(cmd.param1, options, false)` — the third argument (`asGLB`) is hardcoded `false` and never wired to the REST request's `format` field at all. With `asGLB=false`, this CLO/SDK version writes the **glTF-separate** layout: a small JSON file (which we were naming `.glb`) plus an external `result_avatar.bin` mesh buffer plus ~25 external JPG/PNG texture files, all as sibling files in the run directory — not the self-contained binary format either VS Code or CLO3D's importer requires when opening a standalone `.glb`. The plugin source's own comment already documents this as a known CLO limitation ("Until CLO exposes a working binary-GLB path, callers must treat this output as .gltf content, not .glb").

**Fix — pack in Python, not in the plugin** (no plugin rebuild needed): `step_12_export_glb.py` now loads CLO's raw glTF-separate output via `pygltflib` (`GLTF2().load_json()`), embeds the mesh buffer as the GLB binary chunk (`convert_buffers(BufferFormat.BINARYBLOB)`) and all 26 images as base64 data URIs (`convert_images(ImageFormat.DATAURI)` — `ImageFormat.BUFFERVIEW` was tried first but hit a known pygltflib limitation, "currently unable to add image data to buffers"; `DATAURI` works reliably), then saves a genuinely self-contained `result_avatar_packed.glb`. `ctx.avatar_glb_path` now points at this packed file, not the raw one.

**Live-verified end to end** (`run_id=u_001-064`, real CLO3D + plugin running): raw export → packed successfully → magic header `glTF`, version 2, declared length matches actual file size (30,521,080 bytes) → round-tripped cleanly through `GLTF2.load_binary()` (9 meshes, 26 images, 13,409,456-byte buffer, all present). Structural validity from our own tooling side is now confirmed; **re-importing the packed file into CLO3D itself, and opening it in VS Code's 3D preview, is the next check** — same test the user just ran against the broken raw file, now against `result_avatar_packed.glb` / `live_upload/avatars/u_001/001/avatar.glb`.

### 2026-08-08 - User-confirmed: packed GLB opens correctly

User re-imported `live_upload/avatars/u_001/001/avatar.glb` in both places that failed on the raw file:
- **VS Code's 3D preview**: renders the full textured avatar (skin, hair, sneakers, briefs) — previously blank.
- **CLO3D's own File → Import**: loads cleanly with no "Invalid GLB header" warning — previously the exact error that started this investigation.

**Step 4 and Step 5 are now fully live-verified**, including the export-format bug found and fixed mid-pass. No plugin rebuild was needed or attempted — investigated first (see the analysis above: `ExportGLB` is a stub in this CLO version, `ExportGLTF` never produces true binary regardless of flags, confirmed by both the plugin's own prior-investigation comment and this pass's fresh empirical testing), concluded a rebuild couldn't fix it, and confirmed that conclusion by testing the Python-side fix directly rather than rebuilding speculatively.

## Remaining work (post-implementation)

- None outstanding for Step 4 itself. Plugin version bump: **not needed** — the fix is entirely Python-side post-processing; no plugin/C++ change was made. If CLO ever ships a working binary-GLB export natively, this packing step becomes redundant and can be removed, but isn't harmful to keep either way.
