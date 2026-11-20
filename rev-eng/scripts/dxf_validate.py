#!/usr/bin/env python
"""CLO DXF reader pre-flight validator (lane AT). stdlib only.

Applies the clean-import checklist from findings/32_dxf_reader_dispatch.md
(section 7) and units rule from findings/35 ($INSUNITS is the unit source).
Read-only. Usage:
  python -I dxf_validate.py [--json] [--tol 0.01] FILE_OR_DIR...
Exit code: 0 all PASS/WARN, 1 any FAIL.
"""
import argparse, glob, json, math, os, sys

SEV = {"PASS": 0, "WARN": 1, "FAIL": 2}
HANDLED = {"LINE", "POINT", "ARC", "CIRCLE", "TEXT", "MTEXT", "POLYLINE", "INSERT"}
IGNORED = {"SPLINE", "ELLIPSE", "DIMENSION", "SOLID", "LWPOLYLINE", "3DFACE", "HATCH", "LEADER", "TRACE", "ATTRIB", "ATTDEF"}
# LWPOLYLINE listed as ignored: finding 32 lists vendored-lib LWPOLYLINE string but the
# R12 reference never uses it; flag as WARN (unverified), not FAIL.
UNIT_SCALE = {1: 25.4, 5: 10.0, 6: 1000.0}
# annotation keys recognised by 0x40a1dc0 / 0x4096c80
KEYS = ["PIECE NAME", "SAMPLE SIZE", "SIZE", "ANNOTATION", "AUTHOR", "VERSION", "QUANTITY",
        "CATEGORY", "MATERIAL", "UNITS", "STYLE NAME", "PRODUCT", "CREATION DATE",
        "CREATION TIME", "GRADE RULE TABLE", "CURVE TOLERANCE", "ANSI/AAMA VERSION",
        "NUMBER OF SIZES", "SIZE LIST", "RULE"]
REQUIRED_KEYS = ["PIECE NAME", "SIZE", "QUANTITY"]       # per piece (checklist 3)
REQUIRED_GLOBAL = ["UNITS", "SAMPLE SIZE"]                # anywhere in file
OUTLINE_LAYERS = {"1"}
NOTCH_LAYERS = {"4", "80", "81", "82", "83"}
KNOWN_LAYERS = {"0", "Defpoints", "1", "2", "3", "4", "5", "6", "7", "8", "11", "13", "14", "15",
                "80", "81", "82", "83", "84", "85", "86", "87"}
SANE_MM = (50.0, 2000.0)


def read_pairs(path):
    with open(path, "rb") as f:
        raw = f.read().decode("latin-1")
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    pairs, bad = [], 0
    i = 0
    while i + 1 < len(lines):
        try:
            code = int(lines[i].strip())
        except ValueError:
            bad += 1
            i += 1
            continue
        pairs.append((code, lines[i + 1].strip(), i + 1))
        i += 2
    return pairs, bad


def fl(v):
    try:
        return float(v)
    except ValueError:
        return float("nan")


class Ent:
    def __init__(self, typ, line):
        self.type, self.line = typ, line
        self.d = {}      # first value per code
        self.pts = []    # (x,y,z) from 10/20/30 runs (LINE: 10 & 11)
        self.verts = []  # POLYLINE vertices
        self.layer = ""
        self.flag = 0
        self.text = ""
        self.name = ""

    def finish(self):
        self.layer = self.d.get(8, "")
        self.flag = int(fl(self.d.get(70, "0"))) if self.d.get(70, "0").lstrip("-").isdigit() else 0
        self.text = self.d.get(1, "")
        self.name = self.d.get(2, "")


