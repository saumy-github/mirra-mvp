"""E05 - ImportDXF with/without AAMA annotations and $INSUNITS: units and pattern count (old E1 + E11, R3/R4)

HYPOTHESES (findings/22 lane P, 32 lane AA)
  H1: units come from a `UNITS: METRIC|ENGLISH` text entity (AAMA annotation), NOT from $INSUNITS/$MEASUREMENT;
      a DXF without the entity is converted as a baseline/unknown unit -> bounding boxes scale wrongly
      (e.g. x25.4 or x10) vs the annotated file.
  H2: ImportDXF returns true even for empty/invalid files; only GetPatternCount growth tells the truth (R4).
  H3: the plugin's `scale` is ignored (m_bAutoScale true), so scale=1 and scale=2 give identical boxes.

PRECONDITIONS
  * Files to compare, each passed as --dxf label=path (at least two: e.g. ours=<writer output>,
    ref=product_ingestion/clo_block/reference_dxf/<file>.dxf). Optional negative controls: --with-empty
    (writes an empty .dxf), --with-text (text file named .dxf) under out/e05/ ; these are the old E1 cases and
    can raise a MODAL box -> keep e07 watchdog running; the script's timeout then aborts.
  * --make-variants SRC writes out/e05/<name>_insunits_removed.dxf and _insunits_1.dxf from SRC by editing
    only the `$INSUNITS` header variable (header text surgery; harmless for UNITS entity). Adding/removing
    the `UNITS:` / `PIECE NAME:` / `SAMPLE SIZE:` text entities needs the exact entity layout from the
    reference DXF: TODO (not guessed here); craft those variants by hand and pass them with --dxf.
  * Default isolation: /new-project before each file (known good once host_matches_sdk is true). With
    --no-new-project files are appended and indices offset instead.

STEPS per file: new-project -> GET /patterns/count (n0) -> POST /import-pattern {path, scale} ->
  count n1 -> for i in n0..n1-1: GET /patterns/<i>/bbox (GetBoundingBoxOfPattern, CLO internal mm per the
  plugin comments) and /patterns/<i>/input -> record bbox dims, area, count delta. --scale2 repeats with scale 2.0 (H3).

EXPECTED OUTCOME
  * annotated and un-annotated differ by a clean factor (10, 25.4...)   -> H1 confirmed; writer must emit UNITS entity (R3).
  * return true but count delta 0 for empty/text files                   -> H2 confirmed; gate on count (R4).
  * scale 2.0 == scale 1.0 boxes                                         -> H3 confirmed; scale is ignored.
  * delta differs from #pieces in file                                   -> notches/other layers create or drop pieces; record.
RECORD: return bool, count delta, bbox min/max/width/height per piece, area, units guess (width vs expected mm),
  modal text. Compare against product_ingestion clo_default_ground_truth.json by hand.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e05")


def make_variants(src):
    os.makedirs(OUT, exist_ok=True)
    txt = open(src, "r", encoding="utf-8", errors="replace").read()
    base = os.path.splitext(os.path.basename(src))[0]
    pat = re.compile(r"(\$INSUNITS\s*\r?\n\s*70\s*\r?\n)\s*-?\d+")
    if not pat.search(txt):
        raise SystemExit("no $INSUNITS header variable found in source; cannot build variants")
    outs = {}
    outs[f"{base}_insunits_1"] = pat.sub(lambda m: m.group(1) + "     1", txt)
    outs[f"{base}_insunits_0"] = pat.sub(lambda m: m.group(1) + "     0", txt)
    paths = {}
    for n, t in outs.items():
        p = os.path.join(OUT, n + ".dxf")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(t)
        paths[n] = p
    return paths


def one_file(rec, args, label, path, scale):
    tag = f"{label}@{scale}"
    if not args.no_new_project:
        C.run_cmd(rec, f"{tag}.new-project", "/new-project", {}, args.queue_timeout)
    n0 = C.pattern_count(rec, tag + ".before")
    r = C.run_cmd(rec, f"{tag}.import", "/import-pattern", {"path": path.replace("\\", "/"), "scale": scale},
                  args.queue_timeout)
    n1 = C.pattern_count(rec, tag + ".after")
    rows = []
    for i in range(max(n0, 0), max(n1, 0)):
        bb = C.get(f"/patterns/{i}/bbox", timeout=30)
        rows.append({"index": i, "bbox": bb.get("bbox"), "area": bb.get("area")})
    rec.step(f"{tag}.summary", return_ok=r.get("ok"), count_before=n0, count_after=n1, delta=n1 - n0, pieces=rows)
    return {"label": label, "scale": scale, "ok": r.get("ok"), "delta": n1 - n0, "pieces": rows}


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--dxf", action="append", default=[], help="label=path (repeatable)")
    ap.add_argument("--make-variants", help="source DXF to derive $INSUNITS variants from (offline step)")
    ap.add_argument("--with-empty", action="store_true")
    ap.add_argument("--with-text", action="store_true")
    ap.add_argument("--scale2", action="store_true")
    ap.add_argument("--no-new-project", action="store_true")
    args = ap.parse_args()
    files = {}
    for item in args.dxf:
        lab, _, p = item.partition("=")
        files[lab] = p
    if args.make_variants:
        files.update(make_variants(args.make_variants))
        print("variants written:", {k: v for k, v in files.items()})
    if args.with_empty or args.with_text:
        os.makedirs(OUT, exist_ok=True)
        if args.with_empty:
            p = os.path.join(OUT, "empty.dxf")
            open(p, "wb").close()
            files["neg_empty"] = p
        if args.with_text:
            p = os.path.join(OUT, "text.dxf")
            open(p, "w").write("this is not a dxf\n")
            files["neg_text"] = p
    if not files:
        raise SystemExit("nothing to import: use --dxf label=path and/or --make-variants")
    C.plan_only(args, [f"import {k} -> {v}" for k, v in files.items()] +
                ["each: new-project, count, /import-pattern, count, bbox per new piece", "--scale2 repeats at scale 2.0"])
    rec = C.Recorder("e05_importdxf_units", args)
    C.preflight(rec)
    results = []
    for lab, p in files.items():
        results.append(one_file(rec, args, lab, p, 1.0))
        if args.scale2 and not lab.startswith("neg_"):
            results.append(one_file(rec, args, lab, p, 2.0))
    rec.data["table"] = results
    rec.finish("compare table")


if __name__ == "__main__":
    C.guarded(main)
