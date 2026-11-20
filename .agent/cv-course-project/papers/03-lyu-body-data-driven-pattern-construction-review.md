# Paper 3: Body Data-Driven Garment Pattern Construction in Digital Fashion Innovations, a Review

*Status: current*
*Written: 2026-10-18*
*Source: the PDF in this folder, read in full (text only; figures were not readable).*

---

## 1. At a glance

| | |
|---|---|
| **Title** | Body data-driven garment pattern construction in digital fashion innovations: a review |
| **Authors** | Yingrui Lyu, Zhaohui Wang, Qinwen Ye, Yuexin Sun, Jing Chao (Donghua University, Shanghai; Key Laboratory of Clothing Design and Technology) |
| **Where** | *Textile Research Journal* (SAGE), 2026, Vol. 96, No. 11-12, pp. 1299-1335 |
| **DOI** | 10.1177/00405175251352800 (published online 2025) |
| **Type** | Review article (no new model) |
| **Corresponding author** | Zhaohui Wang |

**One sentence:** it explains how different kinds of **body data** (1D measurements, 2D outlines and images, 3D scans, 4D motion scans) are turned into **garment patterns**, with and without AI, and where the field is heading.

**How it differs from Paper 1.** Paper 1 (the TCSVT survey) is about **deep learning on sewing patterns**. This paper is about **where the pattern's dimensions come from**: the body, and how that data flows into the pattern. It is written from the apparel-engineering side and covers the older, non-AI methods too.

---

## 2. The problem the authors saw

Fit problems and repeated pattern revisions happen because body data is **under-used**. Traditional pattern-making uses a handful of 1D numbers (chest, waist, length). Richer data (3D shape, motion) exists but is rarely used. Earlier reviews looked at CAD systems or 3D garment design, but **none explained how body data enters the pattern workflow**, and none covered 4D data or AI-generated patterns.

---

## 3. What the authors did

They organised the field along **two lines** and then crossed them:

1. **Body data**, from simple to rich: 1D, 2D, 3D, 4D.
2. **Tools**, from manual to digital: hand drafting, then CAD, then AI.

Then they described the pattern-building methods for each data type, compared their strengths and weaknesses, listed how pattern accuracy is checked, described real commercial uses, and discussed ethics and the future.

---

## 4. The four kinds of body data

| Type | What it is | Typical source | Used for |
|---|---|---|---|
| **1D** | Lengths, circumferences, widths | Tape measure, 3D scan, body photos (front and side) | Base dimensions; drives pattern formulas and size charts |
| **2D** | Body outlines and cross-section curves | Scans, body images | Ease design, sketch modelling, image-based pattern generation |
| **3D** | Full body shape (point cloud, mesh) | 3D scanners (structured light, stereo, time-of-flight) | Personalisation, flattening, 3D fitting |
| **4D** | A 3D scan sequence over time (body in motion) | 4D scanners (3dMD, MOVE4D, Hohenstein), motion capture | Functional and sports clothing |

Notes the authors make: 1D data from photos is cheap but circumference estimates are less accurate. 3D scans cannot see hidden areas (underarm, inner thigh). 4D scanning is expensive and its processing is still immature.

---

## 5. The tools: manual to CAD to AI

- **Manual:** tape, ruler, chalk, pattern paper; draping fabric on a mannequin. Slow and depends on expert know-how. Physical patterns are hard to manage as company assets.
- **CAD:** 2D CAD (AutoCAD, Gerber) drafts patterns from measurements. 3D CAD (CLO3D, Style3D, Vstitcher) works two ways: **2D-to-3D** (drape flat patterns on a 3D mannequin) and **3D-to-2D** (build on the body, then flatten). Edits to the 2D pattern update the 3D garment.
- **AI** does two jobs:
  - **Parameter prediction:** estimate garment dimensions, fit, ease or fabric behaviour (fuzzy logic, linear regression, SVM, neural networks).
  - **AI-generated patterns (AIG-Pattern):** generate patterns with GANs, VAEs, Transformers, diffusion and multimodal models. Examples named: DressCode, Design2GarmentCode, ChatGarment, AIpparel, Sewformer, Panelformer.

Three AI weaknesses the authors list: it does not understand creative design language, it cannot capture the designer's implicit expectations, and its output is hard to edit and not production-ready.