def parse(path):
    pairs, bad = read_pairs(path)
    res = {"header": {}, "blocks": [], "entities": [], "sections": [], "eof": False,
           "bad_lines": bad, "npairs": len(pairs), "struct_errors": []}
    sec = None
    cur = None            # entity being built
    cur_poly = None
    cur_block = None
    hdr_var = None
    hdr_vals = {}
    pending_hdr = None

    def container():
        return cur_block["ents"] if cur_block is not None else res["entities"]

    def close_entity():
        nonlocal cur
        if cur is None:
            return
        cur.finish()
        if cur.type == "VERTEX" and cur_poly is not None:
            cur_poly.verts.append((fl(cur.d.get(10, "nan")), fl(cur.d.get(20, "nan")), fl(cur.d.get(30, "0"))))
        elif cur.type in ("SEQEND", "BLOCK"):
            pass
        else:
            container().append(cur)
        cur = None

    for code, val, ln in pairs:
        if code == 0:
            if sec == "HEADER":
                if val in ("ENDSEC",):
                    sec = None
                continue
            close_entity()
            if val == "SECTION":
                sec = "?"
                continue
            if val == "ENDSEC":
                sec = None
                cur_block = None
                cur_poly = None
                continue
            if val == "EOF":
                res["eof"] = True
                continue
            if sec == "BLOCKS" and val == "BLOCK":
                cur_block = {"name": "", "ents": [], "line": ln}
                res["blocks"].append(cur_block)
                cur = Ent("BLOCK", ln)
                continue
            if sec == "BLOCKS" and val == "ENDBLK":
                cur_block = None
                cur_poly = None
                continue
            if sec in ("ENTITIES", "BLOCKS"):
                cur = Ent(val, ln)
                if val == "POLYLINE":
                    cur_poly = cur
                elif val not in ("VERTEX", "SEQEND"):
                    cur_poly = None
                continue
            continue  # TABLES etc: ignored
        if sec == "?" and code == 2:
            sec = val
            res["sections"].append(val)
            continue
        if sec == "HEADER":
            if code == 9:
                hdr_var = val
                hdr_vals[hdr_var] = []
            elif hdr_var:
                hdr_vals[hdr_var].append((code, val))
            continue
        if cur is not None:
            if cur.type == "BLOCK":
                if code == 2 and not cur_block["name"]:
                    cur_block["name"] = val
                continue
            if code not in cur.d:
                cur.d[code] = val
            if code in (10, 20, 30, 11, 21, 31):
                if code == 10:
                    cur.pts.append([fl(val), float("nan"), 0.0])
                elif code == 20 and cur.pts:
                    cur.pts[-1][1] = fl(val)
                elif code == 30 and cur.pts:
                    cur.pts[-1][2] = fl(val)
                elif code == 11:
                    cur.pts.append([fl(val), float("nan"), 0.0])
                elif code == 21 and cur.pts:
                    cur.pts[-1][1] = fl(val)
                elif code == 31 and cur.pts:
                    cur.pts[-1][2] = fl(val)
    close_entity()
    res["header"] = hdr_vals
    return res


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def classify_piece(name, ents, ctx, tol, out):
    """Return list of (sev, check, msg) for one piece container."""
    r = []
    add = lambda s, c, m: r.append((s, c, m))
    layers = {}
    for e in ents:
        layers.setdefault(e.layer, []).append(e)
    info = {"name": name, "entities": len(ents), "layers": {k: len(v) for k, v in sorted(layers.items())}}

    # ---- boundary
    outlines = [e for e in ents if e.type == "POLYLINE" and e.layer in OUTLINE_LAYERS]
    lines1 = [e for e in ents if e.type == "LINE" and e.layer in OUTLINE_LAYERS]
    if not outlines:
        add("FAIL", "boundary", "no POLYLINE on layer 1 (piece would be empty/dropped)"
            + (f"; {len(lines1)} LINE(s) on layer 1 not joined by reader" if lines1 else ""))
    best = None
    for e in outlines:
        v = e.verts
        nonfin = [p for p in v if not all(math.isfinite(c) for c in p)]
        if nonfin:
            add("FAIL", "finite", f"layer-1 polyline line {e.line}: {len(nonfin)} non-finite vertex(es)")
            continue
        if len(v) < 3:
            add("FAIL", "boundary", f"layer-1 polyline line {e.line}: {len(v)} vertices (<3)")
            continue
        flagged = bool(e.flag & 1)
        gap = dist(v[0], v[-1])
        dup = gap <= 1e-9
        if flagged:
            if dup:
                add("WARN", "dup_last", f"closed-flag polyline line {e.line} also repeats first vertex "
                    "(zero-length closing segment; 0x409512c pop only runs on the auto-close path)")
        elif gap < tol:
            add("PASS", "closed", f"polyline line {e.line} open-flag but first/last gap {gap:.4g} < tol -> auto-closes")
        else:
            add("FAIL", "closed", f"layer-1 polyline line {e.line} not closed: flag70={e.flag}, "
                f"first/last gap {gap:.4g} mm > tol {tol}")
        if not out.get("_x") and False:
            pass
        if best is None or len(v) > len(best.verts):
            best = e
    if best is not None and best.verts:
        xs = [p[0] for p in best.verts]
        ys = [p[1] for p in best.verts]
        info["bbox_raw"] = [min(xs), min(ys), max(xs), max(ys)]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        s = ctx["scale"]
        info["bbox_mm"] = [round(w * s, 3), round(h * s, 3)]
        info["vertices"] = len(best.verts)
        lo, hi = SANE_MM
        if not (lo <= max(w, h) * s <= hi) or min(w, h) * s < 5:
            add("WARN", "size", f"bbox {w*s:.1f} x {h*s:.1f} mm outside sane garment range {lo:.0f}-{hi:.0f} mm")
        else:
            add("PASS", "size", f"bbox {w*s:.1f} x {h*s:.1f} mm")
    # non-finite elsewhere
    for e in ents:
        if e.type in ("POINT", "LINE", "TEXT") and any(not all(math.isfinite(c) for c in p) for p in e.pts):
            add("FAIL", "finite", f"{e.type} line {e.line} layer {e.layer}: non-finite coordinate")
    # ---- grain
    g = layers.get("7", [])
    gl = [e for e in g if e.type == "LINE" and len(e.pts) >= 2]
    gp = [e for e in g if e.type == "POLYLINE" and len(e.verts) == 2]
    if len(gl) + len(gp) == 0:
        add("WARN", "grain", "no layer-7 grainline (LINE with 2 end points)")
    elif len(gl) + len(gp) > 1:
        add("WARN", "grain", f"{len(gl)+len(gp)} grainlines on layer 7")
    else:
        add("PASS", "grain", "1 grainline on layer 7")
    if any(e.type == "POLYLINE" and len(e.verts) != 2 for e in g):
        add("WARN", "grain", "layer-7 POLYLINE with !=2 vertices")
    # ---- points
    for lay, label in (("2", "turn points"), ("3", "curve points"), ("13", "drill")):
        n = sum(1 for e in layers.get(lay, []) if e.type == "POINT")
        info[f"n_layer{lay}"] = n
    nn = sum(1 for lay in NOTCH_LAYERS for e in layers.get(lay, []) if e.type == "POINT")
    info["n_notch"] = nn
    if nn == 0:
        add("WARN", "notch", "no notch POINTs (layers 4/80-83)")
    if info["n_layer3"] == 0:
        add("WARN", "curve_pts", "no layer-3 curve POINTs: reader derives curves only from layer-3 POINTs (bulge unused)")
    if info["n_layer2"] == 0:
        add("WARN", "turn_pts", "no layer-2 turn POINTs")
    # layers 84-87
    if any(l in layers for l in ("84", "85", "86", "87")):
        add("PASS", "allowance", "has cut/seam-allowance layer " + ",".join(l for l in ("84", "85", "86", "87") if l in layers))
    # unknown layers / non-numeric
    odd = [l for l in layers if l not in KNOWN_LAYERS]
    if odd:
        nonnum = [l for l in odd if not l.lstrip("-").isdigit()]
        if nonnum:
            add("WARN", "layer_names", f"non-numeric layer name(s) {nonnum}: reader converts layer name to int")
        else:
            add("WARN", "layer_names", f"layer(s) {odd} have no decoded semantics")
    # ignored entities
    ig = {}
    for e in ents:
        if e.type in IGNORED:
            ig[e.type] = ig.get(e.type, 0) + 1
        elif e.type not in HANDLED and e.type not in ("VERTEX", "SEQEND", "BLOCK"):
            ig[e.type] = ig.get(e.type, 0) + 1
    if ig:
        add("WARN", "ignored_entities", f"entity types dropped by reader: {ig}")
    # ---- annotations
    texts = [e.text for e in ents if e.type in ("TEXT", "MTEXT")]
    ann = {}
    for t in texts:
        tu = t.upper()
        for k in KEYS:
            if tu.startswith(k):
                ann.setdefault(k, t)
                break
    info["annotations"] = ann
    info["text_count"] = len(texts)
    missing = [k for k in REQUIRED_KEYS if k not in ann]
    if missing:
        add("WARN", "annotations", f"piece lacks TEXT annotation(s): {missing}")
    else:
        add("PASS", "annotations", "PIECE NAME/SIZE/QUANTITY present")
    return r, info


