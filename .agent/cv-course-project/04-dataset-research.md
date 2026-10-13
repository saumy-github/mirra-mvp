# 04 — Dataset Research: what would it take to train a model here?

*Status: current*
*Compiled: 2026-10-06*

Five parallel research passes, each covering a different angle: garment segmentation/design-extraction datasets, sewing-pattern-reconstruction datasets, texture/draping/UV datasets, virtual try-on benchmark datasets, and — separately — an honest inward-looking audit of what data Mirra's own repo actually has or could generate. Compiled here as one reference.

---

## The headline finding: two datasets came up independently across three separate research passes

**SewFactory / Sewformer** (SIGGRAPH Asia 2023, ACM TOG) and **GarmentCodeData** (ECCV 2024) were each surfaced independently by the sewing-pattern research pass, the texture/draping research pass, *and* the VTO-benchmark research pass — three agents, researching different angles, converging on the same two answers without being told about each other's findings. That's a strong signal these are genuinely the right starting point, not a coincidence of search terms.

- **SewFactory/Sewformer** — ~1,000,000 synthetic images, each paired with ground-truth sewing patterns, varied poses/body shapes. **Code, dataset, and a pretrained model are all publicly released** (`sewformer.github.io`). This is the closest existing published system to Mirra's exact project goal — "image → sewing pattern" — and is worth treating as a primary reference and a fine-tuning starting point, not just a dataset.
- **GarmentCodeData** — 115,000 synthetic garments, each with a real parametric sewing pattern (exact panel count, panel geometry, seam/edge correspondence), a 3D draped mesh, a UV map, segmentation labels, body measurements, and design parameters. The only dataset found with genuine panel-level *and* UV-level ground truth matching Mirra's task structure.

Both are synthetic, not real product photography — which matters, and is addressed below.

---

## Mapped precisely to Mirra's pipeline stages

Checking `product_ingestion/curve_config.py` directly surfaced an important nuance for this mapping. Stage 5 (pattern generation) actually splits into two different things:

- **Dimensions** — how big each panel is. Correctly, deterministically driven by the size chart. Already verified millimeter-exact. Not a target for any of these datasets or any model.
- **Style/shape** — how deep the neckline curves, how the armhole is shaped, overall silhouette. Confirmed **fixed template today**: `ArmholeConfig`'s `hollow_position_frac`, `hollow_depth_frac`, `shoulder_flare_frac` are hardcoded defaults (0.40, 0.18, 0.05), only clamped to safe bounds, never set differently per garment from the photo. Mirra cannot currently tell a v-neck from a crew-neck tee — it always generates the same curve shape, just scaled.

That distinction is exactly where each researched dataset group does or doesn't apply:

| Dataset group | Pipeline stage | What it would actually fix |
|---|---|---|
| DeepFashion2 / Fashionpedia / ModaNet / logo sets | Stage 2 (segmentation), Stage 4 (design extraction) | Better garment cutout, better logo/print detection |
| Sewformer / GarmentCodeData | Stage 5 — **style only, not dimensions** | Garments could vary in neckline/sleeve/silhouette instead of one fixed shape |
| CLOTH3D / DeepIron / Pattern-Coordinate Diffusion / synthetic CLO3D pairs | Stage 7 (texture projection) | The actual decided course-project contribution: fold-aware texture projection |
| VITON-HD / DressCode | None | Wrong task entirely — end-to-end image generation, not geometric reconstruction |

---

## Full findings by category

### 1. Garment segmentation / design (logo, print) extraction

| Dataset | Size | Labels | License | Relevance |
|---|---|---|---|---|
| DeepFashion2 | 491K images / 801K items | bbox, landmarks, seg masks, style/pose | Custom "Other" — verify terms | High: segmentation |
| Fashionpedia | 50.5K images | seg masks + 294 attributes | **CC BY 4.0** (cleanest license found) | High: segmentation; partial: design (attributes only) |
| ModaNet | 55K images (+1M weak) | polygon/pixel masks, 13 categories | Research-use | High: segmentation |
| iMaterialist (Fashion) 2019 | 50K images | instance seg + construction attributes | Kaggle competition terms | High: segmentation |
| LogoDet-3K | 158.7K images | logo bbox, 3,000 classes | Research-use | High: logo/print (generic, not garment-specific) |
| TopLogo-10 | 700 images | logo bbox, 10 apparel brands | Research-use | Low alone (too small), but the only garment-specific logo set |

