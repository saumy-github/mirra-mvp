# 03 — Step 2 (Product Ingestion): what's built, what's verified, and what's next

*Status: current*
*Compiled: 2026-10-06*

Consolidates everything covered about Step 2 today — the explainer parts plus the deep-dive Q&A — into one reference, rather than scattered across `02-interesting-findings.md`. That file stays the chronological "interesting findings" log; this one is the settled picture for this specific step.

---

## What Step 2 actually does

Converts a 2D product photo into a real flat **sewing pattern** — not a 3D model directly. Output: DXF panel files (for a T-shirt: front, back, two sleeves), an edge manifest (which edge sews to which), color data, and any extracted logo/print — everything Step 3 needs to assemble and drape the garment on an avatar.

Two genuinely separate inputs feed into this, combined only at the final pattern-generation stage:
- **The photo** decides shape, color, and design.
- **MongoDB's `sizes` collection**, looked up by a required `size_id`, decides actual physical dimensions (`half_chest_width_cm`, `garment_length_cm`, etc.) — validated against the `cloths` collection's `size_ids` list. Size is never inferred from the image.

---

## What's built — the real pipeline, stage by stage

Entry point: `product_ingestion/run_product_ingestion.py`. Output layout: `product_ingestion/output/<cloth_id>-<size_id>-<run_number>/`.

