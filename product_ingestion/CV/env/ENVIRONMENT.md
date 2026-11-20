# Python environment snapshot and restore guide

*Snapshot taken: 2026-11-20, before any CV research code ran*
*Environment: repo `.venv`, Python 3.12.10, pip 26.0.1*

During the CV research I may upgrade or add packages (user's permission, 2026-11-20). After the research the user restores the environment from this snapshot. Every package change made during the research is logged in section 4.

## 1. Snapshot files

| File | What it is |
|---|---|
| `pip-freeze-2026-11-20.txt` | `pip freeze` of the working `.venv` on 2026-11-20 (176 packages). `pip check` reported no broken requirements. This is the state to return to. |

Key versions in the snapshot:

| Package | Version | Note |
|---|---|---|
| torch | 2.4.1+cu121 | CUDA 12.1 build (GPU); swapped from 2.4.1+cpu earlier the same day |
| torchvision | 0.19.1+cu121 | CUDA build |
| transformers | 4.56.0 | SAM 2 support |
| numpy | 1.26.4 | pinned in `requirements.txt` |
| opencv-python / opencv-python-headless | 4.10.0.84 / 4.11.0.86 | |
| scikit-learn | 1.5.1 | |
| rembg | 2.0.67 | U²-Net fallback; newer versions need numpy 2.3+ |
| ultralytics | 8.4.215 | added 2026-11-20 |
| easyocr | 1.7.2 | added 2026-11-20 |
| open_clip_torch | 3.1.0 | added 2026-11-20 (4.x would pull in torch 2.15) |

## 2. How to restore the snapshot

Run from the repo root (PowerShell or Git Bash):

```
.venv/Scripts/python.exe -m pip install --no-deps "torch==2.4.1+cu121" "torchvision==0.19.1+cu121" --index-url https://download.pytorch.org/whl/cu121
.venv/Scripts/python.exe -m pip install -r product_ingestion/CV/env/pip-freeze-2026-11-20.txt --extra-index-url https://download.pytorch.org/whl/cu121
.venv/Scripts/python.exe -m pip check
```

Then remove any package listed in section 4 as *added during research* that is not in the snapshot:

```
.venv/Scripts/python.exe -m pip uninstall -y <package> ...
```

## 3. The state before the CV work started (for reference)

Before 2026-11-20 the `.venv` had the CPU builds `torch==2.4.1+cpu` and `torchvision==0.19.1+cpu`, and none of `ultralytics`, `ultralytics-thop`, `ultralytics-platform`, `polars`, `polars-runtime-32`, `nvidia-ml-py`, `easyocr`, `ninja`, `pyclipper`, `python-bidi`, `shapely`, `open_clip_torch`, `ftfy`, `timm`. All other packages were unchanged by the setup steps. To go back that far:

```
.venv/Scripts/python.exe -m pip install --no-deps "torch==2.4.1+cpu" "torchvision==0.19.1+cpu" --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python.exe -m pip uninstall -y ultralytics ultralytics-thop ultralytics-platform polars polars-runtime-32 nvidia-ml-py easyocr ninja pyclipper python-bidi shapely open_clip_torch ftfy timm
```

## 4. Package changes during the research

| Date | Change | Why | Restore |
|---|---|---|---|
| *2026-11-20* | Snapshot taken | Baseline for restoring | - |
| *2026-11-20 ~10:00* | `clip` 1.0 (and `regex`) installed automatically by Ultralytics the first time YOLOE text prompts ran (P01); not requested by me. torch, numpy and transformers unchanged (checked) | Needed by YOLOE text prompts | `pip uninstall -y clip regex` (check `regex` was not there before: it is not in `pip-freeze-2026-11-20.txt`) |
| *2026-11-20 09:25* | Added `PyWavelets` 1.8.0 (1.10 would also install, but 1.8 is the safe choice with NumPy 1.26) | Wavelet (DWT) texture features for design regions (P05, syllabus Unit II) | `pip uninstall -y PyWavelets` |
| *2026-11-20* | Added `pyarrow` 19.0.1 (26.0.1 was tried first and replaced: it needs NumPy 2) | Read the parquet datasets | `pip uninstall -y pyarrow` |
| *2026-11-20* | Added `pywinauto` 0.6.9 (with `comtypes` 1.5.0, `pywin32` 312) | Automates the CLO menu click that starts the REST plugin (P20); torch and numpy unchanged | `pip uninstall -y pywinauto comtypes pywin32` |
