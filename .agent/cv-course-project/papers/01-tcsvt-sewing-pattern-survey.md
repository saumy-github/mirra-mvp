# Paper 1: Deep Learning for 3D Fashion Design, a Survey from a Sewing-Pattern-Driven Perspective

*Status: current*
*Written: 2026-10-18*
*Source: the PDF in this folder (text decoded from `paper1_decoded.txt`, which has a one-character font-shift artifact) plus the earlier note `06-tcsvt-survey-paper-explained.md`*

---

## 1. At a glance

| | |
|---|---|
| **Title** | Deep Learning for 3D Fashion Design: A Survey From a Sewing-Pattern-Driven Perspective |
| **Authors** | Jinbo Luo, Hong Qu, Yujie Zhao, Jie Zhang, Yadie Yang |
| **Where** | IEEE Transactions on Circuits and Systems for Video Technology (TCSVT), Vol. 36, No. 4, April 2026 |
| **DOI** | 10.1109/TCSVT.2025.3637565 |
| **Dates** | Received Aug 2025, accepted 20 Nov 2025, published online 26 Nov 2025 |
| **Type** | Survey (a literature review, no new model) |
| **Who the authors are** | Fashion and textile researchers (Hong Kong Polytechnic University), plus Sanya University and Macao Polytechnic University |

**One sentence:** a map of how deep learning is used to create, recover and edit the **2D sewing pattern** that a 3D garment is built from.

---

## 2. The problem the authors saw

A sewing pattern is the set of flat cloth shapes (panels) you cut out and sew together. In 3D fashion software (CLO3D, Style3D) the pattern is what decides the final shape, fit and whether the garment can actually be manufactured.

The authors say earlier work had three holes:

1. **Sewing patterns were a side topic.** Other surveys look at deep learning in fashion in general (2D images, 3D shapes, animation), where patterns are one small subtopic.
2. **Research was scattered.** Papers solve one task (only generation, or only reconstruction) with no view of the whole pipeline.
3. **No shared benchmarks.** Datasets and evaluation metrics were spread out and inconsistent, so methods could not be compared fairly.

---

## 3. What the authors did

- **Searched the literature** in IEEE Xplore, ACM Digital Library, SpringerLink, ScienceDirect and arXiv, for papers from 2018 to 2025, using keywords such as "sewing pattern", "3D garment" and "deep learning".
- The search gave **252 candidate papers**. They kept only work that directly links deep learning to **manufacturable sewing patterns**, and dropped pure 2D image synthesis and pattern-free 3D modelling. **204 papers** were analysed in depth.
- **Proposed one organising idea:** a four-stage pipeline that every paper is sorted into.
- **Collected the datasets and metrics** in one place (Section 7 below).
- **Compared three design paradigms** and listed limitations and future directions.

---

## 4. The four-stage pipeline (the paper's backbone)

```
1 Representation  ->  2 Generation  ->  3 Reconstruction  ->  4 Editing
 (store a pattern      (create a         (recover a pattern    (change a pattern
  as data)              pattern)           from text/image/       to fix fit or
                                           sketch)                follow an idea)
```

### 4.1 Representation: how a pattern is written as data

**Four building blocks** of a pattern:

| Block | Meaning |
|---|---|
| **Panels** | closed 2D cloth shapes (front, back, sleeves) |
| **Vertices** | the corner points of a panel |
| **Edges** | the lines between vertices: straight lines, quadratic or cubic Bezier curves, B-splines, circular arcs |
| **Stitches** | pairs of edges sewn together. A hard rule: **stitched edges must have equal length** |

The authors stress this four-block model is an **idealisation**. It ignores pockets, plackets, collars, cuffs, seam allowances and hardware (zips, buttons). They call that a key open challenge.

**Three ways to feed a pattern to a model:**

| Format | What it is | Examples |
|---|---|---|
| **Dictionary** | JSON key-value data. Readable and flexible. Uses abstract units or ratios, converted to cm/mm only at the end using body measurements | GarmentCode |
| **Tokenized** | Numbers are normalised, then rounded into discrete bins (a vocabulary), so a pattern becomes a token sequence like text | DressCode, AIpparel, GarmentDiffusion |
| **Raster** | The pattern is drawn as a small grid image, with layers for markers, edge types and deformations | GarmentImage, GarmageNet |

### 4.2 Generation: creating patterns

**Rule-based (explicit formulas).** A designer writes the geometry as formulas with parameters. Strengths: controllable, easy to explain, needs no training data. The paper's example is a skirt:

- inputs: waist circumference, a length factor, a hem-expansion factor
- formulas turn these into skirt length, arc lengths and radii

