"""Log free disk, RAM and commit every N seconds; exit with an alert when a limit is crossed.

Run in the background by the orchestrator:
  .venv/Scripts/python.exe product_ingestion/CV/scripts/resource_watch.py
Appends to out/resource_watch.log.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gpu_lock import free_memory_gb  # noqa: E402

LOG = HERE.parent / "out" / "resource_watch.log"
DISK_MIN_GB = 1.0   # the pagefile swings free disk by several GB; alert only when critical
COMMIT_MIN_GB = 1.0
INTERVAL = 60


def main() -> None:
    while True:
        disk = shutil.disk_usage("C:/").free / 1e9
        ram, commit = free_memory_gb()
        line = f"{time.strftime('%H:%M:%S')} disk_free_GB={disk:.2f} ram_avail_GB={ram:.2f} commit_free_GB={commit:.2f}"
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if disk < DISK_MIN_GB or commit < COMMIT_MIN_GB:
            print("ALERT " + line, flush=True)
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
