from exp_lib import *
FS = ASSETS / "Female" / "Size"
MIA = ASSETS / "Female" / "FV2.1_Mia.avt"
TPL = FEM_RES / "mia-deafult-size.avs"
files = [p for p in sorted(glob.glob(str(FS / "**" / "*.avs"), recursive=True)) if "Maternity" not in p and tmpl_id(p).endswith("_08")]
print("eligible _08 non-maternity files:", len(files))
feats = {p: feats_avs(p) for p in files}
test = files[::max(1, len(files)//6)][:6]
print("test sizes:", [os.path.basename(p) for p in test], flush=True)
res = {}
for p in test:
    S = feats[p]
    six = [S[i] for i in DRIVEN]
    train = [feats[q] for q in files if q != p]
    others = [i for i in range(57) if i not in DRIVEN and i != 1]
    pr_all = predict_slots(train, six, others)
    pr_u = predict_slots(train, six, U_SLOTS)
    variants = {
        "T_truth_full": None,
        "V6_six_only": {i: S[i] for i in DRIVEN},
        "VH_six_plus_ridge_on_6_slots": {**{i: S[i] for i in DRIVEN}, **{s: float(v) for s, v in zip(U_SLOTS, pr_u)}},
        "VR_six_plus_ridge_on_all51": {**{i: S[i] for i in DRIVEN}, **{s: float(v) for s, v in zip(others, pr_all)}},
    }
    name = os.path.basename(p)[:-4]
    out = {}
    Vt = None
    for vn, ch in variants.items():
        avs = p if ch is None else patch_avs(TPL, ch, WORK / f"g_{name}_{vn}.avs")
        fresh(MIA); apply_avs(avs)
        got = readout(f"g_{name}_{vn}")
        V = mesh_vertices(f"m_g_{name}_{vn}")
        if ch is None:
            Vt = V
        out[vn] = {"slot": truth_metrics(got, S), "mesh_vs_truth": (vdist(V, Vt) if Vt is not None else None)}
        print(name, vn, json.dumps(out[vn]), flush=True)
    res[name] = out
    save("female_e3", res)
print("DONE")
