import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
from cv_shape import garment_landmarks
d = load_mirra()
for c, v in d.items():
    r = garment_landmarks(v["mask"])
    print(c, r["ok"], r["methods"], r["flags"])
    print({k: [round(x) for x in p] for k, p in r["landmarks"].items()})
    print({k: len(p) for k, p in r["polygons"].items()})
