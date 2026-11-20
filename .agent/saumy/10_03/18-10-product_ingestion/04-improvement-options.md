# Step 2 (product ingestion): what the 03 note says, what is true now, and every option for each improvement

*Status: current; the options come from web research, the facts about our code from reading it and from running it*
*Written: 2026-10-18*

How to read this: **Part A** lists what the old note `03-step2-product-ingestion.md` says. **Part B** says what changed or was wrong (checked today). **Part C** is the full problem list. **Part D** gives, for each improvement, all the options I found, with a recommendation. Anything marked *(not verified)* is a claim I could not confirm from a source.

---

## Part A. Information extracted from `03-step2-product-ingestion.md`

### A.1 What the note says is built

1. Segmentation: SAM 2, with U²-Net as fallback.
2. View selection: CLIP zero-shot, picks one image and drops the rest.
3. Colour: K-Means in LAB with skin removal and adaptive K.
4. Design: Canny with adaptive thresholds, local variance, FFT for repeating prints.
5. Pattern generation: `clo_block` wrapped by the panel-generation step.
6. Texture projection: homography warp of the photo onto each panel.

Other statements: no custom-trained models anywhere; DXF has one closed polygon per panel, mm units, one edge per logical edge so edge indices match the seam manifest; two sizes were measured and matched the request to the millimetre; `panel_metadata.json`'s measurements block only records the request, while the `seam_matching` block is a real computed check; there are three real test files.

### A.2 Known gaps the note lists

1. Complex prints sometimes fail colour separation.
2. Very tight or loose fits sometimes under-segment.
3. Unusual angles and poses cause misclassification.
4. Design-extraction thresholds need per-garment-type tuning.
5. Only 5-9 real garments have been run, against a target of 50-100.
6. The segmentation-quality gate is not built.

### A.3 Improvements the note proposes

| # | Improvement | Priority the note gives |
|---|---|---|
| 1 | **Multi-image input** (real back photo, back-only designs, cross-validation, view alignment) | high, main limitation |
| 2 | **Design/print extraction** with better pretrained models (Fashionpedia, DeepFashion2, logo/print segmentation) before any custom training | second |
| 3 | **Segmentation-quality gate** and **per-stage confidence scores** | general quality |
| 4 | **Fabric-property estimation** (the fabric preset is hard-coded to index 0, so every garment simulates with the same physics) | **first** |
| 5 | **Colour constancy / white balance** before clustering | smaller gain |
| 6 | **Inpainting** to separate print from base fabric, and to fill occluded texture | smaller gain |
| 7 | Keep pattern generation out of deep learning (it is exact and auditable) | design decision |
| 8 | Open item: which DXF path (bulge polylines or splines) production actually uses | open question |

---

## Part B. What is out of date or wrong in the note (checked today)

| Statement in the note | What is true now |
|---|---|
| Files named `segmentation.py`, `view_selection.py` and so on | Renamed to `step_01_0_...` through `step_06_0_...` (see `01-file-numbering-plan.md`) |
| DXF exporter is `panel_export_dxf.py` (open question about bulge vs spline) | **Resolved.** The production exporter is `clo_block/step_05_3_clo_dxf_writer.py`, which writes DXF R12 (`AC1009`) **POLYLINE** entities on numeric layers. `panel_export_dxf.py` is unused and now lives in `legacy/` |
| "Segmentation-quality gate identified as needed but not yet built" | **Half built.** `segmentation_quality.json` is written, but nothing acts on it, and two of its three terms are constants (sharpness always 1.0, hole count always 1) |
| Output layout `output/<cloth>-<size>-<run>/` | Now nested `output/<cloth>/<size>/<run>/` (flat folders are old runs) |
| Panel generation "combines the extracted shape/design with the size doc" | Step 5 uses **only** the size row; the photo plays no part in the shape |
| "Fabric hard-coded to preset 0" | Still true, and worse: all four pieces share that one fabric, so per-piece textures overwrite each other (`02-graphic-overlay-finding.md`) |
| CLIP picks the primary image | **CLIP has never loaded**; every run used the first image (cause below) |

