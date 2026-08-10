# CV Course Project — Paper Survey and Topic Selection

**Created:** 2026-08-09
**Purpose:** College Computer Vision course project + paper, chosen so the work also feeds the Mirra MVP.
**Constraint set by the course:** take inspiration from recent papers — **2024, 2025, 2026 only**, nothing older.
**Constraint set by Saumy:** **no conference papers.** Journals and magazines only.

> This folder is separate from `.agent/website-launch/` on purpose — that folder tracks the Mirra
> product build, this one tracks the college coursework. They overlap in subject matter, not in scope.

---

## 1. The three candidate project ideas

1. **Face → 3D avatar.** Take face images and produce that face on a 3D avatar. (Mirra needs this too.)
2. **Dimensions from images.** Scan humans or objects from images and recover their real-world
   measurements. (Mirra needs this too.)
3. **Clothes → 3D.** Take garment images and produce a 3D model or garment measurements.

All three are genuine Mirra subproblems, so any of them double-counts as coursework and product work.

---

## 2. Critical caveat: "journal" does not mean "not a conference"

This is the single most important thing in this document. Several of the most prestigious venues in
this field are **journals that publish conference proceedings**, so a naive "journals only" filter
will still hand you conference papers:

| Venue | Presents as | Actually is |
|---|---|---|
| **ACM TOG** (Transactions on Graphics) | Journal | Vols 43–45 are largely **SIGGRAPH / SIGGRAPH Asia** proceedings |
| **Computer Graphics Forum** | Journal | Frequently **Eurographics / Pacific Graphics / SGP** proceedings |
| **IEEE TVCG** | Journal | Some issues are **IEEE VR / ISMAR** proceedings |

Concretely: `Dress-1-to-3` (TOG 2025) and `LUIVITON` (TOG 2026) are SIGGRAPH papers wearing a
journal label. Before citing anything from TOG / CGF / TVCG, **check whether its issue is a
conference special issue.**

**Safe journal venues** for this field: IEEE **TPAMI**, **TIP**, **TMM**, **TCSVT**, **TNNLS**,
**IJCV**, **Pattern Recognition**, **Computers & Graphics**, **CVIU**, **JVCIR**,
**The Visual Computer**, **Neural Networks**, **Image and Vision Computing**.

### Venues to avoid entirely

These appeared repeatedly in search results and are predatory or near-predatory. Citing them
actively weakens a paper:

- IJSREM / "International Journal of Scientific Research in Engineering and Management"
- IJRASET
- IJACSA
- "International Journal on Science and Technology"
- International Research Journal of Modernization in Engineering Technology and Science

### Mid-tier — legitimate but weak as a sole anchor

**IEEE Access** and **MDPI** titles (Sensors, Applied Sciences, Informatics, Journal of Imaging)
are peer-reviewed and safe to cite, but are APC-funded with lighter review than Transactions. Use
them as supporting citations, not as the paper you claim to be advancing.

---

## 3. Topic 1 — Face / head image → 3D avatar

### IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| ✅ **GPHM: Gaussian Parametric Head Model for Monocular Head Avatar Reconstruction** | **TPAMI** | 2025 | 6 | `10.1109/TPAMI.2025.3596331` |
| Face Generation and Editing With StyleGAN: A Survey | **TPAMI** | 2024 | 93 | `10.1109/TPAMI.2024.3350004` |
| 3DCMM: 3D Comprehensive Morphable Models With UV-UNet for Accurate Head Creation | **TMM** | 2024 | 7 | `10.1109/TMM.2024.3521835` |
| Dual-Space Semi-supervision for Aesthetic-Consistent 3D Face Reconstruction | **TMM** | 2026 | 0 | `10.1109/TMM.2026.3673537` |
| Instruction-Driven 3D Facial Expression Generation and Transition | **TMM** | 2025 | 1 | `10.1109/TMM.2025.3565929` |
| Relightable and Animatable Gaussian Head Avatar From Monocular Videos | TVCG ⚠ | 2026 | 0 | `10.1109/TVCG.2026.3678035` |
| Expressive Head Avatar Modeling From Monocular Video of Neutral Expression | TVCG ⚠ | 2026 | 0 | `10.1109/TVCG.2026.3690559` |
| HFM-GS: Half-Face Mapping 3DGS Avatar Based Real-Time HMD Removal | TVCG ⚠ | 2025 | 0 | `10.1109/TVCG.2025.3616801` |
| Realistic Facial Expression Reconstruction Using Millimeter Wave | TMC | 2025 | 4 | `10.1109/TMC.2025.3540877` |

