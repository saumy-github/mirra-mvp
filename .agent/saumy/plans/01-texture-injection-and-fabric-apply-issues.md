# 01 — Texture/material problems found in the c_001/s_001 VTO test run

Status: *Bug 1 fixed (see `04-fix-panel-material-matching-plan.md`); Bug 2 root-caused and resolved (explanation only, no code fix — see below); no new pipeline run done*
Observed: *2026-09-12*
Run that exposed this: `clo_vto/output/u_001/c_001/s_001/002/` (via
`python clo_vto/run_clo_vto.py --use-default-panels --ingestion-output-dir
product_ingestion/output/c_001/s_001/001 --user-id u_001 --cloth-id c_001
--size-id s_001`)

## Bug 1 (confirmed): GLB texture injection paints avatar body parts with garment fabric

`clo_vto/native_vto/step_12_texture_glb.py::_match_panel()` (line 196) maps
every material found in the exported GLB to one of the 4 garment panels
(`front_panel`, `back_panel`, `sleeve_left`, `sleeve_right`) so the right
texture gets injected into the right material. It has three fallback tiers:

```python
_PANEL_KEYWORDS = {
    "front_panel":  ["front", "f_panel", "body_f"],
    "back_panel":   ["back",  "b_panel", "body_b"],
    "sleeve_left":  ["left",  "sleeve_l", "sl", "arm_l"],
    "sleeve_right": ["right", "sleeve_r", "sr", "arm_r"],
}
# ...
# 2. Index-order fallback for numeric / opaque material names.
# 3. Ultimate fallback: front_panel.
```

The real run's 17-material GLB exposed two distinct failures in this logic:

1. **Substring collision.** `Material_RightShoe_...` and
   `Material_LeftShoe_...` (avatar shoe materials) contain the literal
   substrings `"right"` / `"left"`, so they get matched to `sleeve_right` /
   `sleeve_left` and painted with sleeve fabric texture.
2. **Unconditional catch-all.** Materials named `face_...`, `body2_...`,
   `arm_...`, `leg_...`, `eye_...`, `eyelash_...`, `Material_Hair_...`,
   `toothSG1_...` don't match any keyword and sit past the 4-item
   index-fallback range (`_INDEX_TO_PANEL` only covers indices 0-3), so they
   fall to "ultimate fallback: front_panel" and get the **garment's front
   panel texture pasted onto the avatar's face, skin, hair, eyes, and
   teeth.**

The step's own log reported this as full success:

```
[0] 'FABRIC 1_437309'              -> front_panel: texture injected OK
[5] 'Material_Hair_437505'         -> front_panel: texture injected OK
[8] 'face_437590'                  -> front_panel: texture injected OK
[9] 'body2_437598'                 -> front_panel: texture injected OK
[10] 'arm_437606'                   -> front_panel: texture injected OK
[11] 'leg_437614'                   -> front_panel: texture injected OK
[12] 'eye_437625'                   -> front_panel: texture injected OK
[16] 'toothSG1_437657'              -> front_panel: texture injected OK
────────────────────────────────────────────────────
Output -> ...\simulation_textured.glb  (38.5 MB)
[STEP 13] ✓  completed in 0.4s
```

"Injected OK" only means "a texture write succeeded on that material" — the
function has no concept of "this material isn't a garment panel at all,
leave it alone." Opening `simulation_textured.glb` in a viewer right now
would show the avatar's face/skin/hair/eyes textured in t-shirt fabric.

**Not fixed.** `_match_panel()` needs a real "not a garment material, skip"
path (e.g. only assign a texture to a material if it passes the keyword
match *or* is one of exactly the first N materials CLO is known to export
for the garment, never as a blanket fallback for everything else).

## Bug 2 (RESOLVED — root cause confirmed 2026-09-12): the CLO viewport doesn't show the real garment texture

Saumy captured a screenshot of the live CLO scene after this same run — the
avatar wears a shirt with a black/white repeating triangular/diamond
pattern. That pattern does **not** match the actual garment texture on
disk:

`product_ingestion/output/c_001/s_001/001/panels/textures/front_panel_texture.png`
is a plain navy panel silhouette with a white "BOSTON"-style logo — solid
navy background, no triangles, no repeating geometric pattern anywhere.

So whatever CLO is actually rendering in its own 3D viewport (`FABRIC 1` is
the only material shown in the Object Browser) is **not** the texture our
pipeline sent it, despite `step_08_apply_fabric.py` reporting every fabric,
color, and texture call as `[OK] ... queued` for all 4 panels.

**Most likely explanation, not confirmed:** `step_08_apply_fabric.py::run()`
line 108 calls `ctx.client.set_fabric(idx, fabric_index=0)` for every panel
*before* applying our own color/texture — `fabric_index=0` selects a CLO
built-in preset fabric. If the subsequent
`set_fabric_color`/`set_fabric_texture` calls don't actually visually
override that preset (queued/accepted by the REST layer, but not truly
applied to the render), the panel would keep showing preset 0's own
swatch — which could very plausibly be a generic textured/patterned
default fabric, matching what's in the screenshot. This would line up with
an already-documented, existing known issue in the same file (lines
145–151):