---

## Part C. Consolidated problem list

**New bugs found today (high value, cheap to fix)**

| # | Bug | Where | Effect |
|---|---|---|---|
| 1 | **`_fill_holes` swallows background and arms** on tight crops | `step_02_0_segmentation.py` | `c_002` mask grows 65% → 89%, `c_003` 66% → 85%; colours are wrong (`c_003`, a white and dark-teal colour-block tee, stored base `#182c2a`, a darker teal; the white half is ignored). Details: `03-sam2-prompting.md` |
| 2 | **CLIP model fails to load** (torch 2.4.1 is older than 2.6; the error is hidden by `except Exception`) | `step_01_0_view_selection.py`, `step_01_1_garment_router.py` | always the first image |
| 3 | **`_load_design_type` reads the wrong JSON key** | `clo_vto/.../step_08_apply_fabric.py` | the graphic branch never runs |
| 4 | **`set-fabric-graphic` is not a decal**, and all pieces share fabric 0 | CLO plugin and step 8 | textures overwrite each other (`02-graphic-overlay-finding.md`) |
| 5 | **Quality score is almost constant** and never gates | `step_02_0_segmentation.py` | silent failures |
| 6 | **Black shirt + coloured logo may get the logo colour as base colour** (from reading the code) | `step_03_0_colour_extraction.py` | wrong base colour |

**Everything in A.2** also remains open.

---

## Part D. Improvements and all the options for each

For each area: what we have, the options, and a recommendation.

### D1. Fix the bugs first (no research needed)

| Bug | Fix |
|---|---|
| `_fill_holes` | pad the mask with a background border before flood fill; also only fill holes below a small area fraction |
| CLIP load | ~~upgrade torch to 2.6 or later~~ **ruled out (decided 2026-10-18): the upgrade would break other dependencies**. Remaining options: load the safetensors weights, which on the Hub exist only in an **unmerged pull request** of `openai/clip-vit-base-patch32` (main has only `pytorch_model.bin`), or drop CLIP for a newer model (D3). Also stop swallowing the exception: log it |
| design_type key | read `data["design"]["design_type"]` **only together with a decision on the CLO graphic problem** (`02-graphic-overlay-finding.md`) |
| quality score | replace constant terms with informative ones (D2) |

*Torch constraint:* the installed build is `2.4.1+cpu`, so SAM 2 runs on CPU (about 7-10 s per pass). **Do not upgrade torch**; it would break other dependencies. Any CLIP fix or model swap must work on torch 2.4.1, so prefer weights that ship as safetensors (they are not affected by the `torch.load` restriction).

### D2. Segmentation-quality gate and confidence scores

Goal: stop or flag a run when the cut-out is bad, and record how sure each stage is.

| Option | How | Notes |
|---|---|---|
| **SAM 2 built-in scores** | predicted IoU and **stability score** (how much the mask changes when the threshold moves); the SAM 2 automatic mask generator exposes both as thresholds | cheap; the SAMRefiner paper says the IoU head alone is imperfect for specific objects, so calibrate thresholds on labelled images |
| **Agreement between two segmenters** | IoU between the SAM 2 mask and a U²-Net or BiRefNet mask | SAMRefiner reports agreement with a coarse mask ranks masks better than predicted IoU |
| **Content checks on the mask** | skin-pixel fraction inside the mask, mask touches the border, left-right symmetry, plausible area range (the current 5-95% is very wide) | trivial to compute; would have flagged `c_003` |
| **Clothes-parser overlap** | share of the mask that a parser labels as upper-clothes | needs a parser model (D5) |
| **Vision-language model check** | ask a VLM "does this mask show only a T-shirt?" | most flexible, costs per call |
| **Human review queue** | below a threshold, send to a person | simple; needed anyway for new garment types |

