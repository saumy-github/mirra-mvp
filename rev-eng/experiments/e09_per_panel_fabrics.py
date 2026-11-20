"""E09 - per-panel fabrics: one fabric per T-shirt panel (findings/41 candidate A, PLUGIN_COMMAND_SPEC sec 3)

HYPOTHESIS
  ExportFabric(tmp.zfab, 0) + AddFabric(tmp.zfab) x3 + AssignFabricToPattern(i, pat_i, 1) gives each of the 4
  panels (front, back, sleeve_left, sleeve_right) its OWN fabric, so the EXISTING /set-fabric-color and
  /set-fabric-texture (which resolve GetFabricIndexForPattern(pattern)) colour/texture one panel at a time,
  and ExportGLB then emits one distinct glTF material per panel mesh.

STATUS: BLOCKED (fails fast with exit code 3, also in dry run). The plugin has NO route for
  GetFabricCount, ExportFabric, AddFabric, GetPatternPieceFabricIndex, AssignFabricToPattern.
  Proposed routes (findings/41 sec 8; PLUGIN_COMMAND_SPEC sec 3.1 for the add/assign semantics):
    GET  /fabric/count                      -> GetFabricCount(true)                    (sync read)
    POST /fabric/export {path, fabric}      -> ExportFabric(path, fabric); "" = error  (queued)
    POST /fabric/add {path}                 -> AddFabric(path); reply carries count before/after (queued)
    GET  /patterns/<i>/fabric               -> GetPatternPieceFabricIndex(i)           (sync read; 0 is ambiguous)
    POST /fabric/assign {fabric, pattern, option=1} -> AssignFabricToPattern(...) bool (queued)
  Existing and reused: /set-fabric-color, /set-fabric-texture, /export, /import-pattern, /import-avatar-avt,
  /fabric-status. The reference implementation below runs only after the TODO in main() is removed.

PRECONDITIONS: --avt and --dxf (T-shirt block with 4 pieces, pattern idx order front, back, sleeve_left,
  sleeve_right unless --order given), optional --texture PNG. One CLO, watchdog (e07) running, GUI thread.

STEPS
  1. new-project, clear, import avatar, import DXF; n0 = fabric_count (expect 1). pattern_count must be >= 4.
  2. ExportFabric(out/e09/panel_base.zfab, 0); path non-empty AND file exists on disk.
  3. k=1..3: AddFabric(path); CHECK GetFabricCount == n0+k (do NOT trust AddFabric's return, it is count-1
     even when the add failed). Abort on mismatch.
  4. For panel i: AssignFabricToPattern(i, idx[panel], 1) -> bool; fallback /set-fabric {fabric_index:i} if false.
  5. Read back GetPatternPieceFabricIndex(idx[panel]) == i (trust only i >= 1; 0 is also the failure value).
  6. Per panel: /set-fabric-color distinct colours; the success message "dispatched to fabric N" must give N == i.
     Optional /set-fabric-texture per panel (white colour first, findings/21).
  7. wait /fabric-status all_done; export out/e09/four_fabrics.glb (+ baseline out/e09/one_fabric.glb exported
     BEFORE step 2 for comparison); check with scripts/glb_probe.py (imported by path): materials count, which
     material each garment mesh references, baseColorFactor per material, image count.

EXPECTED OUTCOME
  * counts grow by 1 each, read-back 1,2,3, 4 distinct materials with the 4 set colours, each garment mesh
    ("1","2","3","7" style names) referencing a different material -> hypothesis CONFIRMED; Step 8 can use it.
  * AddFabric return fine but count unchanged -> file unreadable/invalid zfab (exported default fabric without
    texture may not be loadable) -> fall back to CreateZfabFromTextures route (findings/41 sec 3.1 #2).
  * count grows but all 3 new fabrics have the same name/uid and GLB still shows 1 material -> exporter merges
    equal fabrics (dedupe by content); retry with SetFabricName(i, panel) and distinct colours before export.
  * Assign false for fabric 1..3, read-back 0, messages say fabric 0 -> option range/colorway issue; use the
    /set-fabric fallback (SetPatternPieceFabricIndex, silent no-op when index >= count).
  * Colours land on ALL panels (GLB shows 1 material with the last colour) -> panels still share fabric 0
    (assign did not take effect) = old clobbering behaviour.
  * Modal box / queue timeout on AddFabric -> bad zfab; dismiss by hand, record the text.
RECORD: n0, counts after each add, assign bools, read-backs, dispatched-to-fabric messages, GLB material table,
  mesh->material map, file sizes; later optional offline check: save zprj, zprj_probe.py shows listFabric = 4
  and iFabricIndex = 0..3.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e09")
PANELS = ["front", "back", "sleeve_left", "sleeve_right"]
COLOURS = [(220, 30, 30), (30, 160, 60), (30, 60, 220), (240, 200, 20)]


def posix(p):
    return os.path.abspath(p).replace("\\", "/")


def fabric_count(rec, label):
    r = C.get("/fabric/count", timeout=30)  # PROPOSED route, does not exist today
    rec.step(f"fabric-count[{label}]", response=r)
    return int(r.get("count", -1))


def mesh_material_map(path):
    gp = C.glb_probe()
    g = gp.load(path)
    j = g["json"]
    rows = []
    for m in j.get("meshes", []):
        rows.append({"mesh": m.get("name"), "materials": sorted({p.get("material") for p in m["primitives"]
                                                                if p.get("material") is not None})})
    return rows


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt", required=True)
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--texture")
    ap.add_argument("--order", default=",".join(map(str, range(4))),
                    help="pattern indices for front,back,sleeve_left,sleeve_right (default 0,1,2,3)")
    args = ap.parse_args()
    # Fail fast, always (also in dry-run) so nobody mistakes a dry run for a runnable test.
    C.todo_missing_command(
        "FabricAPI::GetFabricCount / ExportFabric / AddFabric / AssignFabricToPattern and "
        "PatternAPI::GetPatternPieceFabricIndex",
        "GET /fabric/count, POST /fabric/export {path,fabric}, POST /fabric/add {path}, "
        "POST /fabric/assign {fabric,pattern,option}, GET /patterns/<i>/fabric (findings/41 sec 8)",
        "Hypothesis A (one fabric per panel) cannot be tested without them.")
    # ---- reference implementation, reachable only after the TODO above is removed ----
    idx = [int(x) for x in args.order.split(",")]
    C.plan_only(args, ["new-project, clear, import avatar+DXF, export baseline one_fabric.glb",
                       "fabric_export(zfab,0); fabric_add x3 with count==n0+k check",
                       "assign_fabric per panel + read-back", "per-panel colour/texture", "export + glb_probe"])
    rec = C.Recorder("e09_per_panel_fabrics", args)
    C.preflight(rec)
    C.run_cmd(rec, "new-project", "/new-project", {}, args.queue_timeout)
    C.run_cmd(rec, "clear", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
    C.run_cmd(rec, "avatar", "/import-avatar-avt", {"path": posix(args.avt)}, args.queue_timeout)
    C.run_cmd(rec, "dxf", "/import-pattern", {"path": posix(args.dxf), "scale": 1.0}, args.queue_timeout)
    if C.pattern_count(rec, "loaded") < 4:
        rec.finish("ABORT_NEED_4_PATTERNS")
        raise SystemExit("need >= 4 patterns")
    C.post("/fabric-status/reset")
    base = C.export_scene(rec, "baseline", os.path.join(OUT, "one_fabric.glb"))
    n0 = fabric_count(rec, "n0")
    zfab = posix(os.path.join(OUT, "panel_base.zfab"))
    os.makedirs(OUT, exist_ok=True)
    C.run_cmd(rec, "fabric-export", "/fabric/export", {"path": zfab, "fabric": 0}, args.queue_timeout)
    if not os.path.exists(zfab):
        rec.finish("ABORT_ZFAB_NOT_WRITTEN")
        raise SystemExit("ExportFabric wrote no file")
    for k in (1, 2, 3):
        C.run_cmd(rec, f"fabric-add[{k}]", "/fabric/add", {"path": zfab}, args.queue_timeout)
        n = fabric_count(rec, f"after-add-{k}")
        if n != n0 + k:
            rec.finish(f"ABORT_COUNT_{n}_EXPECTED_{n0 + k}")
            raise SystemExit(f"GetFabricCount {n} != {n0 + k}: AddFabric did not add (return value is unreliable)")
    mapping = []
    for i, panel in enumerate(PANELS):
        a = C.run_cmd(rec, f"assign[{panel}]", "/fabric/assign",
                      {"fabric": i, "pattern": idx[i], "option": 1}, args.queue_timeout)
        if not a["ok"] and i:
            rec.note(f"assign false for {panel}; fallback /set-fabric (silent no-op if index >= count)")
            C.run_cmd(rec, f"set-fabric[{panel}]", "/set-fabric",
                      {"pattern_index": idx[i], "fabric_index": i}, args.queue_timeout)
        rb = C.get(f"/patterns/{idx[i]}/fabric", timeout=30)  # PROPOSED route
        rec.step(f"readback[{panel}]", response=rb, expected=i,
                 trustworthy=i >= 1)
        mapping.append({"panel": panel, "expected": i, "readback": rb.get("fabric_index")})
    for i, panel in enumerate(PANELS):
        r, g, b = COLOURS[i]
        C.run_cmd(rec, f"colour[{panel}]", "/set-fabric-color",
                  {"pattern_index": idx[i], "r": r, "g": g, "b": b}, args.queue_timeout)
        if args.texture and i == 0:
            C.run_cmd(rec, "texture[front]", "/set-fabric-texture",
                      {"pattern_index": idx[0], "texture_path": posix(args.texture)}, args.queue_timeout)
    C.wait_fabric_done(rec)
    ex = C.export_scene(rec, "four_fabrics", os.path.join(OUT, "four_fabrics.glb"))
    if ex.get("bytes"):
        rows = C.glb_summary([base["path"], ex["path"]])
        rec.step("glb_summary", rows=rows)
        rec.data["mesh_material_map"] = mesh_material_map(ex["path"])
        rec.data["materials_baseline_vs_four"] = [r.get("materials") for r in rows]
    rec.data["mapping"] = mapping
    rec.finish("confirmed iff counts n0+1..3, readback 1,2,3 and 4 distinct materials (see mesh_material_map)")


if __name__ == "__main__":
    C.guarded(main)
