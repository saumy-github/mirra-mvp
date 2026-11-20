"""E10 - fabric physical presets: does ChangeFabricWithJson(0, preset.jfab) change drape? (findings/38 sec 6,
PLUGIN_COMMAND_SPEC sec 3.1 mode "change")

HYPOTHESIS
  Loading a minimal .jfab (mapPhysical + qsFabricName + versions=100) over fabric 0 with ChangeFabricWithJson
  replaces the physics. With identical avatar, DXF, colour and Simulate step count, a STIFF preset (bending x10,
  buckling on) gives a less drooped garment than CLO "Default" (Bu=100, Bv=600, Bh=150), and a SOFT preset
  (bending x0.25) a more drooped/wider one. Measured by simulated garment extents (glb_probe pos_bounds of the
  exported GLB) and by the GLB bin sha256 (different -> geometry differs).

STATUS: BLOCKED (fails fast, exit code 3, also in dry run) for the live part. Missing plugin route (none exists):
    POST /fabric/physical {jfab_path, mode:"change", fabric_index:0, pattern_indices:[], assign_option:1,
                           reapply_color, reapply_texture, simulate_after:0}      (PLUGIN_COMMAND_SPEC sec 3.1)
    wrapping GetFabricCount, GetFabricName, ChangeFabricWithJson(0, path) (bool), reading the name back.
  Also missing and wanted: GET /fabric/count. There is no physics getter in the SDK (findings/38 sec 1): the
  only proof of applied physics is save project (ExportZPrj) + scripts/zprj_probe.py tree --path
  listFabric/0/mapPhysical (offline; step 8 below). The OFFLINE preparation (--prepare) works today and writes
  the presets; run it first, it contacts nothing.

PRESETS (built into experiments/out/e10/): keys copied from the CLO "Default" mapPhysical stored in a Mirra zprj
  (findings/38 sec 2b / sec 4): fSuK=fSvK=100000, fHK=5000, fBuK=100, fBvK=600, fBhK=150, buckling 0,
  fDensity=0.0003, fThickness=0.5, fFriction=0.03, fIDS=0.0001, enFabricType=0. Optionally --zprj + --pac-member
  reads the real block via zprj_probe.py (imported by path) and merges unknown extra keys (_v2, LeftShear...).
  stiff: fBuK/fBvK/fBhK x10, fBuLR/fBvLR/fBhLR=0.8, fBucklingStiffnessU/V/H=0.8, fSuK/fSvK x1.5, enFabricType=4.
  soft : fBuK/fBvK/fBhK x0.25, fSuK/fSvK x0.5, fIDS unchanged, enFabricType=0.
  Caveat [I, findings/38 sec 2b]: a spec-only jfab leaves *_v2 / LeftShear keys to the loader; they may stay at
  the default values (then bending effect is partial) - the zprj diff in step 8 shows which.

STEPS (live, once unblocked)
  1. new-project, clear, import avatar, import DXF, set colour (identical for all runs).
  2. For variant in default, stiff, soft: (re)start from step 1 (/new-project) so runs are independent.
     default: no jfab load. stiff/soft: POST /fabric/physical (mode change, fabric 0) -> api_returned true,
     verified_name true; re-apply colour (ChangeFabricWithJson wipes appearance).
  3. /simulate --sim-steps (same N for all), wait idle.
  4. export out/e10/<variant>.glb; glb_summary + pos_bounds (extents x,y,z, bin_sha).
  5. optional /export zprj (if a route exists; else save by hand) -> zprj_probe.py tree ... --path
     listFabric/0/mapPhysical to confirm fBuK etc. changed.
  6. Compare extents default vs stiff vs soft; repeat default twice to measure determinism noise (e03 says
     Simulate must be deterministic for the bin hash comparison to mean anything).

EXPECTED OUTCOME
  * bin sha differs across the 3 variants AND stiff vertical extent (hem hangs) differs monotonically from soft,
    zprj shows changed mapPhysical -> hypothesis CONFIRMED; Step 8 can ship drape presets.
  * api_returned true, zprj physics changed, but GLB identical -> simulate too short / cloth not re-initialised
    (loader at 0x4998730 not read to the end); try more steps or a reset (re-assign / re-import DXF) after load.
  * api_returned false -> bad fabric index or unreadable/invalid jfab; check JSON validity and listTexture paths.
  * zprj physics unchanged but name changed -> loader applied appearance only (physical keys rejected).
  * modal dialog / queue timeout -> malformed jfab (parse error box) or missing texture path; dismiss, record.
  * default run twice differs -> non-deterministic Simulate; the comparison is void (see e03).
RECORD: preset files + sha, api_returned, name before/after, step count, per-variant bin sha, extents, zprj
  mapPhysical diff, determinism check.
"""
import copy
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e10")