Recommendation: content checks + SAM stability/IoU + agreement with one other model, written into `run_summary.json` as a `confidence` block, with a hard stop below a threshold.

### D3. View selection (replace or repair CLIP)

| Option | Notes |
|---|---|
| **Repair CLIP** (torch ≥ 2.6) | smallest change |
| **SigLIP 2** | newer image-text model, loads through the same zero-shot pipeline; reported better general zero-shot scores than older models, but I found no product front/back benchmark *(not verified for our task)* |
| **Vision-language model** (a chat model with vision) | can answer "front, back, side, detail close-up, flat-lay, model photo", can flag unusable images; costs per call |
| **Rule-based cues** | detect a neck opening shape (front neck is lower than back neck), tags or labels, face visible | cheap extra signal; our own `clo_block` knows front/back neck depths |
| **Train a small classifier** | needs labelled front/back photos | worth it only after the dataset grows |

### D4. Multi-image input (front + back) and view alignment

Today `select_primary_image()` keeps one image. The pieces needed:

| Piece | Options |
|---|---|
| **Classify every image by view** | D3; keep best front, best back, side shots |
| **Use the back photo for the back panel's texture and for back-only prints** | cheapest win: the same segmentation, colour and design steps run on the back photo, then step 6 projects it onto `back_panel` instead of a solid colour |
| **Align views** (so front and back have the same scale and landmarks) | (a) bounding-box normalisation (what step 6 does now); (b) **garment landmarks**: DeepFashion2 defines 294 keypoints over 13 clothing classes, and landmark detectors were built on it (the 2020 challenge winner reached 0.59 AP; DeepMark reached 0.58 at 17 FPS on a phone), which gives neckline, shoulder, hem and sleeve points for a homography or thin-plate-spline warp; (c) match a segmentation-based silhouette |
| **Infer the missing back from the front** | Panelformer exploits left-right symmetry of panels to estimate occluded ones (WACV 2024); a useful idea for hidden parts |
| **Multi-view reconstruction models** | **ReWeaver** (CVPR 2026) reconstructs patterns from sparse multi-view photos (its example uses as few as four views, so it is not a two-photo front/back method); Dress-1-to-3 generates extra views with a multi-view diffusion model and refines the pattern with a differentiable simulator |
| **Back shape from the back photo** | would only help if we move away from "size row decides shape"; not recommended while measurements are the source of truth |

Recommendation: classify every image, use the back photo only for **colour, print and texture** of the back panel. Skip shape reconstruction.

### D5. Design, logo and print extraction (the weakest stage)

Current method: Canny + local variance + FFT, filled-contour crop. Known results: BOSTON crop is rough and loses the small "Leotude" script (`info-prod-ing.md`).

