# Paper 2: Clothing-Agnostic Pre-Inpainting Virtual Try-On (CaP-VTON)

*Status: current*
*Written: 2026-10-18*
*Source: the PDF in this folder, read in full. Figures and table layouts did not extract cleanly, so table numbers below were cross-checked against the paper's own text, and disagreements are listed in section 8.*

---

## 1. At a glance

| | |
|---|---|
| **Title** | Clothing-Agnostic Pre-Inpainting Virtual Try-On |
| **Short name** | CaP-VTON |
| **Authors** | Sehyun Kim, Hye Jun Lee, Jiwoo Lee, Taemin Lee (Kangwon National University, South Korea) |
| **Where** | *Electronics* (MDPI), 2025, 14(23), 4710, https://doi.org/10.3390/electronics14234710 |
| **Dates** | Received 1 Nov 2025, revised 24 Nov, accepted 27 Nov, published 29 Nov 2025 |
| **Academic editor** | Ping-Feng Pai |
| **Type** | Method paper (a pipeline added in front of an existing try-on model) |
| **Base model improved** | **Leffa** (Zhou et al., CVPR 2025), a diffusion-based try-on model |

**One sentence:** it fixes two weaknesses of the Leffa try-on model by (1) using better masks that also cover trousers and dresses, and (2) first **erasing the person's old clothes and repainting realistic skin**, so a long-sleeve shirt can be replaced by a short-sleeve one without the old sleeves "ghosting" through.

---

## 2. Background in plain words

**Virtual try-on (VTON)** here means a 2D image task: given a photo of a person and a photo of a garment, generate a new photo of that person wearing the garment. It is done with image-generating neural networks, not with physics simulation.

Terms used in the paper:

| Term | Meaning |
|---|---|
| **Diffusion model** | An image generator that starts from noise and removes it step by step (Stable Diffusion is one) |
| **Inpainting** | Filling a masked region of an image with new, plausible content |
| **Attention** | The part of a network that decides which region of the reference image to copy detail from |
| **Leffa** | A try-on model that adds a training loss so attention points to the correct region of the garment image. This keeps logos, text and fine patterns from smearing |
| **VITON-HD and DressCode** | Two try-on datasets. VITON-HD is upper-body clothes only. DressCode has tops, bottoms and dresses |
| **SCHP** | Self-Correction for Human Parsing: labels each pixel of a person as hair, face, arm, upper clothes, trousers and so on |
| **OpenPose** | Finds the body skeleton (pose) in a photo |
| **ControlNet** | An add-on that makes a diffusion model follow a given pose or edge map |
| **MajicMix Realistic** | A community Stable Diffusion 1.5 checkpoint tuned for realistic people and skin |
| **FID, SSIM, LPIPS** | Standard image-quality scores. FID: how close generated images are to real ones as a whole (lower is better). SSIM: structural similarity (higher is better). LPIPS: perceptual difference (lower is better) |

---

## 3. The two problems the authors found in Leffa

1. **Bottoms are poorly detected.** Leffa's upper-body model was trained on VITON-HD (upper body only). When the lower body was not detected, the output sometimes re-synthesised the whole body even if only a top should change.
2. **The old clothing leaks through.** When the input person wears long sleeves and the new garment is short-sleeved, the output often still has long sleeves. The authors' explanation: the arm, shoulder and neck skin that should now be visible were not properly restored when the old clothes were removed, so the old silhouette acted as interference.

---

## 4. The method (the authors' contribution)

The pipeline has two stages, in this order:

```
Input person photo (A)
   |
   | SCHP (body parts)  +  DressCode masking (top / bottom / dress)  +  OpenPose (pose)
   v
Stage 1: "Generate Skin" (Stable Diffusion inpainting)
   -> pre-processed person (B): old clothing removed, bare skin repainted
   |
   | DressCode masking again on (B)
   v
Stage 2: Leffa diffusion (VITON-HD model) with the reference garment
   -> final try-on image (C)
```

### 4.1 Stage 1: Generate Skin ("pre-inpainting")

- **Masks** come from the DressCode masking pipeline inside Leffa.
- **Pose control:** OpenPose output is fed through **ControlNet**. Without it, the paper shows the generated image can misplace arms or shoulders or blend into the background.
- **Skin tone fix:** inpainted skin sometimes came out darker or lighter than the person's real skin. The authors add **skin tone extraction**: detect skin pixels in the **YCrCb** colour space, take their average in **HSV**, and blend the new skin with it.
- **Generator:** the MajicMix Realistic checkpoint (Stable Diffusion 1.5 based). It also uses a "noise offset" technique, which the authors say gives better lighting and softer shadows.
- **Prompt:** a positive prompt, "Wearing Held Tight Short Sleeve Shirt, high quality skin, realistic, high quality", and a long negative prompt to avoid blur, artefacts, text, extra limbs, faces and hands.
- **Settings:** 20 inference steps, **no fine-tuning**. The experiment used **599** images for this module, because of limited Colab GPU resources.

### 4.2 Stage 2: modified Leffa with multi-category masking (the "ensemble")

