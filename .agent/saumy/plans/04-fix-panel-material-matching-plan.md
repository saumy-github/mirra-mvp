# Plan 04: Fix GLB material-to-panel matching in the texture injection step

## Overview

`clo_vto/native_vto/step_12_texture_glb.py::_match_panel()` currently
decides which garment panel (front/back/sleeve-left/sleeve-right) a given
GLB material belongs to using substring keyword matching (e.g. `"left" in
name_lower`), with an unconditional "assume front_panel" fallback for
anything that doesn't match. This has two confirmed failure modes: avatar
shoe materials get matched to sleeves because their names happen to contain
"left"/"right", and every other non-garment material (face, hair, eyes,
body, arms, legs, teeth) falls into the fallback and gets painted with the
garment's front-panel texture — all while the step reports `texture
injected OK` for every one of them.

This plan replaces that logic with **exact name matching only** — a
material is assigned to a panel only if its name matches a known garment
material identifier exactly (no substring/partial/"contains" matching
anywhere). Any material that does not exactly match is left untouched, not
defaulted to any panel.

No code is written in this phase.

## Phases

### Phase 1: Establish ground truth for real material names

**Goal**: Know, with certainty rather than assumption, what CLO actually
names garment-panel materials versus avatar-body materials across real
exports — since the current bug exists partly because the matching logic
was written against assumed naming patterns rather than confirmed ones.

**Steps**:

1. Collect the full material list from the two GLB exports already
   produced tonight (the default-panels run and the `c_001/s_001` real
   ingestion run) and any other existing `simulation.glb`/
   `simulation_textured.glb` files already on disk under `clo_vto/output/`.
2. For each material name observed, classify it by hand as "garment panel"
   (should receive a texture) or "avatar body part" (should never be
   touched), using what we already know about this run's 17-material list
   as a starting reference.
3. Note whether garment-panel materials have a stable, predictable naming
   pattern across runs, or whether the name includes a run-specific
   numeric suffix (already observed: `FABRIC 1_437309` — the numeric part
   changed between runs). Confirm exactly which part of the name is stable
   and which part varies, since "exact match" needs to be defined against
   the stable part, not the full string including a per-run-unique suffix.
4. Confirm how many distinct garment materials CLO actually exports for a
   single 4-panel t-shirt in one run — this session's run showed only a
   single `FABRIC 1_...` entry for the whole garment, not four separate
   per-panel materials. If that's consistently true, "matching a material
   to one of four panels" may be the wrong framing entirely, and this
   needs to be understood before Phase 2's matching rule is designed.
5. Document all of this as a reference list (exact stable name patterns
   for garment materials, and exact known name patterns for avatar body
   materials) before writing any matching logic.

### Phase 2: Design the exact-match rule

**Goal**: Define precisely how a material is or isn't assigned to a panel,
with no ambiguity and no fallback-to-default behavior.

**Steps**:

1. Based on Phase 1's findings, define the exact rule for what counts as a
   match — e.g. an exact stable-prefix match against a fixed allow-list of
   known garment material identifiers, or an exact match against the
   material index recorded at import time in `piece_to_index` (already
   established earlier in the pipeline, at pattern-import time) rather
   than inferring from the material's name at all.
2. Explicitly define the "no match" behavior: a material that does not
   exactly match is **skipped and left completely untouched** — no
   texture write, no color write, and this must be visible in the step's
   own log output as a distinct outcome from "injected OK" (e.g. logged as
   "skipped — not a garment material"), not silently absent from the log.
3. Decide whether the existing index-order fallback tier (currently used
   for "numeric/opaque material names") should be kept, narrowed, or
   removed entirely — it must not be able to produce the same
   false-positive behavior as the keyword substring match it's replacing.
4. Confirm this rule change does not affect `step_08_apply_fabric.py`,
   which assigns fabric/color/texture during the CLO session itself using
   `piece_to_index` directly (a different mechanism, operating before
   export) — this plan is scoped only to the post-export GLB
   texture-injection step, not the in-CLO fabric application step.

### Phase 3: Verify against real data before calling it done

**Goal**: Confirm the new exact-match rule actually behaves correctly
against real exports, not just against the one run already seen tonight.

**Steps**:

1. Re-check the new rule against the material lists collected in Phase 1
   from multiple existing runs (not just one), confirming every
   avatar-body material is classified as "no match / skip" and every real
   garment material is classified as a correct, specific panel — by hand,
   before any code exists.
2. Identify what a passing result looks like in the step's log output
   (e.g. exactly 4 "injected OK" lines for a 4-panel default-panel run,
   and the remaining ~13 materials each explicitly logged as skipped) so
   there's a concrete, checkable definition of success ready before
   execution begins.
3. Flag to Saumy, before execution starts, if Phase 1 reveals that
   garment materials are not organized the way the current pipeline
   assumes (e.g. one merged material instead of four) — this would mean
   the fix is larger than a matching-rule change and needs a fresh
   decision before proceeding, per the standing rule to stop and report
   any such finding rather than proceeding past it.

## Dependencies

- Real GLB files already produced tonight (`clo_vto/output/...`) — no new
  pipeline run is required for Phase 1 or Phase 3's classification work.
- No CLO3D session needs to be running for this planning work; a live CLO
  session is only needed later, in the Execution Phase, if a fresh run is
  needed to confirm the fix.

## Expected Outcomes

- A documented, exact-match-only rule for assigning GLB materials to
  garment panels, with no substring/"contains" matching anywhere in the
  logic.
- A defined, logged "not a garment material — skipped" outcome for every
  material that isn't an exact match, replacing the current silent
  front-panel fallback.
- Confirmation (from Phase 1) of whether CLO exports one merged garment
  material or four separate per-panel materials, since this materially
  changes what "correct" looks like.
- No change to `step_08_apply_fabric.py`'s in-CLO fabric application
  mechanism.

## Future consideration (out of scope for this plan)

Saumy flagged: `step_08_apply_fabric.py` currently makes a separate REST
call to CLO per panel per property — 4 panels × (fabric preset + color +
texture) = 12 calls per run, each a network round-trip plus a CLO-side
queue-drain wait. This cost is paid once per person going through virtual
try-on, so it will scale directly with usage once the site has real
traffic, not just during pilot testing.

Worth investigating later whether this can be reduced — e.g. a single
batched command CLO processes as one operation instead of one call per
panel per property — but this is a separate performance question from the
matching-logic fix in this plan, and has not been scoped or investigated
yet. Not started.

## Manual Verification Checklist

- [ ] Saumy has reviewed the exact-match rule from Phase 2 before any code
      is written.
- [ ] Saumy has confirmed whether the "one merged material vs. four
      per-panel materials" question (Phase 1, step 4) changes the scope of
      this fix before execution begins.
- [ ] After execution, Saumy opens a `simulation_textured.glb` produced
      under the new logic in a viewer and visually confirms the avatar's
      face, hair, eyes, and body are untouched (original avatar
      appearance), and only the actual garment shows the injected texture.
- [ ] Saumy reviews the step's log output from that run and confirms every
      non-garment material is explicitly logged as skipped, not silently
      absent.
