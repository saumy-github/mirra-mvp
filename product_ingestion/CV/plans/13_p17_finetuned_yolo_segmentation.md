# 13 · P17 Training our own garment segmentation model (fine-tuned YOLO26s-seg)

*Status: done, accepted as a comparison result; not made the default (v1_auto stays)*
*Date: 2026-11-20, about 14:10 to 15:12 (training 14:30 to 15:00 after a memory restart)*
*Agent report: `out/p17_yolo_seg/REPORT.md`; outputs in `out/p17_yolo_seg/`.*

## Goal
Find out whether a small segmentation model trained on exact garment masks can replace the zero-shot model chain (clothes parser + SAM 2) for the garment outline.

## What was done [V]
- **Model:** fine-tuned YOLO26s-seg (11.4 M parameters, COCO-pretrained), with one class, "garment".
- **Training data:** 1,468 photos with exact masks: VITON-HD product photos, VITON-HD photos of people, and Fashionpedia street photos. P01's test photos were excluded.
- **Training run:** 46 epochs in 30 minutes on the RTX 4050 (6 GB), restarted once with low-memory settings after the memory emergency (`ISSUES.md` I17).
- **Fair comparison:** the instance variant (`largest`) was chosen on the validation split, never on the test sets. The model was scored with P01's exact test subsets and scoring code.

## Results [V]

| Method | Product | Person | Street | Macro IoU | Failures | Time per photo |
|---|---|---|---|---|---|---|
| v0 (old pipeline) | 0.932 | 0.775 | 0.562 | 0.756 | 8.0 % | 0.55 s |
| Zero-shot YOLOE (text prompts) | 0.842 | 0.869 | 0.210 | 0.641 | 26.6 % | 0.30 s |
| Zero-shot YOLO person mask minus skin | 0.557 | 0.866 | 0.831 | 0.751 | 12.7 % | 0.13 s |
| v1 (parser box + point → SAM 2) | 0.936 | 0.893 | 0.838 | 0.889 | 1.1 % | 0.59 s |
| **Fine-tuned YOLO26s-seg (ours)** | **0.979** | **0.901** | 0.788 | **0.889** | 1.8 % | **0.03 s** |
| Fine-tuned YOLO box + point → SAM 2 | 0.947 | 0.897 | 0.801 | 0.882 | 2.4 % | 0.57 s |

- **Mirra photos:** mean IoU 0.890, against 0.907 for v1. c_003 has the same lost lower half (0.564).

## Judgement
- **Accepted as evidence; not adopted as the default.**
  - It ties v1 overall, is better on product photos and photos of people, and is clearly worse on street photos.
  - It has the c_003 failure that P15a's `v1_auto` fixes.
- **For the paper:** training beats prompting.
  - Zero-shot YOLO variants reach only 0.64 to 0.75; the same model family fine-tuned on 1,468 labelled photos reaches 0.889.
  - That equals a two-model zero-shot chain at about 5 % of its time.
- **Caveat:** the test photos come from the same datasets as the training photos (in-domain), so the 0.979 on product photos says little about new shops' photos.

## Next (not done tonight)
- Add labelled colour-block and street photos, then retrain.
- The model could serve as a fast fallback or a fast preview outline.