- The mask comes from the **DressCode** model, which understands tops, bottoms and dresses.
- The final image comes from the **VITON-HD** Leffa model, which has higher visual quality.
- The authors justify this split with Table 1: VITON-HD has a lower FID (4.54 vs 5.05), while DressCode is better on SSIM and LPIPS (the paper's table is garbled in the PDF, but the text states this).

### 4.3 Why they call it "model-agnostic"

The two steps (better masks, then skin pre-inpainting) sit **before** the try-on model, so the authors say they can be added to other diffusion try-on systems, not only Leffa.

---

## 5. Experiments

| Item | Detail |
|---|---|
| **Hardware** | Google Colab, NVIDIA A100 40 GB, about 8 s per generated person image |
| **Test set** | 1,100 person images (100 AI-generated + 1,000 real from VITON-HD test) and 1,100 garment images, all at 1024 × 768 |
| **Compared with** | CatVTON, IDM-VTON, OOTDiffusion, Leffa (VITON-HD and DressCode versions) |
| **Standard metrics** | FID, SSIM, LPIPS (paired and unpaired settings) |
| **Ablation** | Leffa only, Leffa + DressCode, Leffa + Generate Skin, and the full CaP-VTON |

### The authors' own metric: "normal output rate"

Because FID and SSIM cannot tell whether the **sleeve length** was really replaced, they invented a check:

1. Input: a long-sleeve person plus a **short-sleeve** garment.
2. Use **CLIP ViT-B/32** to compare each result image with two sentences: "A person wearing a short sleeve" and "A person wearing a long sleeve".
3. If the short-sleeve score beats the long-sleeve score by **0.02 or more**, the result is "normal". Less than 0.02 is "partially normal". Otherwise it is "abnormal".

### Results (from Section 4.2.4 and 5.4)

| Model | Normal output rate |
|---|---|
| Leffa + Generate Skin | 63.63% |
| Leffa only | 65.27% |
| Leffa + DressCode | 68.18% |
| **CaP-VTON** | **72.8%** (801 of 1,100) |

CaP-VTON also had 22.0% "partially correct" and the lowest abnormal rate, 5.18%. The gain over Leffa alone is **7.53 percentage points**.

### The trade-off the authors admit

CaP-VTON scores **worse** on FID and LPIPS than plain Leffa. Their explanation: Generate Skin deliberately repaints large body areas, which moves the image away from the original statistical distribution, and FID punishes that. They argue sleeve-shape correctness matters more to users than FID.

---

## 6. Limitations the authors state

1. Not equally effective for every clothing change. For **complex pattern changes, fine material texture or whole-body synthesis**, plain VITON-HD or StableVITON may do better. CaP-VTON is best for **upper-body** try-on that needs skin restoration.
2. It works best when the new garment's shape is clearly different from the body outline. **Translucent or complex materials** can give discontinuous results.
3. Future work: complex poses, backgrounds, accessories and hair, faster inference, and a recommendation system.

---

## 7. How to explain it in one minute

> "Image-based try-on models often keep the old shirt's sleeves because they don't properly uncover the skin first. CaP-VTON adds two steps in front of Leffa: better clothing masks (so trousers and dresses work too), and a skin-inpainting step that erases the old clothes and repaints realistic skin with the right tone, guided by the body pose. Then the normal try-on runs. Their own CLIP-based test shows short-sleeve results correct 72.8% of the time versus 65.3% for Leffa, but the usual image-quality scores get slightly worse, which they say is expected."

---

## 8. Things to be careful about when quoting this paper

I read the whole PDF and found internal disagreements. Do not copy numbers without saying which one:

| Topic | Abstract / Conclusion | Body |
|---|---|---|
| Short-sleeve accuracy | **92.5%**, "15.4% better than Leffa's 77.1%" | Section 4.2.4 and 5.4: **72.8%** vs Leffa's 65.27% (**+7.53 points**) |
| CaP-VTON FID | | Section 4.2.2 text says FID **11.46**; the Table 2 and Table 3 rows show **6.55** |
| Image generator | | Section 4.1 says the ChilloutMix checkpoint is "based on Stable Diffusion 3.5", but Section 3.2.2 says the skin model is Stable Diffusion **1.5** based. I have not checked which is right |

Also: it is a **2D image-generation** paper. It does not change the shape of any garment and does not use measurements, so it cannot show how a garment **fits**.

---

## 9. What Mirra can use from this paper

| Idea | Where it helps Mirra | How |
|---|---|---|
| **Skin tone extraction** (detect skin in YCrCb, average in HSV) | Step 1 is expanding to basic face and skin colour; Step 2 colour extraction already removes skin with an HSV range | Reuse the YCrCb detection (usually more robust than a fixed HSV range) in two places: filter skin out of garment colour (Step 2) and estimate an avatar's skin colour (Step 1) |
| **Human parsing (SCHP)** | Our garment cut-out uses SAM2 with point prompts and sometimes grabs arms or background (see `03-sam2-prompting.md`) | Run a clothes parser first, take only the "upper-clothes" region as a prompt or as a sanity check on the SAM2 mask |
| **Multi-category masking (top / bottom / dress)** | Step 2 supports only T-shirts today | A category-aware mask is a first step toward supporting trousers and dresses |
| **A purpose-built metric (CLIP prompt test for sleeve length)** | We have no automatic check that a try-on result matches the product | Adapt it as a cheap QA test on rendered VTO frames: "short sleeve", "crew neck", "red shirt". Compare the CLIP score to the product's expected attributes. Note: the paper's own test is not validated against humans |
| **Do not trust FID alone** | The authors show FID can punish a correct result | When we evaluate Step 3, add attribute-based and fit-based checks (hem position, sleeve length) next to image-quality scores |
| **Modular pre-processing in front of a model** | Our pipeline is already staged | Same design idea: add a quality step (segmentation check, skin filter) before the heavy step |
| **A fast 2D preview option** | Step 3 needs CLO and takes minutes | A 2D diffusion try-on such as Leffa or CaP-VTON could give a quick, approximate preview image, clearly labelled as a preview (it cannot show true fit) |

**What not to take from it:** the paper's headline accuracy figures (they conflict), and any claim about fit, because it uses no body or garment measurements.
