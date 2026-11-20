# SAM 2 in Step 2: what we prompt it with, what goes wrong, how to improve it

*Status: current; includes a live experiment run on the repo's input images*
*Written: 2026-10-18*

---

## 1. What SAM 2 is (short)

SAM 2 (Segment Anything Model 2, Meta) cuts an object out of an image. It does not know what a "T-shirt" is. You tell it what you mean with a **prompt**: clicks on the object (positive points), clicks on things that are not the object (negative points), and optionally a box around it. It returns a few candidate masks with a predicted quality score (`iou_scores`) for each.

---

## 2. Are we giving it a prompt? Yes. Exactly this:

From `product_ingestion/step_02_0_segmentation.py`:

| Pass | Prompt | When |
|---|---|---|
| **1** | **1 positive point at the image centre** + **4 negative points at the four corners** | always |
| **2** | a **3 × 3 grid of positive points** over the middle 60% of the image + the same 4 corner negatives | only if pass 1's mask is under 5% or over 95% of the image |

- There is **no box** and **no text prompt**.
- SAM 2 returns **3 candidate masks**. We keep the one with the **highest predicted IoU score** (`scores.argmax()`).
- If both passes fail, **U²-Net** (`rembg`) runs without any prompt.
- The mask is then cleaned (`_clean_mask`): open/close, keep the largest piece, **fill holes**.

The model runs on **CPU**: the installed `torch` is `2.4.1+cpu`, so even with a GPU in the machine it is not used. One pass takes roughly 7-10 s per image.

---

## 3. What the experiment showed

I ran SAM 2 on `c_001`, `c_002` and `c_003` with different prompts (scratch script, nothing changed in the repo).

### 3.1 The three candidate masks and the one we pick

| Image | Candidate 1 (area, score) | Candidate 2 | Candidate 3 | We pick (highest score) |
|---|---|---|---|---|
| `c_001` (BOSTON tee) | 45.3%, 0.84 | 74.6%, 0.95 | **57.9%, 0.98** | candidate 3: the shirt only ✔ |
| `c_002` (plain pink tee, back view) | 35.7%, 0.67 | 65.6%, 0.88 | **65.2%, 0.99** | candidate 3: the shirt only ✔ |
| `c_003` (striped tee) | 24.9%, 0.56 | 86.1%, 0.93 | **66.5%, 0.96** | candidate 3: the shirt only ✔ |

The three candidates are roughly "a part", "the shirt plus more (arms)", and "the shirt". **Picking by the model's own score chose the right one on all three.** The point prompt itself is not the problem here.

### 3.2 Other prompts tried

| Prompt | `c_001` | `c_002` | `c_003` |
|---|---|---|---|
| Same points, single-mask mode (`multimask_output=False`) | 57.5% | 64.2% | 66.5% (same as pick) |
| Box = bounding box of the picked mask (a stand-in for a detector) | 57.8% | 64.9% | **86.3%, includes the arms** (wrong) |
| Loose box (3% margin around the whole image) | 57.9% | 64.0% | **86.4%, includes the arms** (score drops to 0.80) |

Lessons:

- **A box does not help by itself.** For `c_003` it makes the mask jump to the arms-included version. A box says "something here", not "just the shirt, not the person".
- Single-mask mode gave the same answer as picking from three, here.

---

## 4. The real problem is not the prompt: it is `_fill_holes`

The mask that reaches the next steps is **not** SAM 2's mask. It is bigger. I traced the cleanup step by step:

| Image | SAM 2 raw | after open/close | after largest-piece | **after `_fill_holes`** |
|---|---|---|---|---|
| `c_001` | 57.9% | 57.8% | 57.8% | 57.8% |
| `c_002` | 65.2% | 65.5% | 65.5% | **89.4%** |
| `c_003` | 66.5% | 66.5% | 66.5% | **84.8%** |

`_fill_holes` fills every background region that is not connected to the **top-left pixel**. On a tight crop, regions cut off by the image border (the gap beside an arm, the neck area, parts of the background) are not connected to that corner, so they are "filled" and become part of the garment.

On `c_003` the added area covers the **right arm, the background beside it and the neck opening** (the blue region in `images/c_003_fillholes_added.png`; the raw SAM 2 pick, shirt only, is `images/c_003_sam2_raw_best.png`).

### Why this matters

- **Colour is wrong.** `c_003` is a colour-block tee (white upper half with a stripe band and script text, dark-teal lower half) worn on a person in front of a dark background. The stored base colour is `#182c2a`, a darker teal than the fabric. The white half is skipped by the near-white rule in colour extraction, and the mask also took in arm and background pixels. *(Corrected 2026-11-20: an earlier version of this note called c_003 a red/pink tee, which was wrong.)*
- **Design detection and textures see the extra area**, since both use this mask.
- **The quality score cannot catch it.** `c_003` scores 0.82 and `c_002` 0.67 because only the coverage term varies (see `info-prod-ing.md`).
- **It does not affect `c_001`**, whose background is connected to the corner.
- The currently stored outputs were produced by the same code (I re-ran segmentation for `c_002` and `c_003` and got the identical areas 89.43% and 84.77%).