---

## 6. Pattern construction methods by data type

### 6.1 From 1D data (measurements)

| Method | How it works | Limits |
|---|---|---|
| **Parametric design** | A pattern is defined by entities (points, lines, curves), constraints (distance, angle, tangency) and parameters (body measurements, formulas). Change the numbers and the pattern regenerates. Systems named in the paper: JBlockCreator, DisDraw, YUKA, GRAFIS, Seamly2D, AutoCAD-based tools | Works for simple standard garments (shirts, trousers, suits), not for complex or asymmetric designs. Every style needs its own hand-built model. Real body-to-pattern relations are non-linear but formulas are often linear |
| **2D grading** | Start from a base-size pattern and scale it by size-chart increments to make other sizes (ASTM D5585 is one standard). Used for made-to-measure | Standard grading fits only bodies close to the base model; hard to predefine universal rules; depends on pattern-maker skill |
| **Graphic flattening** | Build prototypes from anatomy (e.g. Nakazawa's bodice) and measurements from scan views | Mostly academic, not in production |
| **AI-aided flat pattern** | Neural nets, fuzzy logic, multiple linear regression, genetic algorithms predict pattern sizes or ease | Needs data; usually still needs a skilled pattern maker |

### 6.2 From 2D data

- **Ease allowance design:** ease is the gap between body and garment. Methods use body cross-section curves to distribute ease. Useful, but mostly tested on calico fabric, so conclusions may not transfer to other fabrics.
- **Sketch modelling:** turn a 2D contour sketch into a 3D garment (Turquin, Decaudin and others). Simple and intuitive, but the depth (Z direction) is unknown and many details are lost.
- **AI image-based pattern generation:** predict pattern parameters from a photo (Jeong et al. drove a parametric drafting module from one garment photo), or reconstruct patterns (SPnet, Sewformer, Panelformer, AIpparel). Images are easy to get, but results rely on estimation without true body ground truth, and patterns often lack darts and structure.

### 6.3 From 3D data

- **Body surface flattening:** unfold a 3D surface into 2D using ARAP, ABF++, spring-mass models or finite elements. Good for tight-fit garments (compression wear, cycling wear). Drawbacks: distortion, poor ease handling, manual cleanup needed.
- **3D grading:** make the same garment on differently sized virtual bodies and flatten each (garment transfer, differentiable simulation like "Dress Anyone", parametric bodies).
- **Virtual draping:** drape digital cloth over a 3D mannequin (Gravity Sketch, VR). Visual and quick, but limited to simple designs and needs expertise.
- **AI scan-based generation:** estimate patterns from 3D scans of clothed people or garments (NeuralTailor, Danner et al.). Problem: lines are coarse, curves not smooth, seams misaligned, so they do not meet manufacturing standards.

### 6.4 From 4D data

Dynamic measurements (body size differences between standing and moving), flattening of dynamic body models (SMPL-based postures), and early dynamic-fit studies (sportswear, workwear, a jacket for deaf people designed with CLO3D stress maps). The authors say 4D data has **not yet been applied directly to pattern construction**; research so far is on measurement and evaluation. The main obstacles: cost, lack of frame correspondence, no standard file format, no guidance on choosing key frames.

---

## 7. How pattern accuracy is checked

| Data level | Metrics |
|---|---|
| **1D** | **Seam length** of adjoining seams (they must match) and **size consistency**: compare the sample against the size chart within an allowed tolerance. Checked by pattern makers, graders and QC staff |
| **2D / 3D** | **Edge length change ratio** after flattening; for AI patterns **Panel L2**, **#Panels**, **#Edges** (as in Paper 1); cross-section **ease allowance**; **stress / pressure** (pressure sensors, or CLO3D pressure maps) |
| **4D** | **Slippage** in motion (displacement at cuffs, waistbands); **point-cloud or mesh-vertex distance** between scan frames (and between real scans and CLO simulations) |

---

## 8. Commercial use and ethics

**Real uses the authors list**

- 1D/2D: parametric customisation (custom menswear, Levi's custom jeans, Brooks Brothers made-to-measure); online pattern platforms that take measurements.
- 3D: CLO3D, Style3D and Browzwear for virtual fitting; Style3D experimented with AI-generated patterns; Nike and Adidas for fabric assessment; Zara and H&M for faster cycles; digital garments sold as assets (The Fabricant, DressX), AI tools turning 2D images into 3D garments (The Fabricant, Clothware).
- 4D: Under Armour (3dMD), Carhartt with Hohenstein, Mizuno and others for sportswear and workwear.

**Ethics**

- **Body data privacy:** direct scans of the body raise privacy concerns. One alternative: scan people in loose clothing and let AI infer body shape. Companies need data protection, transparency and explicit consent.
- **AI bias and IP:** training data often skews to certain body types; AI-generated patterns can copy existing work and ownership is unclear.

---

## 9. Prospects and challenges (the authors' conclusion)

1. **Dynamic pattern construction** with 4D data, soft-tissue mechanics, large dynamic body databases.
2. **AI-assisted pattern generation** via multimodal learning, a **parent pattern (block) with derivative patterns** to keep a brand's pattern style consistent, richer datasets, and expert pattern knowledge built into AI (darts, pleats, gathers).
3. **CAD integration:** connect to PLM, grading and marking, cutting, sales and inventory; file compatibility and APIs; cloud collaboration; AR/VR draping.
4. **Customisation and sustainability:** less physical sampling, on-demand production, upcycling designs.

---

## 10. How to explain it in one minute

> "A garment pattern is only as good as the body data behind it. This review sorts body data into four levels: simple measurements (1D), outlines (2D), full 3D scans, and 3D scans over time (4D). For each it describes how patterns are built, from parametric formulas and size grading to flattening scans, up to AI that predicts or generates patterns. It explains how accuracy is checked, for example by matching seam lengths and size-chart tolerance, lists real brand uses, and warns about body-data privacy and AI bias. Its main message is that measurement-based, parametric methods are the mature, industrial choice today, and that motion data and AI are the next frontier."

---

## 11. What Mirra can use from this paper

| Idea in the paper | How it maps to Mirra | Use |
|---|---|---|
| **1D parametric design is the mature, industrial method** | Our Step 5 is a parametric block driven by a size row (1D data) | Use the review as the citation that supports our design choice. State plainly that we are in the "parametric + grading" family |
| **Parametric limits** (one model per style, linear formulas, only simple garments) | We only have a T-shirt block | Expect to write a separate block for each new garment type (hoodie, trousers). Say so in the roadmap |
| **Grading depends on size charts and base models** | Our sizes `s_001`...`s_010` are separate rows, and hem and wrist taper come from fixed ratios of one CLO size | Consider a proper grading rule per size step instead of one ratio; the review's "width-height independent grading" is one concrete method to read |
| **Accuracy checks: seam length and size consistency within tolerance** | Our tests check bounding boxes and seam match | Add an explicit "measured vs size chart, within X mm" report per run, and an automatic seam-length equality check |
| **Ease allowance** | Our `fit_type` (slim, regular, relaxed, oversized) is stored but ease is mostly baked into the size numbers | Make ease explicit: body measurement plus an ease value gives the garment size. This also helps explain differences between sizes |
| **Stress and pressure maps in CLO3D** (used to optimise fabric and pattern) | We run CLO simulation but do not read any fit result | Export CLO stress or pressure maps as a fit-quality number, which would give Mirra a real "how does it fit" output |
| **2D images give 1D measurements; accuracy is limited** | Measurements are hand-typed today; a photo-to-measurements capability is a gap | Use this as the framing for the photo-to-measurements idea (and note the accuracy limit the authors state) |
| **Privacy: scan loosely clothed, infer shape with AI** | Mirra builds avatars from typed measurements, not scans | Mention as a privacy advantage in the course paper: no body scan is stored |
| **Parent block with derivative patterns** | Our `clo_block` is exactly a parent block | Cite it when explaining why we reverse-engineered CLO's default tee as the base |
| **AI image-based generation lacks darts and structure; patterns not production-ready** | We avoid it for shape | Supports our decision to keep pattern shape rule-based and only use AI for supporting tasks (colour, print, fabric) |
| **Commercial landscape** (CLO3D, Style3D, Browzwear; The Fabricant, Clothware) | These are our competitors and neighbours | Use as the related-industry section of the paper |