No dataset combines garment segmentation *and* logo/print extraction in one set — design extraction would need a logo-detection dataset layered on a segmentation dataset, or Mirra's own photos annotated once volume grows.

**Real or synthetic — all real, unlike the Stage 5/7 datasets below.** DeepFashion2 and ModaNet are real consumer/street-fashion photos, Fashionpedia is sourced from Flickr and other free-license real images, iMaterialist is a real-photo Kaggle dataset, and both logo datasets are real photographed logos. This is the opposite situation from the pattern/texture datasets later in this document — no synthetic-to-real domain-gap problem exists for this part of the pipeline.

**The approach — pretrained models (including SAM2 itself) plus fine-tuning on these — is sound, with one clarification and one real caveat:**

- **Clarification:** SAM2 is already doing this kind of work, but for a different sub-task — it currently powers Stage 2 (segmentation), cutting the whole garment out from its background. Pointing a promptable model like SAM2 at the design/logo specifically (segmenting just the printed region on an already-segmented garment) would be extending that same idea into Stage 4 — a genuine, concrete improvement, not something already done.
- **Caveat — no large real dataset has actual logo-level ground truth.** DeepFashion2, Fashionpedia, ModaNet, and iMaterialist only label the *garment* (masks, boxes, general attributes). Fashionpedia's "has print"/"graphic" attribute is a coarse yes/no tag, not a pixel mask showing *where* the logo is. Real logo-specific annotation only exists in LogoDet-3K (158K images, but generic logos, not garment-context) and TopLogo-10 (garment-specific, but only 700 images / 10 brands). A real training approach here would need to combine pieces — general garment ability from the large datasets, logo-specific fine-tuning from TopLogo-10, general logo-detection ability from LogoDet-3K — rather than one dataset covering the whole sub-task, and would likely grow to include Mirra's own annotated photos over time as the real in-domain evaluation set.

### 2. Sewing pattern / panel reconstruction (most directly relevant to the decided project topic)

| Dataset | Size | Labels | License | Relevance |
|---|---|---|---|---|
| **GarmentCodeData** | 115,000 garments | Full parametric sewing pattern + 3D + UV | Check ETH research-collection page | **High** — only dataset with true panel-level ground truth at scale (synthetic) |
| **SewFactory + Sewformer** | ~1M images | Image + ground-truth sewing pattern | Public release | **Highest** — exact task match, pretrained model available |
| CLOTH3D | 2M+ samples | 3D clothed humans, **no pattern ground truth** | Public | Low — not usable for panel reconstruction |
| Dress-1-to-3 (SIGGRAPH 2025) | N/A — a pipeline, not a dataset | — | N/A | Technique reference only (builds on Sewformer); already excluded from citations as a conference paper |

### 3. Texture / draping / UV correspondence (for the fold-aware texture-projection contribution specifically)

**Real paired data (draped photo + flat ground-truth texture) is genuinely scarce** — the field's actual practice is training on synthetic simulation data instead, because real paired data essentially doesn't exist at scale. Multiple recent papers confirm this works:

| Dataset/Approach | Content | Size | License | Relevance |
|---|---|---|---|---|
| CLOTH3D/CLOTH3D++ | Synthetic draped renders + known UV/texture | 2M+ frames, 8K+ sequences | Academic request | **High** — free perfect pairs, includes T-shirts |
| DeepIron (Eurographics/CGF 2024) | Method solving this *exact* problem — infers original flat texture from a warped/wrinkled clothing image | N/A (paper, study for methodology) | N/A | **High** — closest prior art |
| Single View Garment Reconstruction via Pattern Coordinates (2025) | Trains *exclusively* on synthetic simulated cloth, reports generalizing to real photos with zero real training data | Not stated | N/A | **High** — direct evidence synthetic-only training is viable |
| Multi-Garment Net (MGN) | Real 3D scans + texture maps | 712 garments | Academic (MPI-INF) | Medium — real but garment-level, not panel-level |
| Deep Fashion3D V2 | Real multi-view + registered mesh + textures | 2,078 models / 563 garments | Request-based | Medium — real-world texture ground truth |

### 4. Virtual try-on benchmarks — checked and ruled out for this specific task

| Dataset | Size | Ground truth type | License | Fit |
|---|---|---|---|---|
| VITON-HD | 13,679 pairs | Person+garment+result images only — no panel/UV ground truth | CC BY-NC 4.0 (non-commercial — relevant since Mirra is commercial) | **Poor** |
| DressCode | ~53,000 images | Same — image-to-image only | Research use | **Poor** |
| Deep Fashion3D | 2,078 models / 563 garments | 3D mesh + multi-view, but **explicitly confirmed to exclude sewing patterns** in its own stated limitations | Research use | **Poor** despite looking relevant on the surface |