| # | Option | What it gives | Notes and caveats |
|---|---|---|---|
| 1 | **Fix the mask first** (D1) | removes arm and background from the area searched | mandatory before judging anything else |
| 2 | **Colour-distance segmentation** inside the garment: mark pixels far (in LAB) from the base colour as "design" | clean letter shapes for flat prints; trivial to build; reuses step 3's clusters | fails for tone-on-tone prints (like the embossed script on `c_003`) |
| 3 | **Open-vocabulary detector + SAM 2**: Grounding DINO with a prompt such as "logo", "graphic" or "text" gives a box; SAM 2 turns it into an exact mask | detects an arbitrary print without a fixed class list | one source describes a project that used the prompt "logo" this way; none tested t-shirt prints, so test on ours *(not verified for t-shirts)*; alternatives: OWLv2, Florence-2 |
| 4 | **OCR for text prints**: Florence-2 `<OCR_WITH_REGION>`, or PaddleOCR (DBNet detector plus recognizer) | text content and boxes (also lets us re-render the text crisply) | Florence-2 resizes to 768 × 768 so small text is lost; PaddleOCR's "artistic text" score is its weakest (0.673 on the v5 detector model card); neither was tested on shirts |
| 5 | **Garment instance/part segmentation** (Fashionpedia-trained RF-DETR-Seg, 46 classes, includes collar, lapel, sleeve, neckline; or the SegFormer ATR clothes model, 18 labels) | clean garment and part masks; useful for the mask (D2) and for knowing where the neckline and sleeves are | I did not find a "print" or "logo" class in these *(not verified)*, so they help with the mask, not the graphic |
| 6 | **Learned print-vs-fabric segmentation** | separates print from fabric, folds and shadows; a 2025 cascaded method does SAM-style separation, then multi-class segmentation of print elements | research code from a screen-printing group; not shirt-specific; needs evaluation |
| 7 | **Inpaint the print away** to recover a clean base fabric, then keep the print as its own layer | base texture without ghosting; per-layer control | **LaMa** is fast and conservative on uniform backgrounds; **Stable Diffusion inpainting** can invent unrelated content on plain textures (reports from users); mask a margin around the print |
| 8 | **Intrinsic decomposition** (Marigold IID: albedo, roughness, metallic or albedo, diffuse shading, residual) | removes shading and wrinkles so colours and print are closer to the true fabric | model card license is CreativeML Open RAIL++-M; resolution about 768 px; not tuned for garments *(not verified for garments)* |
| 9 | **FabricDiffusion** (SIGGRAPH Asia 2024, CMU and Google) | turns one clothing photo into a flat **tileable** texture plus normal, roughness and metallic maps, handles prints and logos, rectifies distortion | solves the "swatch" texture problem in CLO (D6); code on GitHub, last updated March 2025; heavy diffusion model |
| 10 | **Vectorise the graphic** (trace to a vector) | resolution-independent logo, small file | separate tool step |

Recommendation: 1, then 2 for flat prints, add 3 (+ 4 for text) for the cases 2 cannot handle; keep 7 and 9 as the texture-quality upgrade.

### D6. Texture projection

| Option | Notes |
|---|---|
| **Keep the homography** for plain tees | cheap, deterministic |
| **Landmark-based warp** (D4) | better panel alignment for sleeves than "left 35% / right 35%" |
| **Tileable PBR texture** (FabricDiffusion) | the right object for CLO's swatch-style texture call (`02-graphic-overlay-finding.md`) |
| **Per-piece fabric + Unified mapping + real graphic placement through the CLO SDK** | the SDK (v2026.1.224) declares `AddFabric`, `AssignFabricToPattern`, `SetTextureMapping(Repeat/Unified)`, `AddGraphicStyleFromImageFile` and `AddGraphicStyleToPatternV2`; our plugin exposes none of them yet. This is the cleanest fix and does not need a new model; see section 5 of `02-graphic-overlay-finding.md` |
| **Inpaint occluded regions** (folds, poses) with LaMa | secondary until a back photo exists |
| **Place the print as its own layer at a measured position and size** | today the graphic is pasted at 30% of the panel width and 35% down regardless of the real print |

### D7. Colour extraction

| Issue | Options |
|---|---|
| **Wrong base colour on a black shirt with a coloured logo** (code reading) | pick the base cluster by **where its pixels are** (e.g. the largest cluster in the eroded core of the garment) instead of by lightness cutoffs; use a clothes-parser region |
| **Lighting and white balance** | (a) classical grey-world or shades-of-grey; (b) use the photo's white background as a reference (cheap, many product photos have one); (c) learned estimators such as **FC4** (CVPR 2017, confidence-weighted pooling), noting learned methods tend to be tied to one camera sensor; (d) diffuse/shading decomposition (Careaga and Aksoy 2024) for per-pixel white balance |
| **Only one colour reaches CLO** | colour-blocked garments (`c_003` has a white upper half with stripes and a dark-teal lower half) lose information; store the palette per region (e.g. per panel area) and apply per piece once the shared-fabric issue is solved |
| **Skin pixels** | replace fixed HSV ranges with YCrCb detection (as in CaP-VTON) or a parser |

