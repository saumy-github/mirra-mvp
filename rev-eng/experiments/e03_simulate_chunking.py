"""E03 - Simulate step-chunking restart test (Folding/Draping phase), old E7 + lane X caveat

HYPOTHESIS (findings/29 lane X): each Simulate(n) call may restart the automatic "Folding" (frames 0-9,
  only if a foldable item exists) / "Draping" (until 50 frames total) arrangement phase from frame 0,
  so 12 x Simulate(10) would NOT equal one Simulate(120) (lane R advised chunking; X contradicts).
  Alternative H-EQ: step counter persists, results identical (within solver determinism).

PRECONDITIONS
  * Garment scene reproducible from files: --avt (avatar) and --dxf (pattern DXF) OR --zprj.
    Without seams/arrangement the cloth may fall freely; that is acceptable for a determinism comparison,
    but use a real block DXF + `/create-seam` if you want a meaningful drape (not automated here).
  * --zprj opens through ImportFile via /import-avatar-avt method=import_file (the only generic ImportFile
    route; the route name is misleading and this path is UNVERIFIED for .zprj -> type 0x1C). Prefer avt+dxf.
  * CPU simulation mode, avoid scenes with Buttons (modal "Negative thread lengths" box), GPU mode shows
    out-of-memory modals. Keep e07 watchdog running. >10 GB free disk.
  * Determinism control: --repeat-control also runs the single Simulate(total) TWICE; if those two differ,
    chunk-vs-single differences are not interpretable.

READ-BACK: no route returns vertex positions or a vertex hash (TODO: proposed GET /scene/vertex-hash ->
  hash of GetClothMeshVertices / avatar+garment positions). Fallback used here: /export format=glb after
  each variant, then compare GLB .bin sha256 and vertex/triangle counts via rev-eng/scripts/glb_probe.py.
  A GLB hash is position-complete for exported meshes, so equality is meaningful; inequality needs the
  control to interpret. Pass --need-vertex-hash to fail fast instead of using the fallback.

STEPS
  For each variant [single120, chunk12x10, (control single120 again)]:
   1. /new-project  2. /clear-avatars  3. import avatar  4. import DXF (or zprj)
   5. /simulate {steps}: once with total, or N times with total/N, timing each call (wall-clock) and waiting for idle
   6. /export glb -> out/e03/<variant>.glb ; glb_probe summary.

EXPECTED OUTCOME
  * bin sha identical (and control identical)         -> H-EQ: chunking is safe; use small chunks for progress/modal handling.
  * chunk != single, control == control               -> H-RESTART (or chunk boundaries change solver state): do NOT chunk;
                                                          use one long Simulate with the watchdog. Compare per-call wall times:
                                                          if each chunk takes roughly constant long time the phase restarts.
  * control != control                                -> solver non-deterministic; compare max vertex deltas instead (need a
                                                          vertex-read route) and treat results as inconclusive.
  * per-call time: chunk calls much slower than 1/12 of single -> restart overhead; record all times.
RECORD: per-call seconds, results message, GLB sha/vertex counts, any modal text, CLO health afterwards.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e03")


def build_scene(rec, args, tag):
    C.run_cmd(rec, f"{tag}.new-project", "/new-project", {}, args.queue_timeout)
    C.run_cmd(rec, f"{tag}.clear-avatars", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
    if args.avt:
        C.run_cmd(rec, f"{tag}.avatar", "/import-avatar-avt", {"path": args.avt.replace("\\", "/")}, args.queue_timeout)
    if args.dxf:
        C.run_cmd(rec, f"{tag}.dxf", "/import-pattern", {"path": args.dxf.replace("\\", "/"), "scale": 1.0},
                  args.queue_timeout)
    if args.zprj:
        C.run_cmd(rec, f"{tag}.zprj", "/import-avatar-avt",
                  {"path": args.zprj.replace("\\", "/"), "method": "import_file"}, args.queue_timeout)
    C.pattern_count(rec, tag)


def simulate(rec, args, tag, chunks, per):
    times = []
    for i in range(chunks):
        t = time.time()
        r = C.run_cmd(rec, f"{tag}.simulate[{i}] steps={per}", "/simulate", {"steps": per}, args.sim_timeout)
        times.append(round(time.time() - t, 2))
        if not r.get("ok"):
            rec.note(f"{tag}: simulate chunk {i} not ok")
    rec.step(f"{tag}.times", seconds=times, total=round(sum(times), 2))
    return times


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt")
    ap.add_argument("--dxf")
    ap.add_argument("--zprj")
    ap.add_argument("--total", type=int, default=120)
    ap.add_argument("--chunks", type=int, default=12)
    ap.add_argument("--sim-timeout", type=float, default=600.0)
    ap.add_argument("--repeat-control", action="store_true")
    ap.add_argument("--need-vertex-hash", action="store_true")
    args = ap.parse_args()
    if args.need_vertex_hash:
        C.todo_missing_command("a vertex-position hash after Simulate", "GET /scene/vertex-hash",
                               "No route exposes cloth/avatar vertices; fallback is GLB bin hash.")
    if not (args.zprj or (args.avt and args.dxf)):
        raise SystemExit("give --avt and --dxf, or --zprj")
    if args.total % args.chunks:
        raise SystemExit("--total must be divisible by --chunks")
    C.plan_only(args, [
        "for variants single(total), chunked(chunks x total/chunks)" + (", single again (control)" if args.repeat_control else ""),
        "new-project, clear-avatars, import avatar + DXF (or zprj), /simulate, /export glb, glb_probe compare"])
    rec = C.Recorder("e03_simulate_chunking", args)
    C.preflight(rec)
    plan = [("single", 1, args.total), ("chunked", args.chunks, args.total // args.chunks)]
    if args.repeat_control:
        plan.append(("single_control", 1, args.total))
    paths = []
    for tag, chunks, per in plan:
        build_scene(rec, args, tag)
        simulate(rec, args, tag, chunks, per)
        ex = C.export_scene(rec, f"{tag}.export", os.path.join(OUT, f"{tag}.glb"))
        if ex.get("bytes"):
            paths.append(ex["path"])
    rows = C.glb_summary(paths)
    for r in rows:
        rec.step("glb", **{k: r.get(k) for k in ("path", "bytes", "bin_sha", "verts", "tris", "error")})
    shas = {os.path.basename(r["path"]): r.get("bin_sha") for r in rows}
    rec.note(f"bin shas: {shas}")
    rec.finish(str(shas))


if __name__ == "__main__":
    C.guarded(main)
