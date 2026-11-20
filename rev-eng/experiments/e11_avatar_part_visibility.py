"""E11 - avatar part visibility: does a patched .dan bVisible=0 make ExportGLB skip Hair / shoes? (findings/42,
findings/46)

HYPOTHESIS
  scripts/avt_patch_tool.py can set mapElement/bVisible=0 (1 byte, same length) on the Hair transformer+shape
  (2 leaves) and on shoes_r / shoes_l. After /import-avatar-avt of the patched copy, /export (avatar only, the
  plugin's default bIncludeHiddenObject=false) skips the hidden objects (finding 42 sec 2: the exporter gate at
  0x145CB2659 calls obj->vtbl+0x70 "is visible"). Expected effect vs baseline (base-1.avt GLB: 9 meshes,
  bin 13,409,456 B, 200,134 verts, packed 30.5 MB): no-hair -> 8 meshes (no "Hair"), bin about 4.6 MB;
  no-shoes -> no shoes_r_Shape/shoes_l_Shape meshes; both -> 5-6 meshes.

STATUS: runnable with EXISTING routes (/import-avatar-avt, /export, /clear-avatars, /new-project) EXCEPT the
  persistence question, which is BLOCKED:
    "does ImportAvatar KEEP the patched flag?" can only be answered by re-exporting an AVT after import. There is
    no route for it (no ExportAvatar / avatar-save call exposed). Proposed: POST /export-avatar-avt {path,
    avatar_index} wrapping the SDK export-avatar call if one exists in ExportAPIInterface.h (unverified), else
    ExportZPrj + inspect the saved project's mapTransformer3D bVisible with scripts/zprj_probe.py. The script
    records this step as "BLOCKED" (exit code stays 0; not a fail-fast because the GLB comparison is
    independently useful). Indirect evidence is the GLB mesh list itself: a hidden mesh missing from the GLB
    means the flag was honoured on load (or at least at export).
  Exit code 3 is returned only with --need-avt-reexport (asserts that route exists).

PRECONDITIONS: --avt input/base-1.avt (read only). Patched COPIES are written to experiments/out/e11/ by
  --prepare (offline, no plugin). The original is never modified. One CLO, watchdog (e07) running.

STEPS
  --prepare (offline): avt_patch_tool.patch(src, out/e11/nohair.avt, hide Hair), noshoes.avt (shoes_r, shoes_l),
     nohair_noshoes.avt; verify each by re-reading bVisible through the tool's own `meshes` logic.
  --live:
  1. for variant in baseline(original --avt), nohair, noshoes, nohair_noshoes:
       /new-project, /clear-avatars, /import-avatar-avt {path}; /avatars/state (avatar_count 1, record);
       /export -> out/e11/<variant>.glb (avatar only: no patterns loaded).
  2. glb_probe (imported by path): mesh name list, skins, materials, images, verts, bin_len, file bytes; compare
     vs baseline (deltas, which names vanished).
  3. AVT re-export for the persistence check: BLOCKED (no route), recorded.

EXPECTED OUTCOME
  * Hair/shoes mesh names absent, bin_len drops by about 8.8 MB (hair) / 0.9 MB (shoes), verts 200,134 -> about
    58.7k / 46.9k -> hypothesis CONFIRMED, flag honoured on import and at export; wire into step_06 patch route.
  * Meshes unchanged (all 9 present, identical bin sha) -> CLO ignores bVisible on .avt import (cf. findings/19:
    some patched floats are not applied) or the gate is per whole avatar; fall back to deleting the Hair subtree
    in the .dan or to offline removal of the mesh/skin/node/material/images from the GLB.
  * Mesh vanishes but its skin/node remains, or the whole avatar vanishes (0 meshes) -> gate is per whole avatar
    or coarser than assumed; record, do not ship.
  * Import fails / modal box / CLO crash on the patched file -> digest or 0x24 rejected (findings/31 sec 5 open
    item); the tool keeps both self-consistent, so a failure means other validation exists. Dismiss, record.
  * Only Hair OR only shoes honoured -> per-part gating differs (accessory enAccessoryPart 1 vs 2/3).
RECORD: patched-file sha256 and edit offsets, avatars/state, per-variant mesh names, bin_len, verts, file bytes,
  deltas vs baseline, sha of bin, queue/timeout outcomes, the BLOCKED re-export note.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e11")
VARIANTS = {
    "nohair": ["Hair"],
    "noshoes": ["shoes_r", "shoes_l"],
    "nohair_noshoes": ["Hair", "shoes_r", "shoes_l"],
}


def posix(p):
    return os.path.abspath(p).replace("\\", "/")


def patch_tool():
    """avt_patch_tool.py imported by path; its sibling avs_grammar must be importable, so add scripts/ first."""
    scripts = os.path.join(C.REV_ENG, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return C.load_module_by_path("avt_patch_tool", os.path.join(scripts, "avt_patch_tool.py"))


def read_visible(at, avt_path):
    """name -> list of bVisible bytes for every /mapTransformer3D node (same logic as the tool's `meshes`)."""
    raw = open(avt_path, "rb").read()
    zo, _ = at.split(raw)
    infos, datas = at.read_zip(raw, zo)
    dan = datas[at.dan_index(infos)]
    lm = at.g.leaf_map(dan)
    out = {}
    for p, (o, s, t) in lm.items():
        if p.endswith("/mapElement/qsName") and "/mapTransformer3D" in p:
            bp = p[:-6] + "bVisible"
            if bp in lm:
                name = dan[o:o + s].decode("latin1")
                out.setdefault(name, []).append(dan[lm[bp][0]])
    return out


def prepare(src):
    at = patch_tool()
    os.makedirs(OUT, exist_ok=True)
    made = {}
    before = read_visible(at, src)
    print("source bVisible bytes:", {k: before.get(k) for k in ("Hair", "shoes_r", "shoes_l")})
    for name, hide in VARIANTS.items():
        dst = os.path.join(OUT, name + ".avt")
        at.patch(src, dst, [], list(hide), [], True)  # tool self-verifies and refuses on any anomaly
        vis = read_visible(at, dst)
        ok = all(all(b == 0 for b in vis.get(h, [1])) for h in hide)
        sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16]
        print(f"{name}: wrote {dst} sha256_16={sha} hidden_ok={ok} bVisible={ {h: vis.get(h) for h in hide} }")
        made[name] = dst
    return made