### D8. Fabric-property estimation (the note's top priority)

Today: `set_fabric(index, fabric_index=0)` for every piece. CLO's physical properties include stretch (warp and weft), bending, shear, buckling, density (weight), thickness and friction. I found **no published numeric preset values** for cotton, denim or silk, and a third-party guide on building a CLO fabric library recommends measuring real swatches.

| Option | How | Notes |
|---|---|---|
| **A. Text metadata → preset** | add a `fabric` or composition field to the `cloths` document (e.g. "100% cotton jersey") and map it to a CLO preset by a rule table | cheapest and usually most reliable when the seller states it; needs a human-made mapping |
| **B. Photo fabric classifier** | image classifiers exist: TextileClass-7 (7 classes incl. cotton, denim, silk), TextileNet (760,949 images, 33 fibre and 27 fabric labels; ResNet50 and ViT baselines) | fine distinctions (cotton vs polyester, satin vs silk, linen vs polyester) are hard; photos of garments are not swatches |
| **C. Vision-language model** zero-shot | ask for fabric type and weight class | needs checking against ground truth; no benchmark found for garment photos |
| **D. Image2Garment** (arXiv, Jan 2026) | a fine-tuned VLM infers material composition and fabric attributes; a lightweight model maps them to **physical parameters**; new datasets FTAG and T2P | closest to a full solution; trained on a small measurement set; simulator not named on the abstract page |
| **E. Single-image stiffness** (PhysGS, 2025) | predicts bending-stiffness fields from one RGB image; reported to beat GPT-4V/GPT-5 prompting on stiffness | very new, not garment-specific |
| **F. From drape or depth** | PhySNet (depth images beat RGB variants for garments), Feng et al. SIGGRAPH Asia 2022 (regress bending stiffness from drape features, 618 measured fabrics) | needs depth or a drape test, not a product photo |
| **G. Simulation-in-the-loop** | fit parameters so a simulated drape matches an observation (Bayesian differentiable physics, CVPR 2024) | needs an observation of real drape |

Recommendation: start with **A** (cheap, immediately removes the "everything is the same fabric" problem), add **B/C** as a fallback when no text exists, track **D** as the research path. Also fix the shared-fabric constraint, or per-piece physics cannot differ anyway.

**SDK facts that make A concrete (read from `JFABSpec.json`, not yet tested):** a fabric file can carry a `mapPhysical` block (stretch, shear, bending, buckling, density, thickness, friction, internal damping) and an `enFabricType` label with 17 values: Default, Silk, Cotton, Wool, Denim, Leather, Cashmere, Satin, Spandex, Rayon, Linen, Taffeta, Polyester, Terrycloth, Flannel, Burlap, Rubber. `AddFabric` and `ChangeFabricWithJson` can load such a file. So (1) a classifier or a text rule only has to output one of those 17 labels, and (2) the physics values can be written into a per-cloth `.jfab` and applied through the SDK. Still unknown: whether `enFabricType` alone changes the numbers, and what values are right for each type. Details: `02-graphic-overlay-finding.md`, section 5.3.

### D9. Inpainting and generative help (the note's smaller gains)

See D5 items 7-9 and D6. Short summary: LaMa for plain-region removal, Stable Diffusion inpainting only when new content is needed (risk of inventing detail), FabricDiffusion for texture recovery.

### D10. Shape from the photo (optional; the note says keep pattern generation non-DL)

Agreed with the note for **dimensions**. For **style attributes** (neckline type, sleeve length class, hem), a photo could choose among blocks. Options: **Sewformer** (two-level Transformer, SewFactory 1M images), **Panelformer** (symmetry for occlusion), **AIpparel** (CVPR 2025, 120,000 garments, image and text), **GarmentCode** + **ChatGarment** (language model edits parameters). Use as a classifier of style, not as the source of dimensions.

