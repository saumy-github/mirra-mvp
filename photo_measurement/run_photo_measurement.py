"""Photo measurement runner: front + side photo + height -> measurements JSON.

The website runs the same pipeline through worker.tasks.run_photo_measurement;
this is for trying photos by hand:

    python photo_measurement/run_photo_measurement.py --front f.jpg --side s.jpg --height 170 --gender female
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from photo_measurement.pipeline import measure_photos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--front", required=True)
    p.add_argument("--side", required=True)
    p.add_argument("--height", type=float, required=True, help="barefoot height in cm")
    p.add_argument("--weight", type=float, help="kg; improves girths when given")
    p.add_argument("--gender", choices=["male", "female"])
    p.add_argument("--shoe-sole-cm", type=float, default=0.0, help="sole thickness if wearing shoes")
    p.add_argument("--out", help="also write the JSON here")
    a = p.parse_args()

    result = measure_photos(a.front, a.side, a.height, a.weight, a.gender, a.shoe_sole_cm)
    text = json.dumps(result, indent=2)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    for w in result["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