def validate(path, tol=0.01):
    res = {"file": path, "checks": [], "pieces": []}
    chk = res["checks"]
    add = lambda s, c, m: chk.append({"sev": s, "check": c, "msg": m})
    try:
        if os.path.getsize(path) == 0:
            add("FAIL", "file", "empty file")
            res["status"] = "FAIL"
            return res
        d = parse(path)
    except Exception as ex:  # noqa
        add("FAIL", "file", f"unreadable: {ex}")
        res["status"] = "FAIL"
        return res
    if d["bad_lines"]:
        add("WARN", "syntax", f"{d['bad_lines']} non-integer group-code lines")
    for s in ("HEADER", "ENTITIES"):
        if s not in d["sections"]:
            add("FAIL" if s == "ENTITIES" else "WARN", "structure", f"missing {s} section")
    if not d["eof"]:
        add("FAIL", "structure", "no EOF record")
    else:
        add("PASS", "structure", "SECTION/ENDSEC/EOF present, sections=" + ",".join(d["sections"]))
    h = d["header"]
    acad = h.get("$ACADVER", [(1, "")])[0][1] if "$ACADVER" in h else None
    if acad is None:
        add("WARN", "header", "no $ACADVER")
    elif acad == "AC1009":
        add("PASS", "header", "$ACADVER AC1009 (R12, as CLO exports)")
    else:
        add("WARN", "header", f"$ACADVER {acad} (CLO exports AC1009)")
    scale = 1.0
    if "$INSUNITS" in h:
        try:
            u = int(float(h["$INSUNITS"][0][1]))
        except Exception:
            u = None
        if u is None:
            add("FAIL", "units", "$INSUNITS unparsable")
        else:
            scale = UNIT_SCALE.get(u, 1.0)
            if u in UNIT_SCALE:
                add("WARN", "units", f"$INSUNITS {u} => CLO multiplies geometry by {scale:g}; "
                    "only valid if coordinates really are in that unit")
            else:
                add("PASS", "units", f"$INSUNITS {u} => scale 1.0 (mm)" + ("" if u == 4 else " [not 4: treated as mm by reader]"))
    else:
        add("PASS", "units", "no $INSUNITS (as CLO reference): scale 1.0, mm assumed")
    meas = h.get("$MEASUREMENT")
    res["header"] = {"ACADVER": acad, "INSUNITS": h.get("$INSUNITS", [(0, None)])[0][1] if "$INSUNITS" in h else None,
                     "MEASUREMENT": meas[0][1] if meas else None}
    ctx = {"scale": scale}

    # pieces
    pieces = []
    for b in d["blocks"]:
        if b["name"].startswith("$") or b["name"].upper().startswith("*"):
            continue
        if any(e.type in ("POLYLINE", "LINE", "POINT", "TEXT") for e in b["ents"]):
            pieces.append((b["name"], b["ents"]))
    inserts = [e for e in d["entities"] if e.type == "INSERT"]
    top = [e for e in d["entities"] if e.type != "INSERT"]
    top_geom = [e for e in top if e.type in ("POLYLINE", "LINE", "POINT")]
    if top_geom and not pieces:
        pieces.append(("(top-level ENTITIES)", d["entities"]))
    elif top_geom and pieces:
        # reference puts extra TEXT/geometry at top level; count them but do not treat as piece
        pass
    res["insert_count"] = len(inserts)
    res["piece_count"] = len(pieces)
    if not pieces:
        add("FAIL", "pieces", "no piece geometry found")
    else:
        add("PASS", "pieces", f"{len(pieces)} piece container(s), {len(inserts)} INSERT(s)")
    if pieces and not inserts and d["blocks"]:
        add("WARN", "pieces", "BLOCKs present but ENTITIES has no INSERT (top-level loop resolves pieces via INSERT)")
    for e in inserts:
        names = {n for n, _ in pieces}
        if e.name not in names:
            add("WARN", "pieces", f"INSERT line {e.line} references block '{e.name}' with no geometry")
    # top-level TEXT annotation (reference puts header-ish text in ENTITIES)
    toptext = [e.text for e in top if e.type in ("TEXT", "MTEXT")]
    allann = set()
    for _, ents in pieces:
        for e in ents:
            if e.type in ("TEXT", "MTEXT"):
                allann.add(e.text.upper())
    for t in toptext:
        allann.add(t.upper())

    def has_key(k):
        return any(t.startswith(k) for t in allann)
    for k in REQUIRED_GLOBAL:
        if not has_key(k):
            add("WARN", "annotations", f"no '{k}:' TEXT anywhere in file")
    if has_key("UNITS"):
        u = next(t for t in allann if t.startswith("UNITS"))
        add("PASS", "annotations", f"found '{u}'")

    for name, ents in pieces:
        r, info = classify_piece(name, ents, ctx, tol, {})
        info["checks"] = [{"sev": s, "check": c, "msg": m} for s, c, m in r]
        sevs = [SEV[s] for s, _, _ in r] or [0]
        info["status"] = ["PASS", "WARN", "FAIL"][max(sevs)]
        res["pieces"].append(info)
    worst = max([SEV[c["sev"]] for c in chk] + [SEV[p["status"]] for p in res["pieces"]] + [0])
    res["status"] = ["PASS", "WARN", "FAIL"][worst]
    return res