GarmentCode is the best-known system: a small programming language for garments that takes body measurements and style attributes.
Another rule-based idea is **inverse design**: drape a template on a scanned body in a simulator and tune its parameters until the simulated garment matches (minimising the Chamfer distance, which measures how far two shapes are from each other).

**Learning-based (neural networks).** Four network families:

| Model | Idea | Good | Weak |
|---|---|---|---|
| **MLP** | regress a fixed-length parameter vector (loss: mean squared error) | cheap, fine for a fixed template | cannot change panel count or vertex count |
| **LSTM** | predict panel vertices one after another (Panelformer, NeuralTailor) | handles variable length | struggles with long-range rules like symmetry; slow; errors pile up |
| **Transformer** | predict the next token (DressCode, AIpparel; loss: cross-entropy) | strong global structure for multi-panel garments | cost grows with the square of sequence length; needs a lot of data |
| **Diffusion** | start from noise and denoise into a pattern (SewingLDM, GarmageNet) | best quality and diversity | slow, many sampling steps |

### 4.3 Reconstruction: recovering a pattern from an input

This is the stage closest to Mirra. The authors frame it as a **one-to-many problem**: one sketch or sentence can match many valid garments. Most models are trained with a regression loss, so they learn the **average** answer instead of representing the ambiguity. They call this an open problem.

| Input | Methods |
|---|---|
| **Text** | DressCode's SewingGPT (a CLIP text encoder feeding a Transformer decoder); SewingLDM (T5 text encoder); ChatGarment, Design2GarmentCode and AIpparel (built on LLaMA/LLaVA-type language models) |
| **Image** | Early CNN methods: **SPnet** (first normalises the photo to a T-pose view, then predicts pattern parameters), **GarmentImage** (a chain of U-Nets). Hybrid: **Sewformer** and **Panelformer** (a ResNet50 feature extractor feeding a Transformer). **Dress-1-to-3** adds an extra Transformer stage. Multimodal language models: ChatGarment and AIpparel (LLaVA with a CLIP-ViT or SigLIP image encoder); Design2GarmentCode (GPT-4V); GarmentX (DINOv2 ViT-B/14 tokens) |
| **Sketch** | PersonalTailor (a sketch guides interpretation of a 3D garment point cloud); a sketch-latent approach using sketchRNN; SewingLDM (makes its own training sketches from the GarmentCodeData images with the PiDiNet edge model, but the synthetic sketches differ from real hand drawings, so accuracy drops on real sketches) |

### 4.4 Editing: changing a pattern

| Type | How | Examples |
|---|---|---|
| **Precise** | Drag control points or change parameters. 2D and 3D stay in sync | Sensitive Couture (uses sensitivity analysis plus re-meshing), PerfectTailor ("cut", "extend", "tighten"), GarmentCode parameter sliders, GarmentX parameter vectors that edit one region without regenerating everything |
| **Fuzzy** | Natural-language commands such as "make the sleeves longer" | Design2GarmentCode (one agent reads the instruction, another writes the program), ChatGarment (finds the referenced part, edits only its parameters) |

The core difficulty of fuzzy editing: "longer sleeves" is under-specified. A naive stretch would distort the cuff and break the armhole seam. Systems cope by editing **structured, disentangled parameters**, so related edges move together. Pleasing aesthetics are still little studied.

---

## 5. Datasets (Table VI in the paper)

| Dataset | Size and content |
|---|---|
| Wang et al. (early) | 8,000 samples; shirts, skirts, kimonos; pattern, image and sketch |
| Korosteleva and Lee | 23,500 patterns from 19 base templates |
| **SewFactory** | 1 million images paired with 19,100 sewing patterns |
| **DressCodeData** | 19,300 samples with text descriptions and textures |
| **GarmentCodeData (GCD)** | 115,000 garments: 2D patterns, 3D meshes, UV maps, body measurements, parametric design info |
| **GCD-MM** | adds paired text and images for 120,000 garments, with editing annotations |
| **GarmentX** | 378,682 garment instances (parameter-image pairs) |

**Caveat the authors repeat:** the big datasets are **procedurally generated from a few parameterised templates**. Style count scales, but real-world variety (intricate necklines, unusual cuffs) is missing, so models generalise poorly to creative real fashion.

---

## 6. Evaluation metrics (Table VII)

| Level | Metrics |
|---|---|
| **Pattern** | number of panels and edges; **Panel L2** (average distance between predicted and true panel vertices); rotation L2 and translation L2; **stitch precision and recall**; Average Matching Distance (distance between matching vertices along stitched edges); IoU of rasterised panels |
| **3D garment** | Chamfer Distance; Point-to-Surface distance; **Simulation Success Rate** (can the pattern be assembled and simulated without errors); Clothes-to-Body Distance |
| **Multimodal** | CLIP Score (text vs rendered garment); human Agreement Score; Aesthetic Score (from Design2GarmentCode) |

