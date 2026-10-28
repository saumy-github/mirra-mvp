"""Face reconstruction runner: 1-3 face photos -> face.glb (+ texture preview).

The website runs the same pipeline through worker.tasks.run_face_reconstruction;
this is for trying photos by hand:

    python face_reconstruction/run_face_reconstruction.py --front f.jpg [--left l.jpg --right r.jpg] --out face.glb
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_reconstruction.pipeline import reconstruct_face


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--front", required=True)
    p.add_argument("--left", help="head turned ~45° to the subject's left")
    p.add_argument("--right", help="head turned ~45° to the subject's right")
    p.add_argument("--out", default="face.glb")
    a = p.parse_args()
    photos = {k: v for k, v in (("front", a.front), ("left", a.left), ("right", a.right)) if v}
    glb, info = reconstruct_face(photos)
    Path(a.out).write_bytes(glb)
    print(json.dumps({**info, "out": a.out, "bytes": len(glb)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
