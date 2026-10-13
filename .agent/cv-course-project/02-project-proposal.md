# 02 — Project Proposal (decided)

*Status: current*
*Decided: 2026-10-06*

Supersedes `01-paper-survey.md`'s Topic 2 recommendation — **Topic 3 (clothes → 3D / garment panel reconstruction)** was chosen instead.

---

## Title

**Image-to-Panel Garment Reconstruction: Extracting Colour, Design and Panel Geometry from Product Photographs for 3D Virtual Try-On**

## Description

Online fashion retail offers only flat product photographs, while 3D try-on requires garments built from flat sewing panels that drape over a body. This project develops a computer vision pipeline that bridges that gap. Given product images, the system segments the garment, selects usable views, extracts dominant colours and surface design, and infers the dimensions and shape of each panel. Current methods flatten garment appearance using a single global transform, which fails under drape, folds and perspective. We propose an improved texture projection stage that recovers flat panel appearance more faithfully, and demonstrate the result by draping reconstructed garments onto measurement-derived avatars.

---

## This is not a hypothetical pipeline — it already exists, in this repo

Every stage named in the description is a real, running module in `product_ingestion/`, documented in `.agent/saumy/10_03/03-step2-product-ingestion.md`:

| Description's stage | Real module |
|---|---|
| Segments the garment | `segmentation.py` (SAM2 → U²-Net fallback) |
| Selects usable views | `view_selection.py` (CLIP zero-shot) |
| Extracts dominant colours | `colour_extraction.py` (K-Means in LAB) |
| Extracts surface design | `design_extraction.py` (Canny + variance + FFT) |
| Infers panel dimensions and shape | `panel_generation_clo.py` / `clo_block` |
| Draping onto measurement-derived avatars | `clo_vto` Step 3 (physics simulation) |

## The proposed contribution's target is a confirmed, exact limitation in the current code

The description's central claim — *"current methods flatten garment appearance using a single global transform, which fails under drape, folds and perspective"* — is not a generic literature observation here. It's a precise description of what `product_ingestion/texture_projection.py` does today, verified directly in this repo:

```
1. Get panel polygon → compute axis-aligned bounding box.
2. Get garment bounding box from segmented RGBA.
3. Compute a homography: garment-bbox corners → panel-bbox corners.
4. Warp the feathered RGBA using the homography.
```

That's exactly one global transform per panel (bounding-box corners to bounding-box corners) — no accounting for drape, folds, wrinkles, or perspective distortion within the photographed garment. **This repo's own existing implementation is the baseline to beat, not just a paper's.** That's an unusually strong position for a course project: a real, running system, with a precisely identified weak point, and a direct way to demonstrate improvement — swap in the new projection stage and compare the output on the same real product photos already in `product_ingestion/output/`.

## What a stronger projection stage would need to do instead

Starting point for the actual technical approach, given the current single-homography weakness:
- **Per-region or non-rigid warping** instead of one global homography — e.g. a piecewise/mesh-based warp (triangulated correspondence between garment photo and flat panel, warped per-triangle) rather than four corner points controlling the whole panel.
- **Fold/drape-aware correspondence** — the photographed garment is never perfectly flat; a real improvement likely needs to detect or account for where the fabric folds over itself in the photo, rather than assuming the visible garment silhouette maps linearly onto the flat pattern.
- **Evaluation**: visually compare projected textures against the current single-homography output on the same cloth/size runs already generated (e.g. `c_001-s_001-007`, `c_001-s_002-002` — both already independently verified today for correct panel dimensions), plus the draped-on-avatar result once passed through Step 3.

## Relevant literature already surfaced in `01-paper-survey.md`'s Topic 3 section

- **TCSVT 2025/26** — *Deep Learning for 3D Fashion Design: A Survey From a Sewing-Pattern-Driven Perspective* (Luo, Qu, Zhao, Zhang, Yang) — the literature map for this entire topic; four-stage framework (representation → generation → reconstruction → editing).
- **IEEE Access 2026** — *QuantFit-VTON* — measurement-conditioned diffusion for predictable garment fit; closest published work to Mirra's core thesis.
- The three PDFs already saved in this folder (`Deep Learning for 2D Fashion Design: A Survey`, `Clothing-Agnostic Pre-Inpainting Virtual Try-On`, Lyu et al. 2025 on body-data-driven garment pattern construction) are the active reading list for this decided direction.

## Open items

- Narrow the literature list in `01-paper-survey.md` section 5 (Topic 3 tables) down to the 8-12 citations this specific proposal actually needs, now that the topic is fixed.
- Decide the exact technical method for the improved projection stage (piecewise warp vs. learned correspondence vs. something else) before writing the method section.
- Confirm whether the course wants a quantitative metric beyond visual comparison (e.g. a reconstruction error against a known-flat reference, if one can be constructed).
