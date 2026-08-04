# Step 4 - Avatar generation pipeline invocation (worker → CLO)

**Status:** planned, not yet executed
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

Not started.
