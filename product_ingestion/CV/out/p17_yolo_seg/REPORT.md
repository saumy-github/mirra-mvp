# P17 report: fine-tuned YOLO26s-seg for the garment outline

*Date: 2026-11-20. Written by the P17 sub-agent and saved here by the orchestrator. Numbers are from runs [V]; inferences are marked [I].*

## 1. Goal
- Fine-tune a small YOLO segmentation model on exact garment masks, with one class ("garment").
- Score it on P01's exact public test subsets and on the 5 Mirra photos with P01's scoring code.
- Try the fine-tuned YOLO box as a SAM 2 prompt.

## 2. Data and splits (`scripts/p17_build_dataset.py`, seed 0, CPU)
- **Sources:** VITON-HD parquet and Fashionpedia val polygons already in `data/`. No new data downloads.
- **Test exclusions:** P01's 150 VITON rows and 100 Fashionpedia photos are excluded from train and val (asserted in code).
- **Labels:**
  - VITON product photos: `cloth_mask > 127`.
  - VITON person photos: parse labels {5, 21, 22}.
  - Fashionpedia: the largest upper garment when P01 would accept the photo. Otherwise the union of upper-body garments of at least 3 % of the image (training only), because only 175 Fashionpedia photos pass P01's strict rule after test exclusion.
  - Test labels are untouched.
- **Format:** JPEG at 640 px longest side or smaller; normalised polygons, with components under 1.5 % dropped. Splits are by VITON row.

| Split | Images |
|---|---|
| Full dataset: train | 1,904 (500 VITON product, 986 VITON person, 418 Fashionpedia) |
| Full dataset: val | 180 (70 / 70 / 40) |
| **Training list used** (`dataset/train_small.txt`, after the memory limit) | **1,468** (350 product, 700 person, 418 street) |

- **Earlier builds kept:** `dataset_try01_strict_fp/` and `dataset_try02_fp8pct/` had too few street photos (79 and 135).