def mesh_names(path):
    gp = C.glb_probe()
    j = gp.load(path)["json"]
    return [m.get("name") for m in j.get("meshes", [])]


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt", required=True, help="stock input/base-1.avt (read only)")
    ap.add_argument("--prepare", action="store_true", help="OFFLINE: write patched copies into out/e11/ and exit 0")
    ap.add_argument("--need-avt-reexport", action="store_true",
                    help="assert the AVT re-export route exists; exits 3 today")
    args = ap.parse_args()
    if args.need_avt_reexport:
        C.todo_missing_command(
            "AVT re-export of the loaded avatar (to see if ImportAvatar kept bVisible)",
            "POST /export-avatar-avt {path, avatar_index} (SDK call unverified) or save zprj + zprj_probe.py",
            "Without it persistence is only inferable from the exported GLB mesh list.")
    if args.prepare:
        prepare(args.avt)
        raise SystemExit(0)
    C.plan_only(args, ["--prepare first (offline): patched copies nohair/noshoes/nohair_noshoes in out/e11/",
                       "for baseline + 3 variants: new-project, clear-avatars, import-avatar-avt, export glb",
                       "glb_probe: mesh names, bin_len, verts, bytes; deltas vs baseline",
                       "AVT re-export of the imported avatar: BLOCKED (no route), recorded"])
    rec = C.Recorder("e11_avatar_part_visibility", args)
    C.preflight(rec)
    files = {"baseline": args.avt}
    for name in VARIANTS:
        p = os.path.join(OUT, name + ".avt")
        if not os.path.exists(p):
            rec.finish("ABORT_NOT_PREPARED")
            raise SystemExit(f"{p} missing: run with --prepare first")
        files[name] = p
    table = {}
    for name, avt in files.items():
        C.run_cmd(rec, f"{name}.new-project", "/new-project", {}, args.queue_timeout)
        C.run_cmd(rec, f"{name}.clear", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
        imp = C.run_cmd(rec, f"{name}.import", "/import-avatar-avt", {"path": posix(avt)}, args.queue_timeout)
        C.avatar_state(rec, name)
        if not imp["ok"]:
            rec.note(f"{name}: import not ok")
            continue
        ex = C.export_scene(rec, f"{name}.export", os.path.join(OUT, name + ".glb"))
        if ex.get("bytes"):
            s = C.glb_summary([ex["path"]])[0]
            table[name] = {"meshes": mesh_names(ex["path"]), "bin_len": s.get("bin_len"), "verts": s.get("verts"),
                           "bytes": ex["bytes"], "bin_sha": s.get("bin_sha"),
                           "materials": s.get("materials"), "images": s.get("images")}
            rec.step(f"{name}.measure", **table[name])
    base = table.get("baseline")
    if base:
        for name, row in table.items():
            if name != "baseline":
                row["vanished_meshes"] = [m for m in base["meshes"] if m not in row["meshes"]]
                row["bin_delta"] = row["bin_len"] - base["bin_len"]
                row["verts_delta"] = row["verts"] - base["verts"]
                rec.step(f"{name}.delta", vanished=row["vanished_meshes"], bin_delta=row["bin_delta"],
                         verts_delta=row["verts_delta"])
    rec.data["table"] = table
    rec.note("ImportAvatar keeps patched bVisible? AVT re-export BLOCKED (no route); inferred only from missing "
             "meshes in the GLB above. Proposed: POST /export-avatar-avt or zprj save + zprj_probe.")
    rec.finish("hypothesis confirmed iff Hair/shoes mesh names vanish and bin_len drops")


if __name__ == "__main__":
    C.guarded(main)