⚠ = check for conference special issue before citing.

**✅ GPHM abstract (verified).** Xu, Wang, Zheng, Su, Liu. Uses 3D Gaussians to build a *parametric*
head model with independent control of identity and expression, handling detail that morphable
models struggle with (notably hairstyles). Achieves photorealistic real-time rendering, and applies
the model to monocular-video / few-shot avatar reconstruction, beating prior work on both
reconstruction quality and training speed.

### Non-IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| An Interactive Conversational 3D Virtual Human | **IJCV** | 2026 | 0 | `10.1007/s11263-025-02725-8` |
| HMamba-3DFT: hierarchical Mamba for emotion-driven semantic 3D facial tracking | **Pattern Recognition** | 2026 | 0 | `10.1016/j.patcog.2026.113415` |
| SS3DFR: Semi-supervised 3D face reconstruction from single face image | **JVCIR** | 2026 | 0 | `10.1016/j.jvcir.2026.104784` |
| EMOVA: Emotion-driven neural volumetric avatar | Image and Vision Computing | 2024 | 3 | `10.1016/j.imavis.2024.105043` |
| ExpAvatar: High-Fidelity Avatar Generation of Unseen Expressions with 3D Face Priors | ACM TOMM | 2024 | 4 | `10.1145/3700770` |
| Personalizing human avatars based on realistic 3D facial reconstruction | Multimedia Tools & Apps | 2024 | 13 | `10.1007/s11042-024-19583-0` |
| Generating animatable 3D cartoon faces from single portraits | Virtual Reality & Intelligent Hardware | 2024 | 13 | `10.1016/j.vrih.2023.06.010` |
| Refined dense face alignment through image matching | The Visual Computer | 2024 | 2 | `10.1007/s00371-024-03316-3` |
| PSHead: 3D Head Reconstruction from a Single Image with Diffusion Prior | Computer Graphics Forum ⚠ | 2025 | 0 | `10.1111/cgf.70279` |
| 3D face image reconstruction using multi-scale dense 3D conv generative networks | The Imaging Science Journal | 2026 | 0 | `10.1080/13682199.2026.2670241` |
| A Lightweight 3DMM-CNN Pipeline for Real-Time Single-Image 3D Face Reconstruction | Informatics (MDPI) | 2026 | 0 | `10.3390/informatics13080122` |

### Assessment

**Most crowded of the three areas.** GPHM is the state of the art and beating it is not a semester
project. If this topic is chosen, the paper must take an **efficiency / lightweight** angle, not a
quality angle — the Informatics 2026 paper is the closest existing model of a realistic student scope.

---

## 4. Topic 2 — Dimensions from images (body measurement / shape) — **RECOMMENDED**

### IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| **Human as Points: Explicit Point-Based 3D Human Reconstruction From Single-View RGB** | **TPAMI** | 2025 | 7 | `10.1109/TPAMI.2025.3552408` |
| **LEAPSE: Learning Environment Affordances for 3D Human Pose and Shape Estimation** | **TIP** | 2024 | 6 | `10.1109/TIP.2024.3393716` |
| MultiGO++: Monocular 3D Clothed Human Reconstruction via Geometry-Texture Collaboration | TVCG ⚠ | 2026 | 0 | `10.1109/TVCG.2026.3699434` |
| MuSAnet: Monocular-to-3D Human Modeling via Multi-Scale Spatial Awareness | TCE | 2024 | 0 | `10.1109/TCE.2024.3410989` |
| Surface-Aligned 3D Human Shape Estimation via Gaussian Curvature Structure Learning | Sensors J. | 2025 | 0 | `10.1109/JSEN.2025.3624143` |
| A Somatotype Classification Approach Based on Generative AI and Frontal Images | Access | 2025 | 3 | `10.1109/ACCESS.2025.3553797` |

