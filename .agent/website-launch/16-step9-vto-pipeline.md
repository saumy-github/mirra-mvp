# Step 9 - VTO pipeline invocation (worker → CLO)

**Status:** blocked on an unresolved bug found during earlier testing — verify/fix before trusting any output
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [07-step0-worker-queue.md](07-step0-worker-queue.md); benefits from [14-step7-garment-catalog.md](14-step7-garment-catalog.md) for real garment selection

## Goal

Given a try-on job, drive the CLO VTO pipeline to drape the selected garment on the user's existing avatar and produce a textured, viewable GLB.

## Current state

- `clo_vto`'s 12-step native pipeline (`clo_vto/native_vto/`, `step_01_health` through `step_12_texture_glb`) already exists and is wired for the current single default-panel t-shirt (`clo_vto/default_panels/dxf/`).
- GLB export (`step_11_export_note.py`) already calls the plugin's `/export` endpoint the same way Step 4's avatar export does.
- Texturing (`step_12_texture_glb.py`) already injects per-panel textures/colors into the exported GLB via `pygltflib`.

## Blocking prerequisite — found, not yet resolved

`step_12_texture_glb.py` loads the exported file with `GLTF2().load(str(glb_path))`, which assumes true binary `.glb`. But the plugin's export (confirmed directly, same investigation as Step 4's avatar GLB) actually produces **JSON-embedded glTF** mislabeled with a `.glb` extension — a plain JSON document starting with `{`, not the binary `glTF` magic header. This is very likely the same bug affecting this step too, since it's the identical endpoint and the identical (binary-assuming) load call.

Because `step_12` is written to be **silently non-blocking on failure by design** (it always returns `True` regardless of whether texturing actually worked), **a "successful" pipeline run today does not guarantee a real textured GLB came out the other end.** This has likely never been verified end-to-end.

**This must be resolved before Step 9 is considered done — not deferred to "we'll notice if it's broken," because the failure mode is specifically designed not to be noticed.**

## Remaining work

1. **Resolve the `.glb`/`.gltf` naming decision** (same decision as Step 4 — make it once, apply everywhere, don't decide it twice).
2. **Fix the loader in `step_12_texture_glb.py`** to read the JSON-embedded path (`pygltflib`'s JSON-load path) instead of assuming binary — or, if the naming decision lands on `.gltf`, this may already resolve itself depending on how `pygltflib` dispatches by extension. Verify either way, don't assume.
3. **Run a real end-to-end test**: full `clo_vto/run_clo_vto.py` against a real avatar + the current default garment, and actually open the resulting file — confirm textures are genuinely applied (not grey/untextured), per doc 01's Phase 3 verification plan, which flagged this exact risk but hadn't executed it yet.
4. **Once Step 7's catalog wiring exists**, point pattern loading at `live_upload/catalog/<cloth_id>/<size_id>/` instead of `default_panels/dxf/` — this step's pipeline logic doesn't otherwise change, just its pattern source.
5. Same non-blocking-failure discipline as everywhere else in this codebase applies to any *new* code added here — but the existing silent-failure design on `step_12` specifically is what let this bug go unnoticed, so treat "test with a real file, don't trust the log line" as a standing rule for this step going forward, not just a one-time fix.

## Files touched

- `clo_vto/native_vto/step_12_texture_glb.py` — loader fix
- possibly `clo_vto/native_vto/step_11_export_note.py` if the naming decision changes the export call itself
- once Step 7 lands: pattern-loading step(s) (`step_04_import_patterns.py` and related) — catalog-driven paths instead of `default_panels/`

## Verification

- Run the full VTO pipeline against a real avatar + garment.
- Open the resulting file in an external viewer — confirm the garment is textured (visible color/pattern), not grey/blank.
- Deliberately break the texture-injection step and confirm it now surfaces as a real, visible failure rather than a silent no-op — closes the exact gap that let this bug go undetected the first time.

## Execution Log

### 2026-08-01/02 - Bug found during doc 01's Phase 2 testing (avatar side, same root cause)

Not this step's own execution yet — noting here because it's the same underlying bug. See `01-docker-and-clo-render-pipeline.md`, "Phase 2 findings" for the original investigation (JSON-embedded glTF, not binary GLB, confirmed by inspecting the file header directly).

Not started on this step's own fix.
