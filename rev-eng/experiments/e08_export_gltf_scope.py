"""E08 - ExportGLTF/GLB scope: component lists vs whole scene (old E8, R11) with glb_probe summary

HYPOTHESIS (findings/25 lane T, 07): ExportGLTF with pattern/avatar component lists exports only the
  selected components (smaller file, fewer nodes/meshes); the whole-scene export includes avatar + all garment
  pieces. Format glb (ExportGLB) = one binary; format gltf = JSON + .bin + loose textures.

PLUGIN LIMITS (read from /export handler, RestPlugin_windows.cpp ~1920-1950)
  * Only options.scale=0.001, bExportGarment = (patterns loaded > 0), bExportAvatar = true are set; there is
    NO way to pass `patternList` (e.g. {0,1}) or an avatar list. COMPONENT LISTS ARE BLOCKED:
    TODO proposed POST /export {path, format, pattern_list:[..], avatar_list:[..], export_garment, export_avatar}.
    `--component-lists` fails fast (exit 3).
  * What IS testable now: whole-scene scope variants by scene content:
      V1 avatar only           (no DXF loaded -> bExportGarment false)
      V2 avatar + garment      (DXF loaded)
      V3 garment-only is NOT achievable (bExportAvatar is always true)
    and format variants glb vs gltf for each, giving size/hash/node counts.

PRECONDITIONS: --avt, --dxf; supervised; disk space (gltf writes loose files; use an empty output dir
  out/e08/). glb_probe is imported by path from rev-eng/scripts/glb_probe.py (read-only).

STEPS: new-project, clear, import avatar -> export V1 as glb and gltf -> import DXF -> export V2 as glb
  and gltf -> glb_probe summary of all files; print the TSV-like table.

EXPECTED OUTCOME
  * V2 > V1 in bytes/nodes/meshes, differing by ~garment pieces       -> exporter follows scene content; component lists unverified.
  * V1 contains garment nodes                                          -> bExportGarment flag ignored.
  * glb vs gltf node/mesh/vertex counts equal                          -> same exporter, different container (lane T vertex rule).
  * ExportGLB returns no files                                         -> check host_matches_sdk (vtable skew), see R1.
RECORD: file sizes, bin sha, nodes/meshes/verts/tris/materials/images, any 'Export failed' message.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e08")


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt", required=True)
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--component-lists", action="store_true",
                    help="fail fast: no plugin route for patternList/avatar lists")
    args = ap.parse_args()
    if args.component_lists:
        C.todo_missing_command("ExportGLTF with ImportExportOption pattern/avatar component lists",
                               "POST /export {pattern_list, avatar_list, export_garment, export_avatar}",
                               "The /export handler never sets component lists.")
    C.plan_only(args, ["new-project, clear, import avatar", "export V1 glb + gltf (avatar only)",
                       "import DXF", "export V2 glb + gltf (avatar+garment)", "glb_probe summary of all files",
                       "component-list variants: BLOCKED (no route)"])
    rec = C.Recorder("e08_export_gltf_scope", args)
    C.preflight(rec)
    C.run_cmd(rec, "new-project", "/new-project", {}, args.queue_timeout)
    C.run_cmd(rec, "clear", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
    C.run_cmd(rec, "avatar", "/import-avatar-avt", {"path": args.avt.replace("\\", "/")}, args.queue_timeout)
    files = []
    for fmt in ("glb", "gltf"):
        ex = C.export_scene(rec, f"V1_avatar_only_{fmt}", os.path.join(OUT, f"v1_{fmt}", f"v1.{fmt}"), fmt)
        if ex.get("bytes"):
            files.append(ex["path"])
    C.run_cmd(rec, "dxf", "/import-pattern", {"path": args.dxf.replace("\\", "/"), "scale": 1.0}, args.queue_timeout)
    C.pattern_count(rec, "loaded")
    for fmt in ("glb", "gltf"):
        ex = C.export_scene(rec, f"V2_avatar_garment_{fmt}", os.path.join(OUT, f"v2_{fmt}", f"v2.{fmt}"), fmt)
        if ex.get("bytes"):
            files.append(ex["path"])
    rows = C.glb_summary(files)
    for r in rows:
        rec.step("glb_probe", **{k: r.get(k) for k in ("path", "kind", "bytes", "bin_len", "bin_sha", "nodes",
                                                       "meshes", "verts", "tris", "materials", "images", "error")})
    rec.note("component lists: BLOCKED (no plugin route).")
    rec.data["table"] = rows
    rec.finish("compare V1 vs V2")


if __name__ == "__main__":
    C.guarded(main)
