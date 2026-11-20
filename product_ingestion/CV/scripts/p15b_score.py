"""P15b step 4: score every <out>/<maskset>/<method> folder with evaluate.py (labels p15b_<method>_<maskset>, plan p15b)
and write <out>/scores.csv.

    .venv/Scripts/python.exe product_ingestion/CV/scripts/p15b_score.py try_01
"""
import csv, subprocess, sys
from p15b_common import *  # noqa
try_name = sys.argv[1]
root = OUT / try_name
KEYS = ["design.f1@0.3", "design.f1@0.5", "design.precision@0.3", "design.recall@0.3", "design.pixel_iou",
        "design.type_accuracy_matched", "design.false_positive_on_plain", "design.colour_block_found"]
rows = []
for ms in MASKSETS:
    if not (root / ms).exists():
        continue
    for m in sorted(p.name for p in (root / ms).iterdir() if p.is_dir()):
        label = f"p15b_{m}_{ms}"
        out = subprocess.run([str(REPO / ".venv/Scripts/python.exe"), str(CV / "scripts/evaluate.py"), "--pred", str(root / ms / m),
                              "--label", label, "--plan", "p15b"], capture_output=True, text=True).stdout
        row = {"method": m, "maskset": ms}
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[0] in KEYS:
                vals = parts[1:]
                row[parts[0]] = vals[-1]
                if parts[0] == "design.f1@0.3":
                    for c, v in zip(CLOTHS, vals[:-1]):
                        row[f"f1_{c}"] = v
        rows.append(row)
cols = ["method", "maskset"] + KEYS + [f"f1_{c}" for c in CLOTHS]
with open(root / "scores.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
g = lambda r, k: str(r.get(k, "-"))
for r in rows:
    print(f"{r['method']:11s} {r['maskset']:7s} F1@.3={g(r,'design.f1@0.3'):>6s} F1@.5={g(r,'design.f1@0.5'):>6s} P={g(r,'design.precision@0.3'):>6s} R={g(r,'design.recall@0.3'):>6s} pxIoU={g(r,'design.pixel_iou'):>6s} typeAcc={g(r,'design.type_accuracy_matched'):>6s} FPplain={g(r,'design.false_positive_on_plain'):>6s} cb={g(r,'design.colour_block_found'):>6s}  per-photo: " + " ".join(g(r, f'f1_{c}') for c in CLOTHS))