### Non-IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| ✅ **Inferring Body Measurements from 2D Images: A Comprehensive Review** | **Journal of Imaging** | 2025 | 6 | `10.3390/jimaging11060205` |
| **Parametric model fitting for textured and animatable 3D avatar from a single frontal image of a clothed human** | **Computers & Graphics** | 2025 | 2 | `10.1016/j.cag.2025.104478` |
| Enhancing video-based human mesh recovery with Attention-Mamba synergy | Expert Systems w/ Applications | 2025 | 1 | `10.1016/j.eswa.2025.127415` |
| Smartphone 3D imaging for body composition using non-rigid avatar reconstruction | Frontiers in Medicine | 2024 | 10 | `10.3389/fmed.2024.1485450` |
| Body composition estimation from mobile phone 3D imaging | British Journal of Nutrition | 2024 | 9 | `10.1017/s0007114524002216` |
| A Human Body Simulation Using Semantic Segmentation and Image-Based Reconstruction | Applied Sciences | 2024 | 3 | `10.3390/app14167107` |

**✅ Journal of Imaging review (verified).** Mohammedkhan, Fleuren, Güven, Postma (2025). Surveys
four method families: classical ML (linear/SVR/kNN on extracted features), CNN-based end-to-end and
transfer learning, hybrid late-fusion of pose features with deep features, and **explicitly flags
vision transformers and diffusion models as underexplored in this domain**.

Datasets it consolidates — this is the practical value of the paper:

| Dataset | Content |
|---|---|
| **CAESAR** | 3D scans, ~2,400 subjects |
| **ANSUR** | 13,000 subjects (military anthropometry) |
| **IMDB-23K** | 23,000 images with height labels |
| **ARAN** | 512 children, multi-view clinical images |
| **MORPH-II** | 55,000 subjects |
| **Body-Fit** | 4,149 subjects, silhouettes |

Also notes a real gap: lack of diverse and child-focused datasets.

### Assessment — why this is the recommendation

- **It fills a live hole in Mirra.** Measurements are currently hand-typed into a form
  (`/measurements`), and the photo `capture/` module was deleted from both frontend and backend.
  Photo → measurements is a genuine product gap, not a hypothetical one.
- **It is actually achievable.** Silhouette/keypoint → regression trains on a laptop GPU. Topics 1
  and 3 need serious compute to be competitive.
- **The gap statement is pre-written.** The J. Imaging review says ViTs and diffusion are
  underexplored and datasets lack diversity. A defensible thesis: *"ViT-based anthropometric
  regression from two orthogonal silhouettes, benchmarked against CNN baselines on CAESAR / Body-Fit."*
- **Ground truth is free.** The existing CLO3D pipeline generates avatars from known measurements,
  so synthetic silhouettes with perfect labels can be rendered on demand — which is the standard
  trick in this literature anyway.

---

## 5. Topic 3 — Clothes → 3D model / measurements

### IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| ✅ **Deep Learning for 3D Fashion Design: A Survey From a Sewing-Pattern-Driven Perspective** | **TCSVT** | 2025/26 | 2 | `10.1109/TCSVT.2025.3637565` |
| Scale-Wise Semantic Alignment Enhanced Multigrained Adaptive Fusion for Virtual Try-On | **TNNLS** | 2025 | 0 | `10.1109/TNNLS.2025.3554826` |
| CHA: Physics-Based Dynamics Modeling for Clothing-Editable Human Avatars | **TMM** | 2026 | 0 | `10.1109/TMM.2026.3701539` |
| ViTon-GUN: Person-to-Person Virtual Try-on via Garment Unwrapping | TVCG ⚠ | 2025 | 3 | `10.1109/TVCG.2025.3550776` |
| FOSUP: Dynamic Garments Diffusion With Fourier Spherical Unwrapping From Monocular Video | TVCG ⚠ | 2025 | 0 | `10.1109/TVCG.2025.3625117` |
| AGFF: Attention-Gated Feature Fusion for Multi-Pose Virtual Try-On | TCE | 2025 | 1 | `10.1109/TCE.2025.3535237` |
| Toward High-Fidelity 3D Virtual Try-On via Global Collaborative Modeling | TCE | 2024 | 3 | `10.1109/TCE.2024.3433526` |
| ✅ **QuantFit-VTON: Measurement-Conditioned Diffusion Model for Predictable Garment Fit** | Access | 2026 | 0 | `10.1109/ACCESS.2026.3668411` |

