"""P05: score every method folder of a try with evaluate.py and write a summary table.
    .venv/Scripts/python.exe product_ingestion/CV/scripts/p05_score_all.py try_02
Output: out/p05_design/<try>/scores.csv (rows = method x mask, columns = mean design metrics + per-photo F1@0.3)."""
import csv, subprocess, sys
from pathlib import Path
CV = Path(__file__).resolve().parents[1]
REPO = CV.parents[1]
try_name = sys.argv[1]
root = CV / "out/p05_design" / try_name
KEYS = ["design.f1@0.3", "design.f1@0.5", "design.precision@0.3", "design.recall@0.3", "design.pixel_iou",
        "design.type_accuracy_matched", "design.false_positive_on_plain", "design.colour_block_found"]
rows = []
for sub, mk in (("methods", "oracle"), ("methods_v0mask", "v0mask")):
    if not (root / sub).exists():
        continue
    for m in sorted(p.name for p in (root / sub).iterdir() if p.is_dir()):
        label = f"p05_{try_name}_{m}_{mk}"
        out = subprocess.run([str(REPO / ".venv/Scripts/python.exe"), str(CV / "scripts/evaluate.py"), "--pred", str(root / sub / m),
                              "--label", label, "--plan", "p05"], capture_output=True, text=True).stdout
        row = {"method": m, "mask": mk}
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[0] in KEYS:
                vals = parts[1:]
                row[parts[0]] = vals[-1]
                if parts[0] == "design.f1@0.3":
                    for c, v in zip(["c_001", "c_002", "c_003", "c_004", "c_005"], vals[:-1]):
                        row[f"f1_{c}"] = v
        rows.append(row)
cols = ["method", "mask"] + KEYS + [f"f1_c_00{i}" for i in range(1, 6)]
with open(root / "scores.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
g = lambda r, k: str(r.get(k, "-"))
for r in rows:
    print(f"{r['method']:22s} {r['mask']:7s} F1@.3={g(r,'design.f1@0.3'):>6s} F1@.5={g(r,'design.f1@0.5'):>6s} P={g(r,'design.precision@0.3'):>6s} R={g(r,'design.recall@0.3'):>6s} pxIoU={g(r,'design.pixel_iou'):>6s} typeAcc={g(r,'design.type_accuracy_matched'):>6s} FPplain={g(r,'design.false_positive_on_plain'):>6s} cb={g(r,'design.colour_block_found'):>6s}")
