"""E06 - fabric colour read-back (old E4, R7)

HYPOTHESES (findings/21 lane N)
  H1: SetFabricPBRMaterialBaseColor float overload takes 0..1 with no gamma conversion. The plugin route
      /set-fabric-color takes 0..255 ints and divides by 255 (RestPlugin_windows.cpp ~2067), so
      (255,0,0) should read back as baseColorFactor ~[1,0,0] with no sRGB curve; (128,128,128) -> 0.502, not 0.216.
  H2: face argument (0 Front / 1 Back / 2 Side) unchecked; Back may fall back to Front.
  H3: colour set while a texture is present does not clear the texture (texture needs reset to white).

DIRECT READ-BACK IS MISSING (TODO, fails fast with --need-direct): there is no route for
  GetFabricPBRMaterialBaseColor(fabricIndex, face) nor for choosing Front/Back in the set call (the
  dispatcher FabricDispatcher::dispatchColor uses the plugin's fixed face). Proposed:
  GET /fabrics/<i>/base-color?face=0|1 and an optional "face" field on POST /set-fabric-color.
  H2 (Front vs Back) is therefore NOT testable now and is reported as blocked.
  PROXY used for H1/H3: export GLB and read materials[].pbrMetallicRoughness.baseColorFactor and images[]
  via rev-eng/scripts/glb_probe.py logic (the exporter may apply its own conversion; so a mismatch is a
  hint, not proof - list this limitation in RESULTS).

PRECONDITIONS: --avt and --dxf (>=1 piece; use a multi-piece block to also see per-pattern fabric index),
  optional --texture PNG for H3. Supervised, watchdog running. Fabric calls are async (PostMessage):
  the script resets /fabric-status/reset and polls /fabric-status until all_done before exporting.

STEPS
  1. new-project, clear, import avatar, import DXF. 2. POST /fabric-status/reset.
  3. For each colour in (255,0,0) (0,255,0) (128,128,128) (10,20,30): POST /set-fabric-color pattern 0,
     wait /fabric-status all_done, export out/e06/<colour>.glb, read baseColorFactor list.
  4. If --texture: set texture (/set-fabric-texture), export, then set colour white, export; compare images/materials.

EXPECTED OUTCOME
  * factors ~ rgb/255 exactly                  -> H1 (linear, no gamma). If ~ (rgb/255)^2.2 the exporter converts to linear.
  * factors unchanged / default                -> colour did not apply (dispatch failure; check fabric-status failed count).
  * colour set with texture leaves images[]    -> H3: reset to white when texturing/untexturing.
RECORD: fabric-status counters, per colour factor list, image counts, file sizes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e06")
COLOURS = [(255, 0, 0), (0, 255, 0), (128, 128, 128), (10, 20, 30)]


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt", required=True)
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--texture")
    ap.add_argument("--pattern", type=int, default=0)
    ap.add_argument("--need-direct", action="store_true")
    args = ap.parse_args()
    if args.need_direct:
        C.todo_missing_command("GetFabricPBRMaterialBaseColor(fabric, face) / Back face set",
                               "GET /fabrics/<i>/base-color?face=N, POST /set-fabric-color {face}",
                               "Direct Front/Back read-back is impossible without it.")
    C.plan_only(args, ["new-project, clear, import avatar+DXF", "reset fabric-status",
                       f"set colours {COLOURS} on pattern {args.pattern}, export GLB each, read baseColorFactor",
                       "optional texture / white-reset sequence (H3)", "H2 Front/Back: BLOCKED (no route)"])
    rec = C.Recorder("e06_fabric_colour_readback", args)
    C.preflight(rec)
    C.run_cmd(rec, "new-project", "/new-project", {}, args.queue_timeout)
    C.run_cmd(rec, "clear", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
    C.run_cmd(rec, "avatar", "/import-avatar-avt", {"path": args.avt.replace("\\", "/")}, args.queue_timeout)
    C.run_cmd(rec, "dxf", "/import-pattern", {"path": args.dxf.replace("\\", "/"), "scale": 1.0}, args.queue_timeout)
    if C.pattern_count(rec, "loaded") <= args.pattern:
        rec.finish("ABORT_NO_PATTERN")
        raise SystemExit("pattern index not present after import")
    C.post("/fabric-status/reset")
    table = []

    def snap(name):
        C.wait_fabric_done(rec)
        ex = C.export_scene(rec, name, os.path.join(OUT, name + ".glb"))
        row = C.glb_summary([ex["path"]])[0] if ex.get("bytes") else {}
        table.append({"name": name, "bytes": ex.get("bytes"), "factors": row.get("baseColorFactors"),
                      "images": row.get("images"), "materials": row.get("materials")})
        rec.step(f"read[{name}]", **table[-1])

    for r, g, b in COLOURS:
        C.run_cmd(rec, f"set-colour {r},{g},{b}", "/set-fabric-color",
                  {"pattern_index": args.pattern, "r": r, "g": g, "b": b}, args.queue_timeout)
        snap(f"col_{r}_{g}_{b}")
    if args.texture:
        C.run_cmd(rec, "set-texture", "/set-fabric-texture",
                  {"pattern_index": args.pattern, "texture_path": args.texture.replace("\\", "/")}, args.queue_timeout)
        snap("textured")
        C.run_cmd(rec, "set-white", "/set-fabric-color",
                  {"pattern_index": args.pattern, "r": 255, "g": 255, "b": 255}, args.queue_timeout)
        snap("textured_then_white")
    rec.note("H2 Front/Back: BLOCKED (no face parameter / no GetFabricPBRMaterialBaseColor route).")
    rec.data["table"] = table
    rec.finish("compare factors with rgb/255")


if __name__ == "__main__":
    C.guarded(main)