# findings/38 sec 2b, "CLO Default in a Mirra zprj" column [V]
DEFAULT_PHYS = {
    "fSuK": 100000, "fSvK": 100000, "fHK": 5000,
    "fBuK": 100, "fBvK": 600, "fBhK": 150,
    "fBuLR": 0, "fBvLR": 0, "fBhLR": 0,
    "fBucklingStiffnessU": 0, "fBucklingStiffnessV": 0, "fBucklingStiffnessH": 0,
    "fDensity": 0.0003, "fThickness": 0.5, "fFriction": 0.03, "fIDS": 0.0001,
    "enFabricType": 0, "qsPhysicalPropertyName": "Default",
}


def posix(p):
    return os.path.abspath(p).replace("\\", "/")


def default_from_zprj(zprj, member):
    """Optional: pull the real listFabric/0/mapPhysical via zprj_probe.py (imported by path). Best effort."""
    zp = C.load_module_by_path("zprj_probe", os.path.join(C.REV_ENG, "scripts", "zprj_probe.py"))
    # zprj_probe.cmd_tree prints; reuse its reader helpers when they fit, else fall back to the constants.
    try:
        b = open(zprj, "rb").read()
        pac = zp.read_member(zprj, member)
        fields = zp.g.parse(pac) if hasattr(zp, "g") else None
        node = zp.nav(fields, "listFabric/0/mapPhysical")
        out = {}
        zp.flatten(node, "", out)
        return {k.split("/")[-1]: v for k, v in out.items()}, len(b)
    except Exception as e:  # noqa: BLE001
        print(f"NOTE: zprj_probe read failed ({type(e).__name__}: {e}); using findings/38 constants")
        return None, 0


def build_presets(base_phys):
    stiff, soft = copy.deepcopy(base_phys), copy.deepcopy(base_phys)
    for k in ("fBuK", "fBvK", "fBhK"):
        stiff[k] = base_phys[k] * 10
        soft[k] = base_phys[k] * 0.25
    for k in ("fBuLR", "fBvLR", "fBhLR", "fBucklingStiffnessU", "fBucklingStiffnessV", "fBucklingStiffnessH"):
        stiff[k] = 0.8
    stiff["fSuK"], stiff["fSvK"] = base_phys["fSuK"] * 1.5, base_phys["fSvK"] * 1.5
    soft["fSuK"], soft["fSvK"] = base_phys["fSuK"] * 0.5, base_phys["fSvK"] * 0.5
    stiff["enFabricType"] = 4
    stiff["qsPhysicalPropertyName"], soft["qsPhysicalPropertyName"] = "MirraStiff", "MirraSoft"
    return {"stiff": stiff, "soft": soft}


def write_presets(base_phys):
    os.makedirs(OUT, exist_ok=True)
    paths = {}
    for name, phys in build_presets(base_phys).items():
        # minimal jfab (findings/38 sec 4): mapPhysical + qsFabricName + versions 100; NO texture paths
        doc = {"uiFabricVersion": 100, "uiVersion": 100, "qsFabricName": f"Mirra_{name}", "mapPhysical": phys}
        p = os.path.join(OUT, f"{name}.jfab")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
        paths[name] = p
        print(f"wrote {p} sha256_16={hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]}")
    return paths


