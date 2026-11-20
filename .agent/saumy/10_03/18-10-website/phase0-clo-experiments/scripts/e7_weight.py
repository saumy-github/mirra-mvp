"""CLO's own weight model: set Width driver = Weight in the Avatar Editor, type a weight, read all 57 values back."""
import subprocess, sys
from exp_lib import *

SC = Path(__file__).parent
PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
group = sys.argv[1]
weights = [float(x) for x in sys.argv[2].split(",")]
cfg = {"female": (ASSETS / "Female" / "FV2.1_Mia.avt", (929, 254)), "male": (REPO / "clo_avatar_generation" / "input" / "base-1.avt", (929, 240))}
base, item_xy = cfg[group]


def click(x, y):
    subprocess.run(PS + [str(SC / "click.ps1"), "-X", str(x), "-Y", str(y)], capture_output=True, text=True, timeout=60)


def ui(*a):
    cmd = PS + [str(SC / "ui.ps1"), "-Action", a[0]] + (["-Id", a[1]] if len(a) > 1 else []) + (["-Value", a[2]] if len(a) > 2 else [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


res = {}
for W in weights:
    fresh(base); time.sleep(1.0)
    ui("open_editor"); time.sleep(0.5)
    cid = "comboWidthType" if group == "female" else "comboChest"
    time.sleep(2.0)
    for _try in range(2):
        click(948, 204); time.sleep(0.8)
        for k in ("{UP}", "{UP}", "{UP}", "{ENTER}"):
            ui("keys", "", k); time.sleep(0.4)
        for k in ("{DOWN}",) * (2 if group == "female" else 1):
            ui("keys", "", k); time.sleep(0.8)
        wv = [l for l in ui("read").splitlines() if "spinBoxWidthCircum" in l]
        if wv and float(wv[0].split("=")[1]) < 90:
            break
        print("  driver not on Weight yet:", wv, flush=True)
    d0 = readout("w_ref")
    out = ui("set", "spinBoxWidthCircumMeasureID002", f"{W:g}")
    got = readout(f"w_{group}_{W:g}")
    ch = {k: (round(d0[k], 2), round(got[k], 2)) for k in range(57) if abs(d0[k] - got[k]) > 0.05}
    res[f"{W:g}"] = {"n_changed": len(ch), "slot1": round(got[1], 2), "driven": {i: round(got[i], 2) for i in DRIVEN}, "U": {i: round(got[i], 2) for i in U_SLOTS + [50]}, "all": [round(x, 3) for x in got]}
    print(group, W, "changed", len(ch), "slot1", round(got[1], 1), "driven", [round(got[i], 1) for i in DRIVEN], "U", [round(got[i], 1) for i in U_SLOTS], flush=True)
    save(f"weight_sweep_{group}", res)
print("DONE")