## 3. Commands
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/p17_build_dataset.py
.venv/Scripts/python.exe product_ingestion/CV/scripts/p17_make_small_list.py
.venv/Scripts/python.exe product_ingestion/CV/scripts/p17_train.py --name run2 --data <abs path>/out/p17_yolo_seg/dataset/data_small.yaml --workers 0 --batch 8 --imgsz 512 --time 0.5 --epochs 40
.venv/Scripts/python.exe product_ingestion/CV/scripts/p17_eval.py --weights out/p17_yolo_seg/runs/run2-2/weights/best.pt --imgsz 512 --sam2
.venv/Scripts/python.exe product_ingestion/CV/scripts/evaluate.py --pred out/p17_yolo_seg/mirra --label p17_yolo_seg_finetuned --plan p17
.venv/Scripts/python.exe product_ingestion/CV/scripts/evaluate.py --pred out/p17_yolo_seg/mirra_sam2 --label p17_yolo_box_pt_sam2 --plan p17
```
- **`--data` must be absolute:** `p17_train.py` changes directory. The failed first launch left an empty `runs/run2/`; the real run is `runs/run2-2/`.
- **GPU lock:** held for training and evaluation.

## 4. Training
- **Model:** `yolo26s-seg.pt` (COCO pretrained, 11.4 M parameters, 22 MB), downloaded to `out/p17_yolo_seg/weights/`.
- **Settings:**
  - imgsz 512, batch 8, workers 0, cache False, AMP, seed 0, auto optimiser, lr0 0.01
  - mosaic 1.0 (off for the last 5 epochs), fliplr 0.5, patience 15, single class
  - time cap 0.5 h, which gave 46 epochs in about 30 min
- **Resources:** peak GPU memory 2.4 to 2.8 GB.
- **Val masks (180 images):** P 0.959, R 0.872, mAP50 0.966, mAP50-95 0.901.
- **Convergence:** the loss was still falling at the end, and val mAP50-95 reached about 0.90 around epoch 28. The time cap ended training.
- **Files:** curves and checks in `runs/run2-2/` (`results.csv`, `results.png`, PR and F1 curves, confusion matrices, `val_batch*_pred.jpg`, `weights/best.pt`, `weights/last.pt`); log `train_run2.log`.
- **Downloads by Ultralytics:** `YOLO_AUTOINSTALL=False`, and no pip installs. It downloaded the weights, `Arial.ttf` (user AppData Roaming Ultralytics folder) and the AMP-check model.

## 5. Evaluation protocol
- **Scoring:** P01's subsets and scoring (`evaluate.mask_metrics` at longest side 512); a missing mask counts as IoU 0, and failure means IoU < 0.1.
- **Inference:** conf 0.25, imgsz 512, retina masks.
- **Time:** YOLO only, on a shared GPU.
- **Variants:** `top1` (highest confidence), `union` (all instances), `largest` (largest instance).
- **Variant choice:** made on the val split, never on test. Val macro IoU: top1 0.877, union 0.884, largest 0.886, so **`largest`** was chosen; this is a near tie.

## 6. Results (public test sets: 150 VITON product, 150 VITON person, 100 Fashionpedia street)

| Method | VITON product | VITON person | Street | Macro IoU | Macro BF1@1% | Failures | s/img |
|---|---|---|---|---|---|---|---|
| **P17 YOLO26s-seg, `largest` (val-chosen)** | 0.979 | 0.901 | 0.788 | **0.889** | 0.891 | 1.8 % | 0.029 |
| P17 `union` (best on test, chosen after seeing it) | 0.979 | 0.912 | 0.810 | 0.9005 | 0.903 | 1.1 % | 0.029 |
| P17 `top1` | 0.979 | 0.889 | 0.776 | 0.881 | 0.886 | 1.8 % | 0.029 |
| P17 YOLO box → SAM 2 | 0.944 | 0.899 | 0.792 | 0.878 | 0.877 | 2.4 % | 0.54 |
| P17 YOLO box + point → SAM 2 | 0.947 | 0.897 | 0.801 | 0.882 | 0.879 | 2.4 % | 0.57 |
| P01 v1 (SegFormer box + point → SAM 2) | 0.936 | 0.893 | 0.838 | 0.889 | 0.884 | 1.1 % | 0.59 |
| P01 v0 (old pipeline) | 0.932 | 0.775 | 0.562 | 0.756 | 0.736 | 8.0 % | 0.55 |
| P01 SAM 2 + Grounding DINO box | 0.948 | 0.861 | 0.840 | 0.883 | 0.884 | 2.7 % | 0.51 |
| P01 SegFormer alone | 0.921 | 0.889 | 0.838 | 0.883 | 0.860 | 1.3 % | 0.09 |
| P01 YOLOE, 5 prompts (zero-shot) | 0.842 | 0.869 | 0.210 | 0.641 | 0.627 | 26.6 % | 0.30 |
| P01 YOLO person mask minus skin (zero-shot) | 0.557 | 0.866 | 0.831 | 0.751 | 0.713 | 12.7 % | 0.13 |

Per-set details are in `public_scores.csv`; per-image rows are in `per_image_p17_yolo_seg_finetuned.csv`.

**Mirra photos** (5, approximate references; rows in `results/mirra_scores.csv`):

| Method | Mean IoU | c_001 | c_002 | c_003 | c_004 | c_005 |
|---|---|---|---|---|---|---|
| P17 YOLO `largest` (`p17_yolo_seg_finetuned`) | 0.890 | 0.982 | 0.968 | 0.564 | 0.968 | 0.970 |
| P17 YOLO box + point → SAM 2 (`p17_yolo_box_pt_sam2`) | 0.896 | 0.997 | 0.964 | 0.540 | 0.989 | 0.989 |
| P01 v1 | 0.907 | 0.997 | 0.997 | 0.562 | 0.989 | 0.989 |
| P01 v1_all | 0.982 | 0.997 | 0.997 | 0.939 | 0.989 | 0.987 |
| P01 v0 | 0.700 | 1.000 | 0.728 | 0.785 | 0.592 | 0.395 |

## 7. What worked and what did not
1. **A small fine-tuned model matches the best zero-shot pipeline on the public sets:**
   - `largest` 0.889, the same as v1, with BF1 0.891 against 0.884;
   - about 20 times faster with one model;
   - it beats every zero-shot YOLO variant by a wide margin.
2. **Where it gains:** flat product photos (0.979 against 0.936) and photos of people (0.901 against 0.893). **Where it loses:** street photos (0.788 against 0.838), which have the least and noisiest training data.
3. **The result is in-domain:** train and test come from the same datasets. VITON product photos are very uniform, so the 0.979 says little about unseen product photos. [I]
4. **YOLO box → SAM 2:** it does not help on public data (0.878 to 0.882), but it sharpens Mirra edges (leakage 0.013 → 0.001).
5. **c_003 is not fixed (0.564):** no training label has a coloured lower half like this.
6. **Instance variant choice is fragile:** val differences are under 0.002, test differences 0.011. [I]

## 8. Issues
- **run1:** stopped by the orchestrator because of memory (1,904 images, imgsz 640, batch 12, 1 worker; stopped after 3 epochs). Kept in `runs/run1/` and `train_run1.log`; not used.
- **First run2 launch:** a relative `--data` path failed; the empty `runs/run2/` is harmless.
- **Disk:** about 500 MB in total (runs 270 MB, weights 23 MB, three dataset folders 206 MB). The two earlier dataset builds (120 MB) can be freed if space is needed.

## 9. Recommendation
- **Do not replace v1 yet:** the model ties v1 overall, is weaker on street photos, and has the same c_003 failure.
- **For the paper:** report `largest` (0.889, val-chosen) as the headline and `union` (0.9005) only as a post-hoc variant, with the in-domain caveat. Suggested framing: "a small fine-tuned model reaches the quality of the SegFormer + SAM 2 pipeline on in-domain data at about 5 % of the time".
- **Next steps if wanted:** add colour-block and street training photos; use the YOLO box as a fast fallback.