> "the panel texture ... is applied via `SetBaseTextureMapImageGivenFilePath`,
> which CLO treats as a repeating fabric swatch rather than a UV-mapped
> print. The silhouette tiles across the panel and its transparent regions
> show the avatar's skin through the garment."

That comment describes a *different* visible symptom (a tiled silhouette
with skin showing through), not a triangle pattern, so it may not be the
exact same failure — **this is not confirmed, only the closest documented
lead.** Needs a live check inside CLO (Fabric panel → inspect what
`FABRIC 1` actually has assigned) rather than more static reading, since
static tracing of `step_08_apply_fabric.py` did not reveal an obvious bug
in the color/texture dispatch calls themselves.

### Resolution (2026-09-12)

Traced the full call chain in `RestPlugin_windows.cpp`:
`set-fabric-color`/`set-fabric-texture` do report `success: true`
immediately at dispatch time (before `FabricDispatcher::dispatchColor`/
`dispatchTexture` actually run `SetFabricPBRMaterialBaseColor`/
`SetBaseTextureMapImageGivenFilePath` on CLO's main thread) — this was
flagged as a separate finding in `02-false-success-reporting-audit.md`.
However, a **real verification layer already exists and works**: those
dispatch functions update `g_fabricStatus` (`pending`/`completed`/
`failed`) once the real SDK call actually completes or throws, exposed via
`/fabric-status`. `step_08_apply_fabric.py` already calls
`ctx.client.wait_for_fabric(timeout=...)`, which polls that real status and
returns the true success/failure — not the premature ack. In this run it
returned `True` for both the color and texture batches, with no
`[fabric-status] FAILED` line anywhere in the log. So the real SDK calls
genuinely succeeded; this was not a hidden async-failure bug.

**The actual cause is the already-documented swatch-vs-UV-print issue**
quoted above, now confirmed rather than speculative: `front_panel_texture.png`
is a whole-garment cutout on a transparent background, but
`SetBaseTextureMapImageGivenFilePath` makes CLO apply it as a **repeating
fabric swatch**, not a UV-mapped print. Tiled repeatedly at small scale
across the whole garment surface and rendered under real lighting, a
navy-background/white-logo cutout produces exactly the kind of busy
geometric/triangular pattern seen in the screenshot — not the literal
logo. This is a real, already-known limitation (not a new bug), and fixing
it properly requires a UV-mapped texture-application approach instead of
the current swatch-based API call — out of scope for tonight.

**Downgrade to `02-false-success-reporting-audit.md` finding #1
(`clo_workspace`):** the premature `success: true` at dispatch time is
real, but is not the live problem here, since `wait_for_fabric()` already
catches genuine async failures correctly. Still worth fixing for
correctness (the immediate `/execute` response is misleading on its own),
but it did not cause this symptom.

## Observed but unexplained: `design_type` debug line

The same run printed:

```
[DEBUG] design_type='', graphic exists=True
No graphic diffuse found or non-logo design — skipping graphic overlay.
```

`extraction_metadata.json` for this exact run
(`product_ingestion/output/c_001/s_001/001/image_info/extraction_metadata.json:58`)
contains `"design_type": "logo"`, and
`step_08_apply_fabric.py::_load_design_type()` derives the metadata file
path as `colors_json.parent / "extraction_metadata.json"` — which, by
static reading, should resolve to that exact file and return `"logo"`, not
`""`. The debug line one call earlier in the same run
(`[DEBUG] colors_json path: ...c_001\s_001\001\image_info\colors.json
(exists=True)`) confirms `colors_json` held the correct path at that point.

**Not resolved.** The code as read should have worked; the log shows it
didn't. Did not chase this further with another pipeline run per
instruction — needs either a debugger/print-statement trace on a fresh run,
or independent confirmation that this is reproducible before concluding
anything about the actual cause.

## Avatar count check (per Saumy's request)

This run's own built-in checks both passed:
- Step 3 (Import Avatar): `Scene holds exactly 1 avatar.`
- Step 11 (Save Project): `Project holds exactly 1 avatar.`

So **no avatar-accumulation problem in this specific run.** The underlying
architectural risk remains real and already known/documented separately
(plugin version notes describe avatars surviving `NewProject()` across
runs in the same CLO session, and multiple already-known-crash-prone
per-index avatar query APIs that make it unsafe to just ask CLO "how many
avatars exist" directly) — this run's pass doesn't retire that risk, it
just means this particular run didn't trigger it.

## Scope note

This file covers only what was found while investigating the one test run
above. A broader pass across `clo_workspace/`, `clo_avatar_generation/`,
`product_ingestion/`, and `clo_vto/` for the same class of bug (a step
reporting success/OK while the underlying result is wrong, defaulted, or
silently skipped) was requested separately and is being done via parallel
subagents — see whatever follow-up doc that produces, not this one.
