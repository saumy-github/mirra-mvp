# 02 — Audit: places that report success/true while the real result is wrong, unverified, or defaulted

Status: *investigated only, nothing fixed, no code changed*
Compiled: *2026-09-12*
Method: 4 parallel read-only agents, one per codebase area, each told to find
more instances of the exact bug shape already confirmed twice tonight (the
CLO plugin's `g_serverRunning` flag, and `clo_vto`'s `_match_panel()`
front-panel catch-all — both documented in
`01-texture-injection-and-fabric-apply-issues.md`). Each agent was told what
was already known/documented so it wouldn't re-report it.

Every item below is **unverified beyond static code reading** — none of
these were reproduced with a live run. Treat this as a prioritized
punch-list to verify one at a time, not as confirmed bugs the way the two
originals are.

---

## `clo_workspace/` (the C++ REST plugin)

1. **DOWNGRADED (2026-09-12, verified against a real run) —
   `RestPlugin_windows.cpp:1934-2005`** — `set-fabric-color`,
   `set-fabric-texture`, `set-fabric-graphic` do report `success: true`
   *before* the real CLO call runs (it's dispatched async via
   `PostMessage`), which is still real and still worth fixing for
   correctness. But a genuine verification layer already exists:
   `FabricDispatcher`'s dispatch functions update `g_fabricStatus`
   (`pending`/`completed`/`failed`) once the real SDK call actually
   completes, exposed via `/fabric-status`, and
   `step_08_apply_fabric.py` already polls it via `wait_for_fabric()`
   before proceeding. This was checked directly against a real run: it
   returned `True` (real success, not just the premature ack) for both
   the color and texture batches. **This was NOT the cause of the
   CLO-viewport texture mismatch in doc 01** — that mismatch's real cause
   was found and confirmed separately (the already-documented
   swatch-vs-UV-print tiling behavior). See doc 01's "Resolution"
   section under Bug 2 for the full trace.
2. **`RestPlugin_windows.cpp:1905-1929`** — `arrange-pattern` and
   `set-fabric` hardcode `asyncResult.success = true` right after calling
   the CLO API, with zero check of the call's own result and no
   `CLOGuard::patternIndexValid` guard (unlike the fabric-color/texture
   handlers, which do guard). A bad pattern index would still report
   success.
3. **`RestPlugin_windows.cpp:690-717`** — 13 of 15 `/capabilities` flags
   are hardcoded `true`, never probed at runtime (only 2 fields were
   converted to real probes, per `v_1.3.0.json`). A caller has no way to
   detect a session where one of those 13 is actually broken.
4. **`BuildArrangementDebugPayload()` (:467-496), `read-pattern-line-lengths`
   (:2099-2124), `read-pattern-arrangements` (:2144-2158),
   `read-avatar-debug` (:2163-2214)** — each swallows CLO API exceptions
   into empty/zero defaults but still reports `success: true`. `v_1.2.0.json`
   already fixed this exact pattern for 5 sibling endpoints; these four
   were missed.
5. *(minor)* **`RestPlugin_windows.cpp:1706-1717`** — avatar property
   before/after verification reads are silently swallowed; `success` is
   still reported based only on the `SetAvatarProperties` call itself.

## `clo_avatar_generation/` (Step 1 — avatar generation)

1. **`step_07_import_base_avatar.py:35-63`** — the "new project" scene-clear
   path (`IMPORT_BASE_AVATAR_INTO_CLO = False`, the current default) trusts
   the immediate REST acknowledgement instead of pulling the real result
   from `/status`, the only step in the file that skips this check. The
   plugin's own `/new-project` handler always returns `success: true` the
   instant the command is *queued*, not once `NewProject()` actually runs —
   and the async worker also hardcodes success. This file's own docstring
   already records "five back-to-back runs left 3,4,1,1,2 avatars" from
   exactly this kind of scene-clear race; step 7 can't detect a repeat of
   that until step 11's post-hoc avatar-count check, after the whole
   apply/save cycle already ran.
2. **`apply_mode.py:44-46`** — defaults `has_native_avatar_import` to `True`
   if `/capabilities` omits the field. Currently masked by step_01's
   required-capabilities check, but would start mattering the moment that
   list changes independently.