### Minimal fix (not applied)

Pad the mask with a 1-pixel background border **before** the flood fill, so every background region that touches any image edge is connected to the corner. Only truly enclosed holes remain fillable. A second safeguard: only fill holes smaller than, say, 2% of the garment area.

---

## 5. Options to make the prompting better

Ordered from cheapest to most work. Items marked (verified) were checked in a source or in the experiment above; the rest are design suggestions.

| # | Option | What it fixes | Evidence / notes |
|---|---|---|---|
| 1 | **Fix `_fill_holes`** (section 4) | wrong mask, wrong colour | verified by experiment |
| 2 | **Keep all 3 candidates and choose with rules**, not only the top score: reject masks that contain skin-coloured regions, prefer the one whose area is plausible | picks the arms-included mask when its score happens to be higher | SAM 2's own docs say multiple masks help for ambiguous prompts like one click (verified); on our 3 images the top score was right, so this is insurance |
| 3 | **Negative points on skin and trousers**: detect skin (YCrCb/HSV, as CaP-VTON does) or run a **clothes parser** (SegFormer clothes model trained on ATR, 18 labels incl. upper-clothes) and put negatives on arms, hands and legs | arms and legs in the mask | the clothes parser model exists on Hugging Face; its labels include "Upper-clothes" but no sleeve/neckline labels (verified from the model card) |
| 4 | **Positive points on the garment instead of the image centre**: take the centre of the parser's upper-clothes region, or several points across it | centre point landing on a print, a hand or an arm | the current 3 × 3 grid is only a fallback |
| 5 | **Drop or adapt the corner negatives** for tightly cropped images: use a negative only where the border colour matches the real background | corner negatives that are actually on the garment | design suggestion |
| 6 | **Box from a detector + a point prompt**: **Grounded SAM 2** (Grounding DINO with a text query such as "t-shirt" gives a box, SAM 2 gives the mask) | no manual prompting; works for other garment types | the repo README describes the box→SAM 2 chain and Grounded SAM is used for clothing segmentation in a hosted virtual try-on app (verified from search results); our experiment shows a box alone can include arms, so combine with option 3 |
| 7 | **Use the previous mask as `mask_input` for a refinement pass** with a few corrective clicks | small leftover errors | `mask_input` is a documented argument of the SAM 2 predictor (verified) |
| 8 | **Second opinion from another segmenter** and use their agreement as a confidence number: BiRefNet (MIT license), RMBG-2.0 (source-available, **non-commercial**), U²-Net (already installed) | silent failures; gives the missing quality gate | a refinement paper (SAMRefiner) reports that agreement with a coarse mask picks better masks than SAM's own predicted IoU; a vendor benchmark scored RMBG-2.0 above SAM 2 for background removal (vendor/Runflow figures, treat as indicative) |
| 9 | **Use SAM 2's own filters**: predicted IoU and stability score thresholds from the automatic mask generator | flag weak masks | verified in the SAM 2 code; SAMRefiner notes the IoU head alone is imperfect for specific objects, so calibrate on a few labelled images |
| 10 | **GPU build of torch** | 7-10 s per pass on CPU | the installed build is CPU-only (`2.4.1+cpu`). **Currently ruled out:** changing the torch version would break other dependencies (decided 2026-10-18) |
| 11 | **Crop to the garment and upscale small images** before segmentation | low-resolution inputs like `c_002` (434 × 460) | design suggestion; SAM 2 works at 1024 px internally |

**License note.** The Hugging Face page for `facebook/sam2-hiera-large` lists Apache-2.0. One 2024 blog post claims the Hiera backbone weights are non-commercial (CC BY-NC 4.0). The two conflict and I could not confirm Meta's current license files. Check the official repo's LICENSE before any commercial release.

---

## 6. Suggested order

1. Fix `_fill_holes` (a few lines, large effect).
2. Add a real gate: use predicted IoU + stability score + skin fraction + agreement with U²-Net, and stop or flag the run when it fails.
3. Add skin-aware negative points or a clothes-parser mask (option 3 or 4).
4. Evaluate Grounded SAM 2 and BiRefNet on the five cloths plus a small new set before replacing anything.

---

## 7. Sources

- SAM 2 image predictor, docstring on `multimask_output`, `box`, `mask_input`: https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py
- Hugging Face SAM 2 documentation: https://huggingface.co/docs/transformers/model_doc/sam2
- Grounded SAM 2 (Grounding DINO box → SAM 2): https://github.com/IDEA-Research/Grounded-SAM-2
- SAMRefiner (mask quality without ground truth): https://arxiv.org/abs/2502.06756
- Runflow background-removal benchmark: https://www.runflow.io/blog/background-removal-benchmark
- Bria RMBG-2.0 announcement (vendor claims, license): https://blog.bria.ai/brias-new-state-of-the-art-remove-background-2.0-outperforms-the-competition
- SegFormer B2 clothes model: https://huggingface.co/gj12138/segformer_b2_clothes
- Garment detector (RF-DETR-Seg on Fashionpedia): https://huggingface.co/resoa/garment-detector-seg
