"""VW variant: fill the 6 slots CLO leaves alone from CLO's own weight model (table sampled in the Avatar Editor),
using the weight that best matches the size's bust/chest, waist and low hip. Compared with the truth mesh like e4."""
import sys
from exp_lib import *

group, pick = sys.argv[1], sys.argv[2]
A = ASSETS
cfg = {
    "female": dict(base=A / "Female" / "FV2.1_Mia.avt", tpl=FEM_RES / "mia-deafult-size.avs", U=[4, 5, 7, 9, 15, 47],
                   files=lambda: [p for p in sorted(glob.glob(str(A / "Female" / "Size" / "**" / "*.avs"), recursive=True)) if "Maternity" not in p and "Teenager" not in p and tmpl_id(p).endswith("_08")]),
    "male": dict(base=REPO / "clo_avatar_generation" / "input" / "base-1.avt", tpl=REPO / "clo_avatar_generation" / "input" / "CLO_Male_Default.avs", U=[4, 7, 9, 15, 47, 50],
                 files=lambda: [p for p in sorted(glob.glob(str(A / "Male" / "Size" / "**" / "*.avs"), recursive=True)) if "Teenager" not in p and tmpl_id(p).endswith("_07")]),
}[group]
sweep = json.loads((SCR / "results" / f"weight_sweep_{group}.json").read_text())
Ws = sorted(float(k) for k in sweep)
T = np.array([sweep[f"{w:g}"]["all"] for w in Ws])  # (n_weights, 57)


def table_at(w):
    return np.array([np.interp(w, Ws, T[:, k]) for k in range(57)])


files = cfg["files"]()
feats = {p: feats_avs(p) for p in files}
tests = [p for p in files if any(s in os.path.basename(p) for s in pick.split(","))]
res_name = f"weighttable_{group}"
res = json.loads((SCR / "results" / f"{res_name}.json").read_text()) if (SCR / "results" / f"{res_name}.json").exists() else {}
for p in tests:
    name = os.path.basename(p)[:-4]
    if name in res:
        continue
    S = feats[p]
    grid = np.arange(Ws[0], Ws[-1] + 0.01, 0.5)
    err = [sum((table_at(w)[i] - S[i]) ** 2 for i in (2, 6, 8)) for w in grid]
    w_hat = float(grid[int(np.argmin(err))])
    tw = table_at(w_hat)
    uvals = {s: float(tw[s]) for s in cfg["U"]}
    uvals[47] = float(tw[47]) * S[0] / tw[0] if 47 in uvals else None
    if group == "male":
        uvals[50] = float(tw[50])
    ch = {**{i: S[i] for i in DRIVEN}, **{s: v for s, v in uvals.items() if v is not None}}
    got_t, Vt = run_variant(cfg["base"], p, f"{group}_{name}_T2")
    avs = patch_avs(cfg["tpl"], ch, WORK / f"{group}_{name}_VW.avs")
    gotW, VW = run_variant(cfg["base"], avs, f"{group}_{name}_VW")
    out = {"weight_that_best_fits_kg": w_hat, "slot": truth_metrics(gotW, S), "mesh_vs_truth": vdist(VW, Vt),
           "bust_waist_hip_fit_error_cm": [round(float(tw[i] - S[i]), 1) for i in (2, 6, 8)]}
    res[name] = out; save(res_name, res)
    print(name, json.dumps(out), flush=True)
print("DONE", flush=True)