1. **Segmentation** (`segmentation.py`) — cut the garment from its background. **SAM 2** (`facebook/sam2-hiera-large`) first, **U²-Net** via `rembg` as fallback. (Note: `.claude/current-roadmap.md` says "RMBG-1.4 with GrabCut fallback" — that's wrong/stale; verified directly against the code.)
2. **View selection** (`view_selection.py`, via `GarmentRouter`) — CLIP zero-shot classification. Currently picks **one** primary image and discards the rest, even when a cloth folder has several — this is the main current limitation (see Future Improvements below).
3. **Color extraction** (`colour_extraction.py`) — K-Means clustering in LAB color space, with real documented refinements: skin-tone pixel exclusion before clustering, adaptive K (2-8) via silhouette score instead of a fixed cluster count.
4. **Design extraction** (`design_extraction.py`) — logo/print extraction via Canny edge detection, with real refinements: brightness-adaptive thresholds (not fixed 50/150), a local-variance map to catch low-contrast logos, and an FFT-based detector for repeating all-over prints that edge detection alone misses.
5. **Pattern generation** (`panel_generation_clo.py`, wrapping `clo_block.CloTShirtDraft`) — combines the extracted shape/design with the size doc's real measurements to produce the actual dimensioned flat panels.
6. **Texture projection** (`texture_projection.py`) — warps the real segmented photo onto each flat panel's shape via homography, so panels carry the actual photographed fabric/print rather than a flat solid color. Output: `panels/textures/{panel}_texture.png`.

**No custom-trained models anywhere.** Every stage uses either a pretrained open-source model as-is (SAM2, U²-Net, CLIP) or a classical, non-learned algorithm (K-Means, Canny). Confirmed — no training/fine-tuning code exists in `product_ingestion`.

### DXF export

`panel_export_dxf.py`. Structure is driven by two hard constraints, not style choice:
- **One closed boundary polygon per panel, per file** — CLO3D's `ImportDXF` requires exactly this; anything else gets misread as internal baselines and imports zero patterns.
- **Units: cm internally, mm in the exported file** — matches what CLO expects for correct physical scale.
- **Curved edges preserve one-vertex/one-entity-per-logical-edge** (via LWPOLYLINE bulge values for simple arcs, or SPLINE entities for more precise curves — the exporter supports both) specifically so edge index `i` in the DXF stays aligned with edge index `i` in the seam manifest. Breaking that alignment would break Step 3's seam-matching.

---

## What's actually verified — hands-on, today, not from a trusted log

Per explicit instruction not to assume from a written record: independently opened real output DXF files with `ezdxf` and measured them directly.

- **`c_001-s_001-007`** (requested `half_chest_width=52.0cm`, `garment_length=71.0cm`): measured `front_panel.dxf` bounding box = `520.00mm × 710.00mm` = exactly `52.0cm × 71.0cm`.
- **`c_001-s_002-002`** (requested `half_chest_width=49.0cm`, `garment_length=68.0cm`): measured bounding box = `490.00mm × 680.00mm` = exactly `49.0cm × 68.0cm`.

**Exact match, to the millimeter, both sizes — and the two sizes produce genuinely different real geometry**, not a placeholder. This was verified by direct measurement, not by trusting any "matches"/"verified" field in the output.

**Important distinction found along the way:** `panel_metadata.json`'s `garment_measurements` block is *not* a verification record — it only logs what was requested as input. It makes no computed claim about the output. The match above is something checked fresh, not something the repo already asserted.

**A different, real computed check does exist in the same file** — the `seam_matching` block (`front_armhole_cm`, `sleeve_cap_cm`, `status: "matched"`). Traced to the actual code: `panels.py` computes `front_armhole_length`/`sleeve_cap_length` as real arc-length sums along the generated curve geometry itself (not copied from any input), and `panel_generation.py` computes the resulting ease and compares it to a configured target within tolerance, writing a genuine computed `matched`/`mismatched` status. This checks something different, though — internal pattern-making consistency (does the sleeve cap properly match the armhole it sews into), not "does the panel match the requested size."

**Testing posture is meaningfully better here than Step 1.** `product_ingestion/tests/` has three real test files — `test_panel_geometry.py`, `test_segmentation_quality.py`, `test_texture_projection.py`. The geometry suite tests the actual production code (`panel_generation_clo.py`) across multiple sizes (xs/m/xl, plus a deliberate outlier case), asserting closed non-self-intersecting polygons, correct edge counts, cap-ease percentages, shoulder-seam length matching, and correct seam-manifest wiring. (Step 1's `avatar_runtime`/`worker` has zero tests, by contrast — see `02-interesting-findings.md` section 8.)

---

## Known gaps (from the current-roadmap's own "known issues," cross-checked against the code today)

- Complex prints sometimes fail color separation.
- Very tight/loose fits sometimes under-segment.
- Unusual angles/poses in product photos cause misclassification.
- Design extraction thresholds need per-garment-type tuning.
- Only ~5-9 real garments have actually been run through the pipeline so far, against a stated target of 50-100 — nowhere near enough labeled data to train or meaningfully fine-tune a custom model, if that's ever pursued.
- The segmentation-quality gate (catch a bad segmentation before it silently corrupts every downstream stage) is identified as needed but not yet built.

---

## Future improvements discussed today

**Multi-image input (currently single-image only, confirmed in code — `select_primary_image()` picks exactly one photo and discards the rest even when several exist):**
- A real back photo would let the back panel reflect its *actual* shape instead of being assumed/mirrored from the front.
- A back-only design (e.g. a logo only printed on the back) is currently invisible to the whole pipeline — multi-image would fix this directly.
- Cross-validation becomes possible (color/shape agreement across views).
- The angle-classification groundwork already exists (`GarmentRouter`/CLIP) — extending it from "pick one winner" to "classify and route every image by angle" is a natural extension of existing code, not new infrastructure.
- The genuinely new problem multi-image introduces: **alignment** between views (matching scale/proportion across front and back photos before combining their shapes) — a real, well-studied but non-trivial computer vision problem.

**Design extraction specifically (flagged as the hardest, most important stage to improve):**
- Agreed it's the right stage to prioritize research on.
- Pushed back gently on jumping straight to training a custom model — the dataset isn't there yet (5-9 garments processed vs. a 50-100 target). Better pretrained options (newer logo-detection/print-segmentation models, used the same way SAM2 slotted in for segmentation) are the cheaper, faster lever to exhaust first, while the real garment dataset grows toward something that could actually support fine-tuning.

**General extraction-quality improvements, independent of multi-image:**
- Build the already-identified segmentation-quality gate (catch failure before it propagates silently).
- Add per-stage confidence scores, so a weak extraction can be flagged for review instead of shipping silently — same philosophy as Step 1's `measurement_verification.json`.

---

## Where deep learning could be used in this step

Stage by stage — where DL already does the work, where it probably shouldn't go, and where it's a real, currently-missing opportunity.

**Already deep learning:** segmentation (SAM2/U²-Net) and view selection (CLIP) — two of the six stages already are DL, not classical CV.

**Should probably stay out of deep learning:** pattern generation (`panel_generation_clo.py`/`clo_block`). This is deterministic, formula-driven geometry — verified today to produce millimeter-exact DXF output matching the requested size chart. A learned model here would trade an exact, auditable calculation for an approximate one, for something that must match a size chart precisely. Resist the instinct to "add ML" here specifically.

**The real, confirmed gap — fabric/material properties are never estimated at all.** Checked `clo_vto/native_vto/step_08_apply_fabric.py` directly: every garment gets `set_fabric(index, fabric_index=0)` — one hardcoded base fabric preset, always, regardless of what the garment actually looks like. Color and texture image are customized per garment; the physics (stiffness, weight, drape, stretch) never vary — a silk blouse and a denim jacket simulate with identical cloth physics today. This is arguably the single highest-value DL opportunity in the whole pipeline, and it's not a refinement — it's a missing capability. A model predicting an approximate fabric category from the photo (knit jersey / woven cotton / denim / silk-satin / fleece, etc.) — even a coarse classifier — could select a matching CLO fabric preset or estimate stiffness/weight/stretch more directly, instead of applying the same physics to everything. This directly undermines the core "realistic drape" promise as it stands.

**Where DL would genuinely improve an existing weak stage — design/logo/print extraction.** Already flagged as the weakest stage; the known failure mode (complex prints failing color separation) is exactly what a learned instance-segmentation model handles better than edge-detection heuristics. Pretrained fashion-specific segmentation models (real published research/datasets exist — DeepFashion2, Fashionpedia) are the cheaper first move, well before training anything custom, given the dataset-size problem already noted above. A further technique worth naming: generative inpainting to cleanly separate "base fabric" from "printed graphic" — removing the print to recover a clean base texture while keeping the print as its own overlay layer, which would also improve texture-projection accuracy (no ghosting from a front-only logo bleeding onto other panels).

**Smaller, real gains:**
- **Color extraction** — K-Means in LAB is solid for a dominant color but has no concept of lighting conditions. A learned color-constancy/white-balance correction step before clustering would improve robustness to inconsistent seller photography.
- **Texture projection** — mostly a deterministic geometric mapping (homography), appropriate as-is. The one DL opportunity: inpainting to fill texture occluded by a fold or the garment's pose in the photo — genuinely useful, but secondary to actually having a second (back) photo in the first place (see multi-image above).

**If prioritizing:** fabric-property estimation first (missing capability, undermines the core drape promise), design/print extraction second (already known-weakest, cheap pretrained options exist), then color-constancy and texture-inpainting as smaller incremental gains once those two land.

---

## Open / unresolved, worth a follow-up

- Whether `panel_export_dxf.py`'s bulge-encoded-LWPOLYLINE path or its SPLINE-entity path is the one actually used in a given production run appears to depend on curve complexity/configuration rather than being a single fixed choice — not fully traced end-to-end today; worth confirming precisely which path real production runs take by default.
