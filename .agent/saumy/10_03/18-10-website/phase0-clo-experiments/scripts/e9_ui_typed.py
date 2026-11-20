"""Use CLO's own Avatar Editor (keys and clicks) to set the avatar, and compare with the shipped size (truth):
  UT6 = type the six values with the default Width driver (Under Bust)
  UTW = switch the Width driver to Weight, type a weight, then type the six values (CLO's weight model fills the rest)
Times every run."""
import subprocess, sys
from exp_lib import *

SC = Path(__file__).parent
PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SC / "ui.ps1")]
A = ASSETS
group = sys.argv[2] if len(sys.argv) > 2 else "female"
GCFG = {
    "female": dict(base=A / "Female" / "FV2.1_Mia.avt", tpl=FEM_RES / "mia-deafult-size.avs", downs=2,
                   files=lambda: [p for p in sorted(glob.glob(str(A / "Female" / "Size" / "**" / "*.avs"), recursive=True)) if "Maternity" not in p and "Teenager" not in p and tmpl_id(p).endswith("_08")]),
    "teen_f": dict(base=A / "Female" / "FV2.1_Luna_Teenager.avt", tpl=A / "Female" / "Size" / "CLO_Teenager_Default.avs", downs=2,
                   files=lambda: [p for p in sorted(glob.glob(str(A / "Female" / "Size" / "**" / "*.avs"), recursive=True)) if "Teenager" in p]),
    "girl": dict(base=A / "Kid" / "KV1.1G_Melody_(7-20).avt", tpl=A / "Kid" / "Size" / "Girl" / "CLO_Girl_Default.avs", downs=2,
                 files=lambda: sorted(glob.glob(str(A / "Kid" / "Size" / "Girl" / "*.avs")))),
    "boy": dict(base=A / "Kid" / "KV1.1B_Oliver_(7-20).avt", tpl=A / "Kid" / "Size" / "Boy" / "CLO_Boy_Default.avs", downs=1,
                files=lambda: sorted(glob.glob(str(A / "Kid" / "Size" / "Boy" / "*.avs")))),
}[group]
MIA = GCFG["base"]
IDS = {0: "spinBoxHeightMeasureID000", 2: "spinBoxChestCircumMeasureID002", 6: "spinBoxWaistCircumMeasureID006",
       8: "spinBoxLowHipCircumMeasureID008", 26: "spinBoxInseamMeasureID026", 36: "spinBoxAcrossShoulderMeasureID036"}
SPEED["f"] = 0.4
pick = sys.argv[1].split(",")
files = GCFG["files"]()
wt = json.loads((SCR / "results" / "weighttable_female.json").read_text()) if group == "female" else {}
res_name = f"ui_typed_{group}"
res = json.loads((SCR / "results" / f"{res_name}.json").read_text()) if (SCR / "results" / f"{res_name}.json").exists() else {}


def ui(action, value=""):
    a = PS + ["-Action", action] + (["-Value", value] if value != "" else [])
    return subprocess.run(a, capture_output=True, text=True, timeout=120).stdout


def typed(S, w=None):
    fresh(MIA); time.sleep(0.8)
    if w is not None:
        out = ui("driver_weight", str(GCFG["downs"]))
        if "spinBoxWidthCircum" not in out:
            raise RuntimeError("weight driver not selected: " + out)
        pairs = [f"spinBoxWidthCircumMeasureID002={w:g}"]
    else:
        pairs = []
    pairs += [f"{IDS[i]}={S[i]:.2f}" for i in (0, 2, 6, 8, 26, 36)]
    ui("setmany", ";".join(pairs))


for p in [q for q in files if any(s in os.path.basename(q) for s in pick)]:
    name = os.path.basename(p)[:-4]
    if name in res:
        continue
    S = feats_avs(p)
    w_hat = wt.get(name, {}).get("weight_that_best_fits_kg", feats_avs(GCFG["tpl"])[1])
    got_t, Vt = run_variant(MIA, p, f"ui_{name}_T")
    out = {}
    for label, w in (("UT6_typed_six", None), ("UTW_weight_then_six", w_hat)):
        t0 = time.time()
        typed(S, w)
        got = readout(f"ui_{name}_{label}")
        V = mesh_vertices(f"m_ui_{name}_{label}")
        out[label] = {"seconds": round(time.time() - t0, 1), "weight_kg": w, "slot": truth_metrics(got, S), "mesh_vs_truth": vdist(V, Vt),
                      "driven_requested_vs_got": {i: (round(S[i], 1), round(got[i], 1)) for i in DRIVEN}}
        print(name, label, json.dumps({k: out[label][k] for k in ("seconds", "mesh_vs_truth")}), out[label]["driven_requested_vs_got"], flush=True)
    res[name] = out; save(res_name, res)
print("DONE", flush=True)