---

## 7. Applications

- **Physical production:** individual customisation (ergonomic fit from 3D scans, aesthetic fit from images or text) and mass customisation through **size grading**. Uniform scaling distorts proportions, so Gerber and Lectra apply rule-based, locally scaled grading; UNIQLO uses Asian body data for region-specific sizing.
- **Virtual simulation:** virtual try-on in CLO3D and Style3D. Patterns also drive **UV mapping**, which places textures, prints and seam details on the 3D garment with less distortion.
- **Digital garments for games and animation:** stylised or non-human bodies, extreme motion.

---

## 8. The big comparison (Section IX)

| Paradigm | How it works | Strength | Weakness |
|---|---|---|---|
| **2D fashion design** | pixel decoders (U-Net, GAN), image-to-image | lots of public image data | only surface-level changes, one viewpoint |
| **Pattern-free 3D** | a decoder predicts a mesh, point cloud or signed distance field directly | flexible and novel | hard to edit, no link to manufacturing, scarce 3D data |
| **Pattern-driven 3D** | a structure-aware decoder outputs 2D patterns, a physics simulator then assembles them | editable and manufacturable | less design freedom |

---

## 9. Limitations and future work the authors name

**Limitations**

1. **Not enough data.** Datasets are small or inconsistently annotated, and aligning patterns with 3D models, images and text is costly.
2. **Representations are too simple.** No pockets, plackets, collars, cuffs or hardware.
3. **Ambiguous inputs.** Models learn the average instead of real design intent.
4. **No standard evaluation.** Everyone invents metrics, and fit and aesthetics rely on subjective ratings.

**Future directions**

1. Large, richly annotated datasets (fine manufacturing detail, semi-automatic annotation, procedural generation plus augmentation).
2. Richer representations that cover pockets, collars and hardware.
3. Better multimodal understanding, for example probabilistic models such as conditional VAEs that keep several valid answers, and interactive feedback.
4. Standard, more objective metrics, including simulation-based fit measures such as body-garment distance or pressure maps.

---

## 10. How to explain it in one minute

> "Every 3D garment starts as a flat sewing pattern: panels, their edges, and which edges get stitched together. This survey sorts all deep learning work on patterns into four stages: **represent** a pattern as data, **generate** one, **reconstruct** one from text, an image or a sketch, and **edit** one. It lists the datasets (up to about 380,000 garments, but made from a few templates) and the metrics, and it ends with four gaps: too little real data, patterns that ignore pockets and collars, ambiguous inputs, and no standard way to judge results."

---

## 11. What Mirra can use from this paper

| Idea in the paper | How it maps to Mirra | Use |
|---|---|---|
| **Pattern-driven 3D design** (pattern first, then simulate) | This is exactly our pipeline: Step 2 makes DXF patterns, Step 3 simulates them in CLO | Cite it as the justification for our architecture over pattern-free 3D |
| **Rule-based generation** | `CloTShirtDraft` in `clo_block/` is a rule-based parametric generator (measurements in, panels out) | Describe our Step 5 in these terms; no training data needed |
| **Four-block pattern model with equal-length stitches** | Our `edge_manifest.json` and `seam_report()` already express edges and seams | Add an automatic "stitched edges are equal length" check per seam (the paper's hard constraint) |
| **Reconstruction from images** (Sewformer, Panelformer, AIpparel) | We do not read shape from the photo today; the size row decides shape | Option for later: use a pretrained image-to-pattern model to **suggest** garment type and style (neckline, sleeve length) and then let measurements set the dimensions |
| **Metrics** (#Panels, #Edges, Panel L2, stitch precision/recall, Simulation Success Rate, Clothes-to-Body Distance) | We have unit tests but no benchmark numbers | Report Panel L2 and edge count against CLO's reference tee, and simulation success rate across sizes, in the course paper |
| **Datasets** (GarmentCodeData, SewFactory) | We have 5 cloths | Use GarmentCodeData as test patterns and a source of synthetic examples; keep in mind it comes from limited templates |
| **Limitation: no pockets, collars, cuffs, seam allowances** | Ours has the same gap (four panels only) | State it honestly as a known limit; list pockets and collars as the next panel types |
| **Editing with structured parameters** | Our size row is already a parameter set | Allow edits like "sleeve length +2 cm" by changing the size row and regenerating; consider a language-model front end later |
| **One-to-many problem** | A product photo does not fix the exact pattern | Argue that using the measurement sheet for dimensions avoids the "average answer" problem |
