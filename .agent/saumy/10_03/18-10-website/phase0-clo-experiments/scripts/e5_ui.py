"""Probe 3: can CLO's own Avatar Editor fill the slots that the .avs import leaves alone?
Types values into the editor (UI Automation) and reads the avatar back through the plugin."""
import subprocess, sys
from exp_lib import *

PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).with_name("ui.ps1"))]
MIA = ASSETS / "Female" / "FV2.1_Mia.avt"
FS = ASSETS / "Female" / "Size"
IDS = {0: "spinBoxHeightMeasureID000", 2: "spinBoxChestCircumMeasureID002", 6: "spinBoxWaistCircumMeasureID006",
       8: "spinBoxLowHipCircumMeasureID008", 26: "spinBoxInseamMeasureID026", 36: "spinBoxAcrossShoulderMeasureID036"}
WEIGHT_ID = "spinBoxWidthCircumMeasureID002"


def ui(action, id_="", value=""):
    a = PS + ["-Action", action]
    if id_:
        a += ["-Id", id_]
    if value != "":
        a += ["-Value", value]
    r = subprocess.run(a, capture_output=True, text=True, timeout=120)
    return r.stdout.strip()


def spinners(txt):
    d = {}
    for line in txt.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    return d


def start(base=MIA):
    fresh(base)
    time.sleep(1.0)
    print("  editor:", ui("open_editor"), flush=True)
    time.sleep(1.0)


def changed(a, b, thr=0.05):
    return {k: (round(a[k], 2), round(b[k], 2)) for k in range(57) if abs(a[k] - b[k]) > thr}


S_path = [p for p in glob.glob(str(FS / "**" / "US_ASTM_Petite_Straight_4.avs"), recursive=True)][0]
S = feats_avs(S_path)
six = {i: S[i] for i in DRIVEN}
res = {}

# U1 baseline
start()
base = readout("u1_base")
sp0 = spinners(ui("read"))
res["U1_editor_spinners_at_start"] = {k: sp0[k] for k in list(sp0)[:12]}
print("U1 spinners (first 12):", res["U1_editor_spinners_at_start"], flush=True)

# U2 type waist only
txt = ui("set", IDS[6], "80")
got = readout("u2_waist80")
res["U2_type_waist_80"] = {"slots_changed(before,after)": changed(base, got), "n_changed": len(changed(base, got))}
print("U2 waist 80 ->", len(changed(base, got)), "slots changed; U slots:", {k: v for k, v in changed(base, got).items() if k in U_SLOTS}, flush=True)

# U3 type weight 70
start()
base = readout("u3_base")
ui("set", WEIGHT_ID, "70")
got = readout("u3_weight70")
res["U3_type_weight_70"] = {"n_changed": len(changed(base, got)), "driven": {i: (round(base[i], 2), round(got[i], 2)) for i in DRIVEN + [1] + U_SLOTS}}
print("U3 weight 70 ->", res["U3_type_weight_70"]["n_changed"], "slots changed; drive/U:", res["U3_type_weight_70"]["driven"], flush=True)

# truth mesh for size S
got_t, Vt = run_variant(MIA, S_path, "u_truth")
V_truth = Vt


def typed_six(label, pre=None):
    start()
    if pre:
        for step in pre:
            print("  pre:", step, ui(*step), flush=True) if False else ui(*step)
    for i in (0, 2, 6, 8, 26, 36):
        ui("set", IDS[i], f"{S[i]:.2f}")
    got = readout(label)
    V = mesh_vertices("m_" + label)
    out = {"slot": truth_metrics(got, S), "mesh_vs_truth": vdist(V, V_truth),
           "driven_got": {i: (round(S[i], 2), round(got[i], 2)) for i in DRIVEN}}
    print(label, json.dumps(out), flush=True)
    return out


res["U4_typed_six_default_link"] = typed_six("u4_typed_six")
res["U5_typed_six_unlinked"] = typed_six("u5_typed_six_unlinked", pre=[("click", "linkWidthButton"), ("click", "linkHeightButton")])
res["U6_weight60_then_six"] = typed_six("u6_weight60_six", pre=[("set", WEIGHT_ID, "60")])
save("ui_e5", res)
print("DONE", flush=True)