Standard VTO benchmarks are built for end-to-end image generation, not geometric reconstruction — the wrong category entirely for this project, confirming the sewing-pattern-specific datasets above are the right place to look instead.

### 5. What Mirra's own repo actually has — audited directly, not assumed

- **Real processed data is small.** 5 cloth folders exist (`c_001`-`c_005`), each with exactly **one** source photo. Only `c_001` has ever been run through the pipeline — **9 total runs, all one garment**, at 2 sizes. That's 1 distinct garment, not a dataset, by any standard (compare: DeepFashion2 ~800K images, CLOTH3D ~11K sequences).
- **Real-data-only is not viable** for training or meaningfully fine-tuning anything. Not a close call.
- **Synthetic generation via CLO3D splits into two tiers, with very different cost:**
  - **Available now, no new engineering:** `texture_projection.py`'s own docstring states "the panel polygon IS the UV space" — meaning the flat-texture-to-draped-mesh correspondence is already fully recoverable from an existing `Simulate()` + `ExportGLB()` call, since you author the flat texture yourself. Running the existing avatar + VTO pipeline repeatedly with varied synthetic flat textures on known panel shapes would produce free, exact (flat texture ↔ draped 3D surface) pairs today — directly useful training data for the texture-projection sub-task specifically.
  - **Would need new work:** CLO's actual photorealistic render engine (V-Ray, found in `02-interesting-findings.md` section 9) is **never wired into the automation plugin** — only `Simulate()`/`ExportGLB()`/`ExportAVT()` are exposed. Generating realistic synthetic *product photos* (as opposed to UV/mesh correspondence data) would require new plugin work to trigger a V-Ray render and capture an image, which doesn't exist today.

---

## Put together: the realistic data strategy

1. **Don't train from scratch.** Neither Mirra's own data (1 garment) nor any single public dataset alone is the move — start from **Sewformer's pretrained weights** (the exact published task match) and fine-tune.
2. **GarmentCodeData and SewFactory are the right pretraining/fine-tuning substrate** for panel reconstruction broadly — both synthetic, both genuinely panel/UV-level, both converged on independently by multiple research passes.
3. **For the specific texture-projection contribution**, free synthetic training data is buildable *today* using only already-confirmed-working CLO3D API calls (`Simulate()` + `ExportGLB()` with varied synthetic textures) — no new plugin engineering, and directly validated as a sound strategy by external literature (multiple 2024-2025 papers train this exact sub-problem on synthetic-only data and report it generalizes to real photos).
4. **Mirra's own small real dataset (9 runs, 1 garment, independently verified for exact size-chart accuracy earlier today) is still valuable** — not as training data, but as the real-world *evaluation* set: the thing a synthetic-trained model ultimately has to work on.
5. **Photorealistic synthetic product-photo generation (via V-Ray) is a separate, larger infrastructure investment** — worth evaluating on its own, not bundled into the near-term plan.

---

## Dataset reference — name, link, description

Every dataset (and two non-dataset references — a technique paper and a pipeline — kept here since they were part of the research) discussed above, in one place.

### Segmentation / design extraction