**✅ TCSVT survey abstract (verified).** Luo, Qu, Zhao, Zhang, Yang. The **first** systematic review
of deep learning for sewing-pattern-driven 3D fashion design. Proposes a four-stage pipeline —
**representation → generation → reconstruction → editing** — reviews geometric encoding for pattern
representation, data-driven pattern generation, reconstruction from multimodal inputs (images,
sketches, text), and 3D garment editing. Consolidates datasets and evaluation metrics. Names limited
data availability and encoding domain-specific design constraints as the open challenges.
**This is effectively a literature map of Mirra's Step 2 (product ingestion), regardless of which
course topic is picked.**

**✅ QuantFit-VTON abstract (verified).** Nikolaev, Roman, Makarov. Augments VITON-HD with *numeric*
person and garment measurements (height, length, width) and conditions a diffusion model on them via
a Measurement Encoder, training with a large neutral inpainting region so length and silhouette can
change freely. Reports FID comparable to IDM-VTON with **>50% reduction in hem-position error**.
This is the closest published work to Mirra's core thesis — measurement-driven, predictable fit.

### Non-IEEE journals

| Paper | Journal | Year | Cites | DOI |
|---|---|---|---|---|
| TryOn-Adapter: Efficient Fine-Grained Clothing Identity Adaptation | **IJCV** | 2025 | 8 | `10.1007/s11263-025-02352-3` |
| Enhancing image-based virtual try-on with Multi-Controlled Diffusion Models | **Neural Networks** | 2025 | 4 | `10.1016/j.neunet.2025.107552` |
| Wp-VTON: wrinkle-preserving virtual try-on via clothing texture book | **Neural Networks** | 2025 | 2 | `10.1016/j.neunet.2025.107546` |
| 3D-aware virtual try-on using only 2D inputs | **CVIU** | 2026 | 1 | `10.1016/j.cviu.2026.104661` |
| SketchTailor: sketch-driven modeling for garment pattern reconstruction | **Computers & Graphics** | 2025 | 3 | `10.1016/j.cag.2025.104345` |
| Diffusion model-based size variable virtual try-on technology and evaluation method | **Computers & Graphics** | 2025 | 2 | `10.1016/j.cag.2025.104448` |
| VITON-DRR: Details retention virtual try-on via non-rigid registration | **Computers & Graphics** | 2025 | 1 | `10.1016/j.cag.2025.104288` |
| ClotheDreamer: Text-guided garment generation with 3D Gaussians | Applied Intelligence | 2025 | 7 | `10.1007/s10489-025-06596-x` |
| Revolutionizing online shopping with FITMI: a realistic virtual try-on solution | Neural Computing & Applications | 2025 | 15 | `10.1007/s00521-024-10843-6` |
| Improving virtual try on clothes using image depth estimation | Scientific Reports | 2025 | 6 | `10.1038/s41598-025-18107-6` |
| Har-vton: diffusion-based virtual try-on with hybrid attention | The Visual Computer | 2025 | 1 | `10.1007/s00371-025-04223-x` |
| Multimodal-Conditioned Latent Diffusion Models for Fashion Image Editing | ACM TOMM | 2026 | 1 | `10.1145/3789212` |
| Garment Recycle Training and Conditional Garment-Person Outline Attention-Guided Virtual Try-on | ACM TOMM | 2025 | 0 | `10.1145/3758098` |
| A computer-vision based framework for virtual 3D garment reconstruction | Multimedia Tools & Apps | 2024 | 0 | `10.1007/s11042-024-20269-w` |
| Parametric 3D clothing generation: From sketch to dynamic fit | J. Engineered Fibers & Fabrics | 2026 | 0 | `10.1177/15589250261441600` |

