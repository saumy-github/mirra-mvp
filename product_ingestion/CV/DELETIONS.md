# Deletion log

*Started: 2026-11-20*

If disk space runs out during the research, I may delete **only**:
1. Python packages in the repo `.venv`.
2. Datasets I downloaded for this work (in `data/`).
3. Earlier versions of models I trained during this work.
4. Open-weight pretrained models or algorithm files I downloaded and used (for example in the Hugging Face cache or the Ultralytics weights folder).

**Nothing that existed before this work started may be deleted** (code, inputs, earlier runs, notes, or files outside the list above). Experiment outputs in `out/` are never deleted.

Every deletion is recorded below, before or right after it happens.

| Date | What was deleted | Category (1 to 4) | Size | Why | Can it be got back? |
|---|---|---|---|---|---|
| *2026-11-20 07:05* | `data/deepfashion2_upper_masks/` (Hugging Face `zyuzuguldu/deepfashion2-upper-body-masks`) | 2 (dataset I downloaded) | 397 MB | Disk C: fell to 1.7 GB free; this copy holds masks only, no photos, so it was unusable (`ISSUES.md` I6) | Yes: re-download from Hugging Face |
| *2026-11-20 07:05* | `data/fashionpedia/val_test2020.zip` (the zip only; the unpacked photos in `data/fashionpedia/test/` are kept) | 2 (dataset I downloaded) | 236 MB | Disk C: at 1.7 GB free; the zip was already unpacked | Yes: `https://s3.amazonaws.com/ifashionist-dataset/images/val_test2020.zip` |
| *2026-11-20 ~09:45* | Partial Hugging Face cache downloads (`*.incomplete` blobs) left by the P07 agent's own killed downloads | 4 (open-weight model files downloaded during this work) | about 700 MB | Reported by the P07 agent: unfinished files from downloads stopped during the memory emergency, removed before re-downloading | Yes: re-downloaded on next use |
| *2026-11-20 09:30* | `data/fashionpedia_train/` (train annotations `instances_attributes_train2020.json` and a few train images, fetched by the P07 agent) | 2 (dataset downloaded during this work) | 740 MB | Disk C: at 0.82 GB free while the pagefile grew; P07 is paused and can use the val labels | Yes: `https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_train2020.json` |
| *2026-11-20 07:35* | Hugging Face cache `models--openai--clip-vit-large-patch14` | 4 (open-weight model I downloaded tonight and used) | 1.6 GB | Disk C: fell to 0.18 GB free when the Windows pagefile grew by 3.5 GB under memory pressure; CLIP-L was only a baseline backbone, dropped from P16 and P07 | Yes: re-downloads from Hugging Face on next use |
| *2026-11-20 07:05* | `data/dresscode_test/` (Hugging Face `zhengchong/DressCode-Test`, still packed) | 2 (dataset I downloaded) | 1.3 GB | Disk C: at 1.7 GB free; not used yet (only P14 would use it, later) | Yes: re-download from Hugging Face if P14 needs it and space allows |

Earlier, separate clean-up (before these rules, done on the user's direct instruction, 2026-11-20): heavy files in `clo_avatar_generation/output/` run folders, recorded in `clo_avatar_generation/runs_summary.md`.