def extents(path):
    gp = C.glb_probe()
    lo, hi = gp.pos_bounds(gp.load(path))
    return {"lo": lo, "hi": hi, "size": [round(h - l, 5) for l, h in zip(lo, hi)]}


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt")
    ap.add_argument("--dxf")
    ap.add_argument("--sim-steps", type=int, default=100)
    ap.add_argument("--sim-timeout", type=float, default=900.0)
    ap.add_argument("--prepare", action="store_true", help="OFFLINE: write stiff/soft .jfab into out/e10/ and exit 0")
    ap.add_argument("--zprj", help="optional: zprj to copy the real Default mapPhysical from")
    ap.add_argument("--pac-member", default="simulation.zpac!simulation.pac")
    args = ap.parse_args()
    base = dict(DEFAULT_PHYS)
    if args.zprj:
        real, _ = default_from_zprj(args.zprj, args.pac_member)
        if real:
            base.update({k: v for k, v in real.items() if isinstance(v, (int, float, str))})
    if args.prepare:
        write_presets(base)
        raise SystemExit(0)
    # Fail fast, always (also in dry-run) so nobody mistakes a dry run for a runnable test.
    C.todo_missing_command(
        "FabricAPI::ChangeFabricWithJson(fabricIdx, path) [+ GetFabricCount/GetFabricName for the checks]",
        "POST /fabric/physical {jfab_path, mode:'change', fabric_index:0, ...} (PLUGIN_COMMAND_SPEC sec 3.1), "
        "GET /fabric/count",
        "Run with --prepare first to create the presets offline.")
    # ---- reference implementation, reachable only after the TODO above is removed ----
    if not (args.avt and args.dxf):
        raise SystemExit("--avt and --dxf are required")
    presets = write_presets(base)
    rec = C.Recorder("e10_fabric_physical_preset", args)
    C.preflight(rec)
    rows = {}
    for variant in ("default", "default_repeat", "stiff", "soft"):
        C.run_cmd(rec, f"{variant}.new-project", "/new-project", {}, args.queue_timeout)
        C.run_cmd(rec, f"{variant}.clear", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
        C.run_cmd(rec, f"{variant}.avatar", "/import-avatar-avt", {"path": posix(args.avt)}, args.queue_timeout)
        C.run_cmd(rec, f"{variant}.dxf", "/import-pattern", {"path": posix(args.dxf), "scale": 1.0}, args.queue_timeout)
        C.post("/fabric-status/reset")
        if variant in presets:
            r = C.run_cmd(rec, f"{variant}.physical", "/fabric/physical",
                          {"jfab_path": posix(presets[variant]), "mode": "change", "fabric_index": 0,
                           "pattern_indices": [], "assign_option": 1}, args.queue_timeout)
            if not r["ok"]:
                rec.note(f"{variant}: ChangeFabricWithJson not ok -> physics NOT applied; skipping")
                continue
        C.run_cmd(rec, f"{variant}.colour", "/set-fabric-color",
                  {"pattern_index": 0, "r": 200, "g": 200, "b": 200}, args.queue_timeout)
        C.wait_fabric_done(rec)
        C.run_cmd(rec, f"{variant}.simulate", "/simulate", {"steps": args.sim_steps}, args.sim_timeout)
        ex = C.export_scene(rec, f"{variant}.export", os.path.join(OUT, variant + ".glb"))
        if ex.get("bytes"):
            gsum = C.glb_summary([ex["path"]])[0]
            rows[variant] = {"bin_sha": gsum.get("bin_sha"), "bin_len": gsum.get("bin_len"),
                             "extents": extents(ex["path"])}
            rec.step(f"{variant}.measure", **rows[variant])
    rec.data["table"] = rows
    if "default" in rows and "default_repeat" in rows:
        rec.note(f"determinism: default vs repeat bin_sha equal = {rows['default']['bin_sha'] == rows['default_repeat']['bin_sha']}")
    rec.note("Physics proof: save project and run zprj_probe.py tree <zprj> <member> --path listFabric/0/mapPhysical")
    rec.finish("compare extents/bin_sha: default vs stiff vs soft")


if __name__ == "__main__":
    C.guarded(main)