3. **`step_12_export_glb.py:138-153`** — the binary-GLB-direct success
   branch only checks a 4-byte magic number + min size, skipping the
   round-trip `GLTF2().load_binary()` verification the JSON-fallback branch
   does. Lower severity since a bad GLB here is cosmetic to Step 1's real
   deliverable (the `.avt`), but the asymmetry isn't documented anywhere.

## `product_ingestion/` (Step 2 — garment ingestion)

1. **`clo_block/clo_draft.py:564-575`**, called from `build()` — an
   implausible-sleeve-cap geometry check (ratio outside CLO's own reference
   band) only fires a Python `warnings.warn(...)`. It never reaches
   `panel_metadata.json` or `run_summary.json`, and
   `run_product_ingestion.py:244-253` hardcodes
   `"panels": {"status": "success"}` regardless. A genuinely unwearable
   sleeve (a defect this exact check exists to catch) ships as a clean
   success with no field anywhere recording it happened.
2. **`run_product_ingestion.py:244-253` and `:409-419`** — panel status is
   always `"success"`; `main()` returns exit code 0 even when
   `image_status == "failed"` (segmentation/colour/design entirely failed).
   Only an uncaught exception yields a non-zero exit.
3. **`texture_projection.py:98,192-247`** — `project_panel_texture()` writes
   a fully blank/transparent texture on two failure paths (`garment_bbox is
   None`, `findHomography` returning `None`), and the overall
   `TextureProjectionResult.success` stays `True` regardless, since it's
   set once at construction rather than per-panel.
4. *(minor, borderline)* **`view_selection.py:126-131`** — when CLIP finds
   no real front-view candidate, it silently falls back to whichever image
   scored highest on the front-view axis even if labeled `back_view` or
   `irrelevant`, tagged as `"best_available_front_candidate"`. At least this
   one is visible in `extraction_metadata.json`, unlike 1-3.

## `clo_vto/` (Step 3 — virtual try-on)

1. **`step_06_read_edges_and_slots.py:73-100`** — the front/back torso-panel
   slot-matching fallback's last tier scores any slot containing the
   substring `"front"`/`"back"` — which real CLO slot names like
   `Arm_Front_1_L` also contain. If the two earlier, more specific tiers
   both miss, the *torso* panel (not just a sleeve) can get matched to an
   arm slot, and the step still reports `"Matched slots"` success.
2. **`step_05_verify_patterns.py:184-226`** — the scale check that's
   actually derived from real applied geometry
   (`scene_length_ratio_est`) is advisory-only and returns `True` on
   failure; only the *less* accurate check (derived from static metadata,
   independent of the real applied scale) can hard-fail the pipeline. The
   check most likely to catch a genuine unit/scale bug can't stop anything.
3. **`step_10b_save_project.py:42-71`** — if CLO rejects the save, or the
   `.zprj` never lands on disk, the step prints a `[WARN]` and still
   `return True`. Since `pipeline.py` sets the top-level report `"status"`
   directly from the boolean step results, a run with **no project file at
   all** can still show `"status": "completed"`.
4. **`step_10_simulate.py:6-24`** — unconditionally `return True` whether
   the 150-step simulation actually finished draining or timed out after
   300s. No re-check before proceeding to save/export — a mid-simulation
   garment state could get saved/exported/textured and reported as a
   normal successful run.
5. *(lower severity)* **`step_07_arrange_patterns.py:42-45`** — per-piece
   `arrange_pattern()` results are printed but not checked before moving
   on; relies entirely on a later bulk substring-based verification
   (`"none" not in ...`) that's weaker than the discarded per-call result
   already available.

---

## What I'd actually chase first

Given everything found tonight, in order:

1. **`clo_workspace` finding #1** (fabric color/texture/graphic reporting
   success before the async call runs) — directly relevant to the
   unexplained CLO-viewport texture mismatch already open in doc 01. If
   this is the cause, it also implicates `step_08_apply_fabric.py`'s
   "queued" reports across the whole project, not just this one run.
2. **`clo_vto` #2** (the accurate scale check being advisory-only) — a
   real scale bug here would silently produce a garment that's the wrong
   size on every single run, not just an edge case.
3. **`product_ingestion` #1** (implausible-cap warning going nowhere) —
   already-built tooling exists to catch this; it's a small fix (write the
   flag somewhere a caller can see) rather than new logic.

Nothing here has been fixed. No pipeline run was done to reproduce any of
these, per instruction.