| Name | Link | Description |
|---|---|---|
| DeepFashion2 | [paper](https://openaccess.thecvf.com/content_CVPR_2019/html/Ge_DeepFashion2_A_Versatile_Benchmark_for_Detection_Pose_Estimation_Segmentation_and_CVPR_2019_paper.html) | 491K real fashion images / 801K clothing items, with bounding boxes, dense landmarks, and instance segmentation masks. The richest general-purpose real-photo segmentation dataset of the group. |
| Fashionpedia | [paper (arXiv)](https://arxiv.org/pdf/2004.12276) | 50.5K real images (Flickr + free-license sources) with segmentation masks and 294 fine-grained attributes across 27 categories/19 parts. Cleanest license found (CC BY 4.0). |
| ModaNet | [paper (arXiv)](https://arxiv.org/pdf/1807.01394) | 55K real street-fashion images with full polygon/pixel annotation (plus 1M more weakly-labeled), 13 garment categories. |
| iMaterialist (Fashion) 2019 | Kaggle — exact URL not confirmed during research; search "iMaterialist Fashion 2019 FGVC6" | 50K real images, 40K with instance segmentation, 10K with segmentation plus fine-grained construction attributes (sleeves, zippers, pockets). |
| LogoDet-3K | [paperswithcode](https://cs.paperswithcode.com/dataset/logodet-3k) | 158.7K real images, 3,000 logo classes, ~200K annotated logo objects. Generic logos, not garment-specific context. |
| TopLogo-10 | [v7labs](https://www.v7labs.com/open-datasets/toplogo-10) | 700 real images, 10 apparel brand logos (Nike, Adidas, Gucci, etc.). The only garment-specific real logo dataset found — small, usable only as a pilot/fine-tuning set. |

### Sewing pattern / panel reconstruction

| Name | Link | Description |
|---|---|---|
| GarmentCodeData | [paper (arXiv)](https://arxiv.org/pdf/2405.17609) · [ECCV page](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/7721_ECCV_2024_paper.php) | 115,000 synthetic 3D garments, each with its exact generating sewing pattern (panel count, geometry, seam/edge correspondence), plus UV map, segmentation, and body measurements. The only dataset with true panel-level ground truth at this scale. |
| SewFactory / Sewformer | [paper (arXiv)](https://arxiv.org/abs/2311.04218) · [project site](https://sewformer.github.io) | ~1,000,000 synthetic images paired with ground-truth sewing patterns across varied poses/bodies. Code, data, and a **pretrained image→pattern model** are all public — the closest published match to Mirra's project goal. |
| CLOTH3D | [paper (arXiv)](https://arxiv.org/pdf/1912.02792) | 2M+ synthetic clothed-human samples with garment dynamics — but **no sewing-pattern ground truth**, so not usable for panel reconstruction despite its size. |
| Dress-1-to-3 *(pipeline, not a dataset)* | [paper (arXiv)](https://arxiv.org/pdf/2502.03449) | SIGGRAPH 2025 technique that reuses a pretrained Sewformer-lineage model plus multi-view diffusion and differentiable simulation to refine a predicted pattern. Already excluded from citations as a conference paper; kept here as a technique reference only. |

### Texture / draping / UV correspondence

| Name | Link | Description |
|---|---|---|
| CLOTH3D / CLOTH3D++ | [paper (arXiv)](https://arxiv.org/pdf/1912.02792) | Same dataset as above, relevant here for a different reason: synthetic draped renders with known UV maps and applied textures — free, exact (draped render ↔ flat texture) pairs. |
| DeepIron *(method paper, not a dataset)* | [paper (arXiv)](https://arxiv.org/pdf/2310.15447) | Eurographics/CGF 2024 — solves the exact target problem: a "Texture Unwarper" that infers the original flat texture from a photo of warped/wrinkled clothing. Closest prior art to study for methodology. See also `05-logo-extraction-and-3d-placement.md` for how this connects to logo-specific extraction. |
| Single View Garment Reconstruction via Pattern Coordinates *(method paper)* | [paper (arXiv)](https://arxiv.org/abs/2504.08353v1) | 2025 paper training exclusively on synthetic simulated cloth data, reporting it generalizes to real photos despite zero real training data — direct evidence the synthetic-only strategy works. |
| Multi-Garment Net (MGN) dataset | [project page](https://virtualhumans.mpi-inf.mpg.de/mgn/) | 712 real garments as 3D scans with SMPL registration and real texture maps. Real data, but garment-level, not panel-level. |
| Deep Fashion3D (V2) | [GitHub](https://github.com/GAP-LAB-CUHK-SZ/deepFashion3D) | 2,078 real-garment reconstructions (563 instances, 10 categories), multi-view real images with registered mesh and texture maps. Real-world texture ground truth, but confirmed to exclude sewing-pattern data. |

### Virtual try-on benchmarks (ruled out for this project's task)

| Name | Link | Description |
|---|---|---|
| VITON-HD | discussed in [this survey (arXiv)](https://arxiv.org/pdf/2503.20418) — no official project link confirmed during research | 13,679 real person+garment image pairs. Only provides composited try-on result images — no panel or UV ground truth. CC BY-NC 4.0 (non-commercial). |
| DressCode | discussed in [this survey (arXiv)](https://arxiv.org/pdf/2503.20418) — no official project link confirmed during research | ~53,000 real images across upper-body/lower-body/dress categories. Same limitation as VITON-HD — image-to-image only. |

---

## Sources (from all five research passes)

Same links as the reference list above, kept here as the original compiled source list.
