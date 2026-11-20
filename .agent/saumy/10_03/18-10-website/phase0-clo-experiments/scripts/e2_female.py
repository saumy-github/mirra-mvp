from exp_lib import *
MIA = ASSETS / "Female" / "FV2.1_Mia.avt"
REF = FEM_RES / "random-weight-female.avt"
TPL = FEM_RES / "mia-deafult-size.avs"
base = feats_avs(TPL)
ref = feats_avt(REF)
V_mia = np.load(WORK / "V_mia.npy"); V_ref = np.load(WORK / "V_ref70.npy")
six_ref = {i: ref[i] for i in DRIVEN}
exps = {
 "A_weight70_only": {1: 70.0},
 "B_six_from_ref70": dict(six_ref),
 "C_six_from_ref70_plus_weight70": {**six_ref, 1: 70.0},
 "D_all57_from_ref70": {i: ref[i] for i in range(57)},
 "E_tall_slim": {0: 185.0, 2: 88.0, 6: 66.0, 8: 96.0, 26: 88.0, 36: 40.0},
 "F_short_heavy": {0: 158.0, 2: 120.0, 6: 108.0, 8: 130.0, 26: 74.0, 36: 42.0},
}
res = {}
for name, ch in exps.items():
    avs = WORK / f"f_{name}.avs"
    patch_avs(TPL, ch, avs)
    sent = feats_avs(avs)
    fresh(MIA)
    r = apply_avs(avs)
    got = readout("f_" + name)
    V = mesh_vertices("m_f_" + name)
    changed = [(k, round(sent[k], 2), round(got[k], 2)) for k in range(57) if abs(sent[k] - got[k]) > 0.1]
    vs_default_floats = [k for k in range(57) if abs(got[k] - base[k]) > 0.1]
    out = {
        "request_ok": r.get("success"),
        "slots_CLO_changed_after_import(sent->got)": changed,
        "n_slots_differ_from_default_after": len(vs_default_floats),
        "non_driven_slots_moved_from_default": [k for k in vs_default_floats if k not in DRIVEN and k != 1],
        "mesh_vs_default_mia": vdist(V, V_mia),
        "mesh_vs_true_ref70": vdist(V, V_ref),
        "height_m": round(float(V[:, 1].max()), 4),
        "got_driven": [round(got[i], 2) for i in [0, 1, 2, 5, 6, 8, 26, 36]],
    }
    res[name] = out
    print(name, json.dumps(out), flush=True)
save("female_e2", res)
print("DONE")
