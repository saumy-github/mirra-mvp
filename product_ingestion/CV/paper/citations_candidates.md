# Candidate citations for the paper

*Prepared: 2026-11-20. For the user, who writes the paper. Check each entry against the original before citing.*

Course rule: the "inspiration" papers must be journal or magazine papers from 2024 to 2026. Tools such as SAM 2, CLIP, SigLIP and YOLO may be cited as software (Q5, answered yes). Classic method papers may be older.

## 1. Inspiration papers (journal or magazine, 2024 to 2026)
| Paper | Venue | Why it fits |
|---|---|---|
| Luo, Qu, Zhao, Zhang, Yang. "Deep Learning for 3D Fashion Design: A Survey From a Sewing-Pattern-Driven Perspective" | IEEE TCSVT, vol. 36, no. 4, 2026. DOI 10.1109/TCSVT.2025.3637565 | Frames our work as pattern-driven 3D design (pattern first, then simulation); its evaluation metrics (panel IoU, attribute accuracy) and limitations match ours. Explainer: `.agent/cv-course-project/papers/01-tcsvt-sewing-pattern-survey.md` |
| Lyu, Wang, Ye, Sun, Chao. "Body data-driven garment pattern construction in digital fashion innovations: a review" | Textile Research Journal 96(11-12), 2026, 1299-1335. DOI 10.1177/00405175251352800 | Says parametric patterns work best when measurements are read automatically from photos; supports the image-driven shape ratios (P06) and the parametric block. Explainer: `.agent/cv-course-project/papers/03-lyu-body-data-driven-pattern-construction-review.md` |
| Kim, Lee, Lee, Lee. "Clothing-Agnostic Pre-Inpainting Virtual Try-On" (CaP-VTON) | Electronics (MDPI) 14(23), 4710, 2025 | Uses human parsing (SCHP) to separate clothing from skin, as our P01/P04 use a clothes parser; its skin-tone extraction idea. Note: its abstract and body give conflicting accuracy numbers. Explainer: `.agent/cv-course-project/papers/02-cap-vton-clothing-agnostic-pre-inpainting.md` |
| Nikolaev, Roman, Makarov. "QuantFit-VTON: Measurement-Conditioned Diffusion Model for Predictable Garment Fit" | IEEE Access, 2026. DOI 10.1109/ACCESS.2026.3668411 | Measurement-driven fit, Mirra's overall aim (supporting citation; IEEE Access is lighter-reviewed) |
| Cannavò, Offre, Lamberti. "A Semiautomated Pipeline for the Creation of Virtual Fitting Room Experiences..." | IEEE Computer Graphics and Applications, 2024. DOI 10.1109/MCG.2024.3521716 | Motivation: the published version of a body-plus-garment virtual fitting pipeline |
| Mohammedkhan, Fleuren, Güven, Postma. "Inferring Body Measurements from 2D Images: A Comprehensive Review" | Journal of Imaging (MDPI), 2025. DOI 10.3390/jimaging11060205 | Related work on reading measurements from images |

More journal options are listed in `.agent/cv-course-project/01-paper-survey.md` (section 5: Topic 3 tables).

