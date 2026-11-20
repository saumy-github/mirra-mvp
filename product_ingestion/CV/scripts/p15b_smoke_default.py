"""P15b: smoke test of extract_design() default (v4_relabel) on c_004 with the v1 mask, CPU only (no gpu_lock needed)."""
from p15b_common import *  # noqa
import cv_design_regions as cvd
import step_04_0_design_extraction as s4
d = load_inputs("v1")["c_004"]
rgba = np.dstack([d["rgb"], d["mask"].astype(np.uint8) * 255])
cvd.RELABEL_DEVICE = "cpu"
r = s4.extract_design(rgba)
print(s4.DEFAULT_METHOD, r.method, r.message)
for x in r.regions: print("  ", x["type"], [round(v) for v in x["box"]], x["source"])
r0 = s4.extract_design(rgba, method="v0"); print("v0", r0.method, r0.has_design)