### Excluded — conference papers in journal clothing

| Paper | Venue | Why excluded |
|---|---|---|
| Dress-1-to-3: Single Image to Simulation-Ready 3D Outfit | ACM TOG 2025 | SIGGRAPH 2025 |
| LUIVITON: Learned Universal Interoperable Virtual Try-ON | ACM TOG 2026 | SIGGRAPH-track |
| MaX4Zero: Masked Extended Attention for Zero-Shot Virtual Try-On | CGF 2026 | Eurographics-track |

### Assessment

Strong second choice. The TCSVT survey plus QuantFit-VTON give an unusually clean story:
measurement-conditioned garment fit is *published, recent, and unfinished*.

---

## 6. IEEE Magazines (2024–2026)

Searched IEEE Computer Graphics & Applications, IEEE MultiMedia, IEEE Consumer Electronics Magazine.

### The one that matters

| Paper | Magazine | Year | DOI |
|---|---|---|---|
| ✅ **A Semiautomated Pipeline for the Creation of Virtual Fitting Room Experiences Featuring Motion Capture and Cloth Simulation** | **IEEE CG&A** | 2024 | `10.1109/MCG.2024.3521716` |

**Abstract verified.** Cannavò, Offre & Lamberti (Politecnico di Torino). Names both of Mirra's core
problems explicitly: *"difficulties in obtaining high-fidelity reconstructions of body shapes"* and
*"providing realistic visualizations of animated clothes following real-time customers' movements."*
Pipeline = accurate 3D avatar reconstruction → motion-capture animation → garment design and
simulation. Validated with a **user study** against two existing tools, measuring usability,
embodiment, model accuracy, perceived value, adoption, and **purchase intention**.

Two reasons this is valuable: it is the published version of Mirra's architecture, and its
evaluation protocol is directly borrowable — a user study is what separates a course paper from a
plain MAE-in-centimetres report.

### Adjacent magazine articles

| Paper | Magazine | Year | Cites | DOI |
|---|---|---|---|---|
| Smartphone Video-Based Monocular 3D Reconstruction | IEEE Consumer Electronics Mag. | 2024 | 2 | `10.1109/MCE.2024.3402848` |
| From Virtual Live Entertainment to Real-Time Telepresence: Interoperable and Latency-Aware End-to-End Avatar Pipelines | IEEE CG&A | 2026 | 0 | `10.1109/MCG.2026.3713291` |
| The Rise of AI-Generated Anime Avatars: Trends, Challenges, Opportunities | IEEE CG&A | 2026 | 0 | `10.1109/MCG.2025.3627323` |
| Empirical Studies of Large-Scale Environment Scanning by Consumer Electronics | IEEE Consumer Electronics Mag. | 2025 | 1 | `10.1109/MCE.2025.3549585` |
| Exploring Avatar Experiences in Social VR: Analysis of User Reviews | IEEE Consumer Electronics Mag. | 2024 | 15 | `10.1109/MCE.2024.3350875` |
| MAStGS: MASt3R-Assisted Efficient 3D Gaussian Splatting for Indoor Scene Reconstruction | IEEE MultiMedia | 2026 | 0 | `10.1109/MMUL.2026.3687868` |
| Dynamic Gaussian-Based Digital Twin Reconstruction of Articulated Multi-Joint Objects | IEEE CG&A | 2026 | 0 | `10.1109/MCG.2026.3701284` |

### Negative results worth recording

- IEEE magazines have **zero** 2024+ articles on garment / sewing-pattern reconstruction other than
  the VFR paper above.
- IEEE magazines have **zero** articles on anthropometric body measurement. Topic 2 lives entirely
  in Transactions.

