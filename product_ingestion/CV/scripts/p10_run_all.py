"""P10 second pass: run the full product-ingestion pipeline on the 5 Mirra photos with the final defaults,
convert the runs to the scoring format and score them.

Holds the GPU lock for the whole batch (one photo at a time), writes into a NEW runs folder so the first
pass (out/p10_pipeline_runs/) is kept.

Run:  .venv/Scripts/python.exe product_ingestion/CV/scripts/p10_run_all.py --runs out/p10_pipeline_runs_v2 --label p10_final_pipeline_v2
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CV = HERE.parent
REPO = CV.parents[1]
sys.path.insert(0, str(HERE))
from gpu_lock import gpu_lock  # noqa: E402

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
CLOTHS = ["c_001", "c_002", "c_003", "c_004", "c_005"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="out/p10_pipeline_runs_v2", help="runs folder, relative to the CV folder")
    ap.add_argument("--label", default="p10_final_pipeline_v2")
    ap.add_argument("--no-attributes", action="store_true")
    args = ap.parse_args()
    runs = CV / args.runs
    runs.mkdir(parents=True, exist_ok=True)
    log = runs / "run_all_5.log"
    codes = {}
    with gpu_lock("p10", timeout_s=3 * 3600):
        with log.open("a", encoding="utf-8") as fh:
            for c in CLOTHS:
                fh.write(f"===== {c} {time.strftime('%H:%M:%S')}\n"); fh.flush()
                cmd = [PY, str(REPO / "product_ingestion" / "run_product_ingestion.py"),
                       "--cloth-id", c, "--size-id", "s_001", "-o", str(runs)]
                if args.no_attributes:
                    cmd.append("--no-attributes")
                codes[c] = subprocess.run(cmd, cwd=str(REPO), stdout=fh, stderr=subprocess.STDOUT).returncode
                fh.write(f"===== {c} exit {codes[c]} {time.strftime('%H:%M:%S')}\n"); fh.flush()
    print("exit codes:", codes)
    std = runs / "standard"
    subprocess.run([PY, str(HERE / "p10_run_to_standard.py"), "--runs", str(runs), "--out", str(std)], check=True)
    subprocess.run([PY, str(HERE / "evaluate.py"), "--pred", str(std), "--label", args.label, "--plan", "p10"], check=True)


if __name__ == "__main__":
    main()
