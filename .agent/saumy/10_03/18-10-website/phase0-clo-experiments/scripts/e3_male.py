from exp_lib import *
from avatar_runtime.avs_patch import load_derived_model
MS = ASSETS / "Male" / "Size"
BASE = REPO / "clo_avatar_generation" / "input" / "base-1.avt"
TPL = REPO / "clo_avatar_generation" / "input" / "CLO_Male_Default.avs"
model = load_derived_model()
files = [p for p in sorted(glob.glob(str(MS / "**" / "*.avs"), recursive=True)) if tmpl_id(p).endswith("_07")]
print("male _07 files:", [os.path.basename(p) for p in files], flush=True)
feats = {p: feats_avs(p) for p in files}
dflt = feats_avs(TPL)
sel = [p for p in files if any(k in p for k in ("R_34", "R_40", "R_46", "R_52"))]
res = {}
Ucand = None
for p in sel:
    S = feats[p]; six = [S[i] for i in DRIVEN]; name = os.path.basename(p)[:-4]
    train = [feats[q] for q in files if q != p]
    out = {}
    # truth
    fresh(BASE); apply_avs(p); got_t = readout(f"h_{name}_T"); Vt = mesh_vertices(f"m_h_{name}_T")
    out["T"] = {"slot": truth_metrics(got_t, S)}
    # six only
    avs6 = patch_avs(TPL, {i: S[i] for i in DRIVEN}, WORK / f"h_{name}_V6.avs")
    fresh(BASE); apply_avs(avs6); got6 = readout(f"h_{name}_V6"); V6 = mesh_vertices(f"m_h_{name}_V6")
    unchanged = [k for k in range(57) if k not in DRIVEN and k != 1 and abs(got6[k] - dflt[k]) < 0.1 and abs(S[k] - dflt[k]) > 0.3]
    recomputed = [k for k in range(57) if k not in DRIVEN and k != 1 and abs(got6[k] - dflt[k]) >= 0.1]
    out["V6"] = {"slot": truth_metrics(got6, S), "mesh_vs_truth": vdist(V6, Vt), "slots_CLO_recomputed": len(recomputed), "slots_left_at_default_but_should_differ": unchanged}
    print(name, "V6", json.dumps(out["V6"]), flush=True)
    U = sorted(set(unchanged)) if not Ucand else Ucand
    Ucand = U if Ucand is None else Ucand
    # six + ridge on U slots (LOO from other male sizes)
    prU = predict_slots(train, six, U)
    avsH = patch_avs(TPL, {**{i: S[i] for i in DRIVEN}, **{s: float(v) for s, v in zip(U, prU)}}, WORK / f"h_{name}_VH.avs")
    fresh(BASE); apply_avs(avsH); gotH = readout(f"h_{name}_VH"); VH = mesh_vertices(f"m_h_{name}_VH")
    out["VH"] = {"U": U, "slot": truth_metrics(gotH, S), "mesh_vs_truth": vdist(VH, Vt)}
    print(name, "VH", json.dumps(out["VH"]), flush=True)
    # six + current model (all derived) -- note: model trained incl. this size (leak)
    x = (np.array(six) - np.array(model["mean"])) / np.array(model["std"])
    feat = np.r_[1.0, x]; Wm = np.array(model["weights"]); pm = feat @ Wm
    chm = {i: S[i] for i in DRIVEN}; chm.update({int(ix): float(v) for ix, v in zip(model["derived_indexes"], pm) if int(ix) != 1})
    avsM = patch_avs(TPL, chm, WORK / f"h_{name}_VM.avs")
    fresh(BASE); apply_avs(avsM); gotM = readout(f"h_{name}_VM"); VM = mesh_vertices(f"m_h_{name}_VM")
    out["VM_current_model"] = {"slot": truth_metrics(gotM, S), "mesh_vs_truth": vdist(VM, Vt)}
    print(name, "VM", json.dumps(out["VM_current_model"]), flush=True)
    res[name] = out; save("male_e3", res)
print("DONE")
