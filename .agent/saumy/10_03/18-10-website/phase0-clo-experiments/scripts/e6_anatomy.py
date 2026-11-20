"""Where do CLO's body measurements sit on the real mesh, and which hip is the 'fullest'?
Exports the default avatar as GLB, slices it at CLO's own measurement heights, and compares the tape-style
(convex hull) perimeter of each slice with the circumference CLO reports in the size block."""
import sys
from exp_lib import *
from scipy.spatial import ConvexHull

which = sys.argv[1]  # female | male
if which == "female":
    base, tpl = ASSETS / "Female" / "FV2.1_Mia.avt", FEM_RES / "mia-deafult-size.avs"
else:
    base, tpl = REPO / "clo_avatar_generation" / "input" / "base-1.avt", REPO / "clo_avatar_generation" / "input" / "CLO_Male_Default.avs"
S = feats_avs(tpl)
fresh(base)
V = mesh_vertices(f"anat_{which}")
ytop = float(V[:, 1].max())
print(which, "mesh top %.2f cm, floor %.2f cm" % (ytop * 100, V[:, 1].min() * 100), flush=True)


def circ(y, half=0.004):
    pts = V[np.abs(V[:, 1] - y) < half][:, [0, 2]]
    if len(pts) < 10:
        return None
    order = np.argsort(pts[:, 0]); xs = pts[order, 0]
    cuts = np.where(np.diff(xs) > 0.03)[0]
    groups = np.split(order, cuts + 1)
    keep = [g for g in groups if np.abs(pts[g, 0]).min() < 0.17]
    sel = np.concatenate(keep)
    h = ConvexHull(pts[sel])
    return float(h.area * 100.0)  # perimeter in 2-D hull .area is the perimeter (m -> cm)


rows = {}
names = {21: ("Bust height", 2), 22: ("Under Bust height", 5), 23: ("Waist height", 6), 24: ("High Hip height", 7), 25: ("Low Hip height", 8)}
floor = 0.0  # GLB y = 0 is the ground; the lowest vertex can be below it (shoes, feet)
for hi, (nm, ci) in names.items():
    y = floor + S[hi] / 100.0
    c_mesh = circ(y)
    rows[nm] = {"height_cm_from_floor": round(S[hi], 1), "CLO_circumference_cm": round(S[ci], 1), "mesh_slice_perimeter_cm": None if c_mesh is None else round(c_mesh, 1)}
    print(nm, rows[nm], flush=True)
# scan the hip zone for the fullest section
scan = []
for h in np.arange(S[25] - 8, S[23] + 1, 1.0):
    cc = circ(floor + h / 100.0)
    if cc:
        scan.append((round(float(h), 1), round(cc, 1)))
best = max(scan, key=lambda t: t[1])
rows["hip_zone_scan"] = scan
rows["fullest_section"] = {"height_cm_from_floor": best[0], "perimeter_cm": best[1], "below_waist_cm": round(S[23] - best[0], 1)}
rows["clo_gaps_below_waist_cm"] = {"high_hip": round(S[23] - S[24], 1), "low_hip": round(S[23] - S[25], 1)}
rows["height_slot_cm"] = round(S[0], 1)
rows["mesh_top_cm_above_floor"] = round((ytop - floor) * 100, 1)
print("fullest:", rows["fullest_section"], "CLO gaps below waist:", rows["clo_gaps_below_waist_cm"], flush=True)
save(f"anatomy_{which}", rows)
print("DONE")
