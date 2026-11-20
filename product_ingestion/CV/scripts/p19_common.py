"""Shared helpers for P19/P18 scripts: offline panel layouts, photo/mask loading."""
import sys, json, tempfile
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parents[3]          # repo root
PI = ROOT / "product_ingestion"
CV = PI / "CV"
OUT = CV / "out" / "p19_panel_maps"
if str(PI) not in sys.path:
    sys.path.insert(0, str(PI))


def s001_layouts():
    """Real size-s_001 tee layouts (cm) without MongoDB (values from panel_metadata.json of a real run)."""
    from garment_measurements import GarmentMeasurements
    from step_05_0_panel_generation_clo import generate_panels
    m = GarmentMeasurements(
        half_chest_width=52.0, garment_length=71.0, shoulder_width=46.0, neck_width=18.0,
        neck_depth_front=9.0, neck_depth_back=2.5, sleeve_length=21.0, bicep_width=21.8,
        armhole_depth=24.0, seam_allowance=1.0, fit_type="regular", ease_cm=4.0,
        body_height=175.0, body_chest=96.0, body_shoulder=44.0)
    import io, contextlib
    with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
        res = generate_panels(m, Path(td))
    return res.layouts


def load_mirra():
    lab = json.load(open(CV / "out/p00_baseline/reference/labels.json"))["cloths"]
    out = {}
    for c, v in lab.items():
        im = cv2.cvtColor(cv2.imread(v["image"]), cv2.COLOR_BGR2RGB)
        m = cv2.imread(v["garment_mask"], 0)
        if m.shape[:2] != im.shape[:2]:
            m = cv2.resize(m, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
        out[c] = dict(rgb=im, mask=(m > 127).astype(np.uint8) * 255, label=v)
    return out