## 2. Classic method papers (for the methods compared)
| Method (where used) | Reference |
|---|---|
| Canny edge detector (P03, P05) | J. Canny, "A computational approach to edge detection", IEEE TPAMI 8(6), 1986 |
| LoG / zero crossings (P03) | D. Marr, E. Hildreth, "Theory of edge detection", Proc. Royal Society B 207, 1980 |
| Bilateral filter (P03) | C. Tomasi, R. Manduchi, ICCV 1998 (conference). Journal alternative: S. Paris, P. Kornprobst, J. Tumblin, F. Durand, "Bilateral filtering: theory and applications", Foundations and Trends in Computer Graphics and Vision 4(1), 2009 |
| CLAHE (P03) | K. Zuiderveld, "Contrast limited adaptive histogram equalization", Graphics Gems IV, 1994 (book chapter) |
| Retinex (P03) | E. Land, J. McCann, "Lightness and Retinex theory", J. Optical Society of America 61(1), 1971 |
| Homomorphic filtering (P03) | A. Oppenheim, R. Schafer, T. Stockham, "Nonlinear filtering of multiplied and convolved signals", Proc. IEEE 56(8), 1968 |
| Harris corners (P06) | C. Harris, M. Stephens, Alvey Vision Conference, 1988 (conference) |
| Shi-Tomasi (P06) | J. Shi, C. Tomasi, "Good features to track", CVPR 1994 (conference) |
| SIFT (P06, L1) | D. Lowe, "Distinctive image features from scale-invariant keypoints", IJCV 60(2), 2004 |
| ORB (P06) | E. Rublee et al., ICCV 2011 (conference) |
| Hough transform (P05, P06) | R. Duda, P. Hart, "Use of the Hough transformation to detect lines and curves in pictures", Communications of the ACM 15(1), 1972 |
| Gabor filters / texture segmentation (P05) | A. Jain, F. Farrokhnia, "Unsupervised texture segmentation using Gabor filters", Pattern Recognition 24(12), 1991 |
| Wavelets (P05) | S. Mallat, "A theory for multiresolution signal decomposition: the wavelet representation", IEEE TPAMI 11(7), 1989 |
| GrabCut / graph cut (P01) | C. Rother, V. Kolmogorov, A. Blake, "GrabCut", ACM TOG 23(3), 2004 (SIGGRAPH) |
| Mean shift (P01, P04) | D. Comaniciu, P. Meer, "Mean shift: a robust approach toward feature space analysis", IEEE TPAMI 24(5), 2002 |
| K-medoids (P04) | L. Kaufman, P. Rousseeuw, "Finding Groups in Data", Wiley, 1990 (book) |
| Silhouette score (P04) | P. Rousseeuw, "Silhouettes", J. Computational and Applied Mathematics 20, 1987 |
| Gaussian mixtures / BIC (P04) | G. Schwarz, "Estimating the dimension of a model", Annals of Statistics 6(2), 1978 |
| CIEDE2000 (all colour scores) | G. Sharma, W. Wu, E. Dalal, "The CIEDE2000 color-difference formula", Color Research & Application 30(1), 2005 |
| LDA (P07, P16) | R. Fisher, "The use of multiple measurements in taxonomic problems", Annals of Eugenics 7(2), 1936 |
| Thin-plate splines (P19) | F. Bookstein, "Principal warps: thin-plate splines and the decomposition of deformations", IEEE TPAMI 11(6), 1989 |
| Kendall's tau (metric agreement) | M. Kendall, "A new measure of rank correlation", Biometrika 30(1-2), 1938 |

## 3. Tools and models (cite as software; most come from conference or arXiv papers)
- SAM 2 (Ravi et al., 2024, arXiv 2408.00714); `facebook/sam2-hiera-large`.
- SegFormer (Xie et al., NeurIPS 2021); clothes-parsing weights `sayeed99/segformer_b3_clothes`.
- SigLIP 2 (Tschannen et al., 2025, arXiv 2502.14786); `google/siglip2-base-patch16-224`.
- Marqo-FashionSigLIP (Marqo, 2024; model card).
- CLIP (Radford et al., ICML 2021).
- Grounding DINO (Liu et al., ECCV 2024); `IDEA-Research/grounding-dino-tiny`.
- YOLO11/YOLO26 and YOLOE (Ultralytics, software).
- EasyOCR (JaidedAI, software; CRAFT detector: Baek et al., CVPR 2019).
- RMBG-1.4 (BRIA AI, model card).
- OpenCV, scikit-learn, scikit-image (software).

## 4. Datasets
| Dataset | Reference | Licence |
|---|---|---|
| Fashionpedia | Jia et al., ECCV 2020 (arXiv 2004.12276) | CC BY 4.0 |
| VITON-HD | Choi et al., CVPR 2021 | research only |
| DeepFashion In-shop | Liu et al., CVPR 2016 | research only |
| Fashion Product Images (Small) | Kaggle, P. Aggarwal | as on Kaggle |
