# 05 — Logo/design extraction methods, and getting a detected logo into 3D

*Status: current*
*Compiled: 2026-10-06*

Three parallel research passes: academic methods for logo/print extraction specifically from garments, general object-detection architectures assessed for fit on that same sub-task, and — a different question — how a detected 2D logo actually gets correctly recreated on a 3D garment. Builds on `04-dataset-research.md`; doesn't repeat its dataset tables.

---

## Part 1 — Papers on logo/design extraction specifically from clothing

| Paper | Venue/Year | Method | Key finding | Link |
|---|---|---|---|---|
| **DeepIron** | **Eurographics / Computer Graphics Forum 2024** (correction — `04-dataset-research.md` listed this as a 2023 arXiv preprint; it's since been published at Eurographics/CGF 2024) | "Texture Unwarper" — latent-space mapping between a warped (photographed) garment image and its unwarped flat texture | Recovers flat garment texture from a single photo despite body-shape deformation, pose, and self-occlusion from wrinkles — closest existing method to Mirra's actual problem | [arXiv](https://arxiv.org/pdf/2310.15447) |
| Fashion Product Classification (w/ Adidas) | Industry study | Fine-tuned VGG19 for logo/stripe/color classification | 94.4% accuracy at real production scale (~20,000 articles/season) — evidence a CNN approach works in practice, though this is classification, not pixel-level segmentation | [source](https://www.academia.edu/90895511/Fashion_Product_Classification_through_Deep_Learning_and_Computer_Vision) |
| Segmentation task for fashion/apparel (DeepFashion2-based) | Conference, 2022 | Mask R-CNN vs. Faster R-CNN compared head-to-head | **Instance segmentation beats box detection by ~20%** for clothing localization — direct evidence for choosing a segmentation-style model over a detection-style one here | [arXiv](https://arxiv.org/pdf/2006.11375) |
| Logo/brand detection for textile sorting (thesis) | NCI thesis, 2023-2024, not peer-reviewed | Fine-tuned YOLOv5 vs. off-the-shelf logo models | Fine-tuning beats generic pretrained logo detectors for this kind of applied task — lower-rigor source, but a concrete data point | [NCI repository](https://norma.ncirl.ie/5815/) |

**Correction to make in `04-dataset-research.md`:** its DeepIron entries (headline finding section and dataset table) should be updated from "2023 paper" to "Eurographics/CGF 2024" — done below in this same session.

---

## Part 2 — General object detection, assessed for fit on logo-on-garment segmentation

| Architecture | Core approach | Fit for logo-on-garment segmentation | Data requirement | Link |
|---|---|---|---|---|
| Mask R-CNN | Region proposals + per-region pixel mask | Poor — needs labeled data Mirra doesn't have (only TopLogo-10, 700 images) | Heavy fine-tuning | [arXiv](https://arxiv.org/abs/1703.06870) |
| YOLO-World | Real-time open-vocabulary detection | Partial — fast, zero-shot by text prompt, but outputs boxes, not the precise masks needed for 3D placement | Zero-shot | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Cheng_YOLO-World_Real-Time_Open-Vocabulary_Object_Detection_CVPR_2024_paper.html) |
| Grounding DINO | Transformer open-set detection from free text | Partial — zero-shot localization ("a printed logo on a shirt"), still needs a segmenter after it | Zero-shot | — |
| SAM2 | Promptable segmentation, no detection of its own | Precise masks, but needs to be told *where* to look — already used in Mirra's Stage 2 | Zero-shot, given a prompt | Already in the pipeline |
| **Grounded SAM(2)** | Grounding DINO detects the region by text → SAM(2) turns it into a precise mask | **Best proven fit** — zero-shot, no logo-labeled dataset needed, reuses Mirra's existing SAM2 investment, 48.7 mean AP on the SegInW zero-shot benchmark | Zero-shot | [arXiv](https://arxiv.org/pdf/2401.14159) |
| **SAM 3** (Meta, Nov 2025) | Unified "promptable concept segmentation" — detects, segments, and tracks a described concept in one model | Best newest fit — could replace the two-model Grounded-SAM pipeline entirely; less battle-tested since it's very recent | Zero-shot | [Ultralytics docs](https://docs.ultralytics.com/models/sam-3) |

**Recommendation:** prototype **Grounded SAM 2** first (mature, documented, reuses the SAM2 family already in Mirra's pipeline) as the zero-shot replacement for today's Canny-based design extraction, with **SAM 3** as a fast-follow evaluation once it's more established. Both sidestep the dataset gap identified in `04-dataset-research.md` (no large real dataset has logo-level pixel ground truth) by not needing a labeled logo dataset at all.

---

## Part 3 — If we detect the whole logo, how do we recreate it in 3D?

This turned out to be two separate problems, and Mirra already has code for both — one done correctly, one with a confirmed bug.

### The placement mechanism already exists, and is the standard correct technique

Placing a 2D image onto a 3D mesh at a specific position/orientation/scale is a mature, solved graphics problem: a **UV-mapped texture decal**. A projection maps the 2D image onto the mesh's UV coordinates, and the engine alpha-blends it over the base material. This is exactly what `clo_vto/step_08_apply_fabric.py`'s `ctx.client.set_fabric_graphic(front_idx, graphic_path, u=0.5, v=0.35, scale=1.0)` call already does — native, correct, standard technique. **3D placement is not the open problem here.**

### Confirmed directly in the code: the logo is currently applied twice

- `product_ingestion/texture_projection.py` (`_composite_graphic`, called at line 131-132) bakes the extracted graphic into the panel's flat texture PNG **unconditionally**, whenever a graphic exists on the front panel — no `design_type` check.
- `clo_vto/native_vto/step_08_apply_fabric.py` then applies that same baked-in texture via `set_fabric_texture` (step c) — **and separately** calls `set_fabric_graphic()` again (step d) whenever `design_type in ("logo", "text")`.
- The code's own comment for the `"pattern"` branch states: *"already covered by texture atlas — skipping graphic overlay"* — proving the double-application risk was known and deliberately guarded against for patterns. **The same guard was never added for `"logo"`/`"text"`.** So today, any logo or text design gets composited once as a flat texture bake and once again as a native 3D decal, at nearly the same position — likely a visible double-darkening/artifact, not a deliberate two-layer design.

**This should be fixed before anything else in this area** — it's a confirmed, cheap, mechanical fix (add the same skip condition `step_08` already uses for `"pattern"`), unrelated to any of the research above.

### The actual open problem: getting a clean, undistorted logo *before* placement

Once the double-application bug is fixed, the real unsolved piece is upstream of placement, not placement itself: the photo shows the logo at an angle, partially hidden by a fold, or distorted by drape — and nothing currently un-distorts it before baking/placing it. 2024-2025 virtual try-on literature names this directly as an open problem: geometry-based warping "preserve[s] garment texture detail" but "perform[s] poorly when garment self-occlusion occurs, which is common in daily life." No clean universal answer exists yet — the field splits three ways:
1. Most practical systems simply place what was detected and accept the gap/artifact.
2. Research systems increasingly use learned inpainting to hallucinate the occluded region — this is exactly DeepIron's approach (Part 1 above).
3. Nobody assumes logo symmetry as a general solution — logos aren't reliably symmetric.

**So: this is the real connection to the course project.** The project's decided contribution is already "region-aware/fold-aware texture projection" instead of one global homography — DeepIron-style texture unwarping for logos specifically is the same underlying problem, applied to the design layer rather than the whole garment's base texture. Solving the general case (Stage 7's proposed contribution) would substantially help this specific case too, rather than needing two separate solutions.

---

## Recommended next steps, in order

1. **Fix the logo/text double-application bug** in `step_08_apply_fabric.py` — cheap, mechanical, unrelated to any research above.
2. **Prototype Grounded SAM 2** as a zero-shot replacement for Canny-based design extraction (Stage 4) — no labeled logo dataset required.
3. **Treat logo un-distortion as the same problem as the course project's main contribution** (fold-aware texture projection, Stage 7) rather than a separate research thread — DeepIron is the key reference paper for both.
