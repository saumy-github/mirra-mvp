"""P17: fine-tune a small YOLO segmentation model on garment masks (one class "garment").

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p17_train.py [--model yolo26s-seg.pt] [--time 0.65] [--name run1]

Takes the GPU lock for the whole training. Weights/curves: out/p17_yolo_seg/runs/<name>/ .
The COCO weights are looked up in out/p17_yolo_seg/weights/ (downloaded there on first use, small models only).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out" / "p17_yolo_seg"
sys.path.insert(0, str(HERE))
from gpu_lock import gpu_lock  # noqa: E402

os.environ.setdefault("YOLO_AUTOINSTALL", "False")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolo26s-seg.pt")
    ap.add_argument("--time", type=float, default=0.65, help="training hours cap")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--name", default="run1")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--data", default=str(OUT / "dataset" / "data.yaml"))
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    (OUT / "weights").mkdir(parents=True, exist_ok=True)
    os.chdir(OUT / "weights")  # ultralytics downloads the .pt into the cwd
    from ultralytics import YOLO, settings
    settings.update({"datasets_dir": str(OUT / "dataset"), "runs_dir": str(OUT / "runs"), "sync": False})
    with gpu_lock("p17"):
        if a.resume:
            model = YOLO(str(OUT / "runs" / a.name / "weights" / "last.pt"))
            model.train(resume=True)
        else:
            model = YOLO(a.model)
            model.train(
                data=a.data, epochs=a.epochs, time=a.time, imgsz=a.imgsz,
                batch=a.batch, workers=a.workers, cache=False, device=0, seed=0, deterministic=False,
                project=str(OUT / "runs"), name=a.name, exist_ok=False, patience=15, amp=True,
                fliplr=0.5, degrees=0.0, mosaic=1.0, close_mosaic=5, plots=True, val=True,
                save_period=-1, single_cls=True, overlap_mask=True, mask_ratio=4,
            )
        import torch
        del model
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
