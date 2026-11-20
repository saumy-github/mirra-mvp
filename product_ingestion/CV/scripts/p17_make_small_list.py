"""P17: write the <=1,500-image train list (low-memory restart): 350 VITON product + 700 VITON person + all Fashionpedia (418)."""
import random
from pathlib import Path
D = Path(__file__).resolve().parents[1] / "out" / "p17_yolo_seg" / "dataset"
tr = sorted((D / "images" / "train").glob("*.jpg"))
rng = random.Random(0)
by = {k: [p for p in tr if p.name.startswith(k)] for k in ("vc_", "vp_", "fp_")}
sel = rng.sample(by["vc_"], 350) + rng.sample(by["vp_"], 700) + by["fp_"]
(D / "train_small.txt").write_text("\n".join(p.as_posix() for p in sel), encoding="utf-8")
(D / "data_small.yaml").write_text(
    f"path: {D.as_posix()}\ntrain: {(D / 'train_small.txt').as_posix()}\nval: images/val\nnames:\n  0: garment\n", encoding="utf-8")
print(len(sel), {k: len(v) for k, v in by.items()})
