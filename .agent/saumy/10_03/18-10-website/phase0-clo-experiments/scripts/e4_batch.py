"""Ground-truth test of the .avs route: for a shipped CLO size S, compare
  T  = import the full shipped .avs (truth)
  V6 = default template with only the 6 driven slots set (CLO recomputes the rest)
  VH = V6 + ridge-predicted values for the slots CLO does not recompute (leave-one-out from the other sizes)
  VN = V6 + those slots copied from the nearest other shipped size (no regression)
  VM = (male only) V6 + the repo's current derived-size model for all derived slots
Usage: python e4_batch.py <group> <comma separated size-name substrings or 'all'>
"""
import sys
from exp_lib import *
from avatar_runtime.avs_patch import load_derived_model

group, pick = sys.argv[1], sys.argv[2]
A = ASSETS
G = {
    "female": dict(base=A / "Female" / "FV2.1_Mia.avt", tpl=FEM_RES / "mia-deafult-size.avs",
                   files=lambda: [p for p in sorted(glob.glob(str(A / "Female" / "Size" / "**" / "*.avs"), recursive=True)) if "Maternity" not in p and "Teenager" not in p and tmpl_id(p).endswith("_08")],
                   U=[4, 5, 7, 9, 15, 47]),
    "male": dict(base=REPO / "clo_avatar_generation" / "input" / "base-1.avt", tpl=REPO / "clo_avatar_generation" / "input" / "CLO_Male_Default.avs",
                 files=lambda: [p for p in sorted(glob.glob(str(A / "Male" / "Size" / "**" / "*.avs"), recursive=True)) if "Teenager" not in p and tmpl_id(p).endswith("_07")],
                 U=[4, 7, 9, 15, 47, 50]),
    "teen_f": dict(base=A / "Female" / "FV2.1_Luna_Teenager.avt", tpl=A / "Female" / "Size" / "CLO_Teenager_Default.avs",
                   files=lambda: [p for p in sorted(glob.glob(str(A / "Female" / "Size" / "**" / "*.avs"), recursive=True)) if "Teenager" in p],
                   U=None),
    "girl": dict(base=A / "Kid" / "KV1.1G_Melody_(7-20).avt", tpl=A / "Kid" / "Size" / "Girl" / "CLO_Girl_Default.avs",
                 files=lambda: sorted(glob.glob(str(A / "Kid" / "Size" / "Girl" / "*.avs"))), U=None),
    "boy": dict(base=A / "Kid" / "KV1.1B_Oliver_(7-20).avt", tpl=A / "Kid" / "Size" / "Boy" / "CLO_Boy_Default.avs",
                files=lambda: sorted(glob.glob(str(A / "Kid" / "Size" / "Boy" / "*.avs"))), U=None),
}
cfg = G[group]
files = cfg["files"]()
feats = {p: feats_avs(p) for p in files}
dflt = feats_avs(cfg["tpl"])
tests = files if pick == "all" else [p for p in files if any(s in os.path.basename(p) for s in pick.split(","))]
print(group, "sizes:", len(files), "tests:", [os.path.basename(p) for p in tests], flush=True)
model = load_derived_model() if group == "male" else None
U = cfg["U"]
res_path = f"{group}_e4"
res = json.loads((SCR / "results" / f"{res_path}.json").read_text()) if (SCR / "results" / f"{res_path}.json").exists() else {}
for p in tests:
    name = os.path.basename(p)[:-4]
    if name in res:
        continue
    S = feats[p]; six = [S[i] for i in DRIVEN]
    others_train = [q for q in files if q != p]
    train = [feats[q] for q in others_train]
    out = {}
    t0 = time.time()
    got_t, Vt = run_variant(cfg["base"], p, f"{group}_{name}_T")
    out["T"] = {"slot": truth_metrics(got_t, S)}
    avs6 = patch_avs(cfg["tpl"], {i: S[i] for i in DRIVEN}, WORK / f"{group}_{name}_V6.avs")
    got6, V6 = run_variant(cfg["base"], avs6, f"{group}_{name}_V6")
    if U is None:
        U = sorted(k for k in range(57) if k not in DRIVEN and k != 1 and abs(got6[k] - dflt[k]) < 0.1 and abs(S[k] - dflt[k]) > 0.3)
        print("  U slots determined from first V6:", U, flush=True)
    recomputed = [k for k in range(57) if k not in DRIVEN and k != 1 and abs(got6[k] - dflt[k]) >= 0.1]
    out["V6"] = {"slot": truth_metrics(got6, S), "mesh_vs_truth": vdist(V6, Vt), "n_recomputed_by_clo": len(recomputed),
                 "not_recomputed": [k for k in range(57) if k not in DRIVEN and k != 1 and k not in recomputed]}
    prU = predict_slots(train, six, U)
    avsH = patch_avs(cfg["tpl"], {**{i: S[i] for i in DRIVEN}, **{s: float(v) for s, v in zip(U, prU)}}, WORK / f"{group}_{name}_VH.avs")
    gotH, VH = run_variant(cfg["base"], avsH, f"{group}_{name}_VH")
    out["VH"] = {"U": U, "slot": truth_metrics(gotH, S), "mesh_vs_truth": vdist(VH, Vt)}
    # nearest neighbour on the six driven values
    T = np.array(train); sd = T[:, DRIVEN].std(0) + 1e-9
    dist = (((T[:, DRIVEN] - np.array(six)) / sd) ** 2).sum(1)
    nn = int(dist.argmin())
    avsN = patch_avs(cfg["tpl"], {**{i: S[i] for i in DRIVEN}, **{s: float(T[nn, s]) for s in U}}, WORK / f"{group}_{name}_VN.avs")
    gotN, VN = run_variant(cfg["base"], avsN, f"{group}_{name}_VN")
    out["VN"] = {"nearest": os.path.basename(others_train[nn]), "slot": truth_metrics(gotN, S), "mesh_vs_truth": vdist(VN, Vt)}
    if model is not None:
        x = (np.array(six) - np.array(model["mean"])) / np.array(model["std"])
        pm = np.r_[1.0, x] @ np.array(model["weights"])
        chm = {i: S[i] for i in DRIVEN}; chm.update({int(ix): float(v) for ix, v in zip(model["derived_indexes"], pm) if int(ix) != 1})
        gotM, VM = run_variant(cfg["base"], patch_avs(cfg["tpl"], chm, WORK / f"{group}_{name}_VM.avs"), f"{group}_{name}_VM")
        out["VM_current_model_leaky"] = {"slot": truth_metrics(gotM, S), "mesh_vs_truth": vdist(VM, Vt)}
    out["seconds"] = round(time.time() - t0)
    res[name] = out
    save(res_path, res)
    print(name, json.dumps({k: (v.get("mesh_vs_truth") if isinstance(v, dict) else v) for k, v in out.items()}), flush=True)
print("DONE", flush=True)