def text_report(r):
    o = [f"== {r['file']}  [{r['status']}]  pieces={r.get('piece_count')} header={r.get('header')}"]
    for c in r["checks"]:
        o.append(f"  {c['sev']:4} {c['check']}: {c['msg']}")
    for p in r["pieces"]:
        o.append(f" piece '{p['name']}' [{p['status']}] bbox_mm={p.get('bbox_mm')} verts={p.get('vertices')} layers={p['layers']}")
        for c in p["checks"]:
            if c["sev"] != "PASS":
                o.append(f"    {c['sev']:4} {c['check']}: {c['msg']}")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tol", type=float, default=0.01)
    a = ap.parse_args()
    files = []
    for p in a.paths:
        if os.path.isdir(p):
            files += glob.glob(os.path.join(p, "**", "*.dxf"), recursive=True)
        else:
            files += glob.glob(p) or [p]
    results = [validate(f, a.tol) for f in files]
    if a.json:
        json.dump(results, sys.stdout, indent=1, default=str)
        print()
    else:
        for r in results:
            print(text_report(r))
        print("\nSUMMARY: " + ", ".join(f"{s}={sum(1 for r in results if r['status']==s)}" for s in SEV))
    sys.exit(1 if any(r["status"] == "FAIL" for r in results) else 0)


if __name__ == "__main__":
    main()
