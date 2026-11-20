import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from p19_common import *
L = s001_layouts()
for k, l in L.items():
    p = np.array(l.polygon())
    print(k, p.shape, p.min(0).round(1), p.max(0).round(1))
    for e in l.edges:
        print("   ", e.name, e.edge_type, np.round(e.start,1), np.round(e.end,1))