### D11. More data (5 cloths today)

| Source | Notes |
|---|---|
| **GarmentCodeData** | 115,000 synthetic garments with patterns and 3D; procedural, from limited templates; license not stated on the pages I read |
| **SewFactory / DressCodeData / GarmentX** | listed in Paper 1 |
| **Fashionpedia** (CC BY 4.0), **DeepFashion2** | clothing images with masks and landmarks |
| **Dress Code dataset** | public on GitHub (>50k image pairs, tops, bottoms, dresses) |
| **Own catalogue** | more cloths with the metadata fields we need (fabric, size chart); legal and licensing care for scraped photos |

---

## Part E. Suggested sequence

1. **Bugs (D1):** `_fill_holes`, CLIP load and logging. Hours.
2. **Gate (D2):** content checks + stability/IoU + agreement.
3. **Look at CLO** (`02-graphic-overlay-finding.md`) and decide the texture/graphic strategy.
4. **Fabric (D8-A):** a fabric field and a mapping table.
5. **Design extraction (D5:** colour-distance + open-vocabulary + OCR).
6. **Multi-image (D4):** back photo for back texture.
7. **Research track:** FabricDiffusion, Image2Garment, SigLIP 2.

---

## Sources

- SAM 2 predictor: https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_image_predictor.py
- SAMRefiner: https://arxiv.org/abs/2502.06756
- CVE-2025-32434 (torch.load): https://nvd.nist.gov/vuln/detail/CVE-2025-32434
- CLIP safetensors in an unmerged PR (Space commit): https://huggingface.co/spaces/0xZohar/object-assembler/commit/edbbf0058a44fbcdec80cbd459b17acce87dd0d6
- SigLIP 2: https://arxiv.org/abs/2502.14786
- DeepFashion2 landmark winner (Lin 2020): https://arxiv.org/abs/2005.00419
- DeepMark (WACV 2021): https://openaccess.thecvf.com/content/WACV2021/papers/Sidnev_DeepMark_Real-Time_Clothing_Detection_at_the_Edge_WACV_2021_paper.pdf
- Panelformer: https://openaccess.thecvf.com/content/WACV2024/html/Chen_Panelformer_Sewing_Pattern_Reconstruction_From_2D_Garment_Images_WACV_2024_paper.html
- Sewformer: https://arxiv.org/abs/2311.04218
- AIpparel: https://arxiv.org/abs/2412.03937
- Dress-1-to-3: https://arxiv.org/abs/2502.03449
- ReWeaver: https://arxiv.org/abs/2601.16672
- FabricDiffusion: https://arxiv.org/abs/2410.01801
- Image2Garment: https://arxiv.org/abs/2601.09658
- PhysGS: https://arxiv.org/abs/2511.18570
- PhySNet: https://arxiv.org/abs/2112.10727
- FC4 colour constancy: https://openaccess.thecvf.com/content_cvpr_2017/papers/Hu_FC4_Fully_Convolutional_CVPR_2017_paper
- Marigold IID model card: https://huggingface.co/prs-eth/marigold-iid-appearance-v1-1
- Garment detector (Fashionpedia): https://huggingface.co/resoa/garment-detector-seg
- SegFormer clothes (ATR): https://huggingface.co/gj12138/segformer_b2_clothes
- TextileClass-7: https://data.mendeley.com/datasets/m2h53zr39s
- GarmentCode and GarmentCodeData: https://github.com/maria-korosteleva/GarmentCode and https://igl.ethz.ch/projects/GarmentCodeData/
- Dress Code dataset: https://github.com/aimagelab/dress-code
- CLO fabric section of the help centre (stretch, bending, buckling definitions): https://support.clo3d.com/hc/en-us/sections/115000714287-Fabric