### How to use magazines vs journals

Magazine articles are peer-reviewed and satisfy the "no conference papers" rule, but they are
shorter, overview/practitioner-oriented, and rarely carry a reproducible method with benchmarks.

```text
Anchor / technical baseline  → Transactions (TPAMI, TIP, TMM, TCSVT)
Motivation, framing, evaluation design → magazines (CG&A)
```

A paper whose only inspiration is a magazine article looks thin. Citing CG&A for *why the problem
matters* and TPAMI for *what the state of the art is* looks properly grounded.

---

## 7. Recommendation

**Choose Topic 2 — body dimensions from images.** Supporting structure:

| Role | Paper |
|---|---|
| Problem motivation | **IEEE CG&A 2024** — VFR pipeline; states body-shape reconstruction fidelity as the blocker |
| Technical baseline | **IEEE TPAMI 2025** — *Human as Points* |
| Second baseline | **IEEE TIP 2024** — *LEAPSE* |
| Datasets + gap statement | **J. Imaging 2025** review — ViT/diffusion underexplored |
| Evaluation design | **IEEE CG&A 2024** user-study protocol |
| Product-side relevance | **IEEE TCSVT 2025/26** survey, **IEEE Access 2026** QuantFit-VTON |

Caution: do **not** present the J. Imaging review as the primary inspiration — courses generally
want a methods paper. Anchor on TPAMI, use the review to structure related work.

---

## 8. Open items

- **IEEE Xplore document `11523541`** — Saumy supplied this link. **Could not be retrieved:**
  ieeexplore.ieee.org returns HTTP 418 (Cloudflare bot block) to automated fetches, and the URL is
  not indexed in Semantic Scholar or OpenAlex. Needs the title + abstract pasted in manually
  (Saumy has institutional access) before it can be placed against this list.
- Decide the final topic, then narrow to 8–12 citations from the tables above.
- Confirm dataset access — CAESAR and ANSUR both require registration/licensing, which can take time.

---

## 9. Search methodology (for reproducing or extending this)

General web search was near-useless here — it buries journal work under arXiv preprints and
CVPR/ICCV papers. What worked:

1. **OpenAlex API with server-side filtering**, which enforces the journal-only constraint properly:
   ```text
   https://api.openalex.org/works
     ?filter=title_and_abstract.search:<terms>,
             from_publication_date:2024-01-01,
             type:article,
             primary_location.source.type:journal
     &sort=cited_by_count:desc
     &select=title,publication_year,doi,cited_by_count,primary_location
   ```
   Use `title_and_abstract.search:` — the plain `search=` parameter is far too fuzzy and returns
   unrelated high-citation medical reviews.
2. **Semantic Scholar API for verified abstracts:**
   ```text
   https://api.semanticscholar.org/graph/v1/paper/DOI:<doi>?fields=title,abstract,venue,year,authors
   ```
3. **Magazine sweeps by OpenAlex source id:**
   IEEE CG&A `S105380075`, IEEE MultiMedia `S72873717`, IEEE Consumer Electronics Mag. `S2483040032`.
4. **IEEE Xplore itself blocks automated access** (HTTP 418). To search it manually:
   search → left sidebar **Content Type → Journals / Magazines** (uncheck Conferences) →
   **Year 2024–2026** → sort by citations, not relevance.

Two limits of the Xplore filter worth knowing: it does **not** exclude conference proceedings
published in journal issues (TVCG/VR), and it includes IEEE Access and Early Access articles
(the latter having no volume/page numbers yet, which some citation styles reject).

---

## 10. Verification status

- ✅ = abstract retrieved and read in full. Applies to: GPHM (TPAMI), TCSVT sewing-pattern survey,
  QuantFit-VTON (IEEE Access), J. Imaging body-measurement review, CG&A virtual fitting room.
- All other entries: **title, venue, year, citation count and DOI verified** via OpenAlex with
  `type:article` + `primary_location.source.type:journal` enforced — but abstracts not individually
  read. Confirm relevance before citing.
- Citation counts are as of 2026-08-09 and will drift.
