"""E02 - patched .avt floats re-deform test (lane K hypothesis 1, old E9)

HYPOTHESIS (findings/19): the .avt load path never calls the resize driver 0x511a1b0, so changing the
  stored resizing flags (`enLastUpdateMode` 4->1/2, `bHeightLinked` true->false) in a patched .avt copy
  does NOT move any vertex. Falsified only if the exported/re-saved avatar positions differ from the
  unpatched baseline.

PRECONDITIONS
  * A stock .avt (--avt) whose MVresizingMap contains both fields (all repo templates do).
  * For --live: supervised CLO, e07 watchdog open, nothing else in the scene.
  * Copies are written ONLY under experiments/out/e02/ ; no repo file is modified.

MODES
  default (no --live): PREPARE ONLY. Reads --avt, writes variant copies and a manifest:
      baseline.avt        byte-identical re-zip of the same .dan (control: shows re-zip alone changes nothing)
      mode1.avt           enLastUpdateMode = 1
      mode2.avt           enLastUpdateMode = 2
      unlinked.avt        bHeightLinked = false
      mode1_unlinked.avt  both
    Patches are same-size in-place edits (int32 / bool) located with avs_grammar.leaf_map, imported by
    path from rev-eng/scripts/avs_grammar.py. The 600-byte stale ZIP-length header field 0x24 is left as
    CLO's reader apparently ignores it (lane Z); the SHA-256 digest does not cover the ZIP so it stays valid.
    Then run:  python -I rev-eng/scripts/avs_grammar.py dandiff <baseline.avt> <variant.avt>  to confirm
    only the intended leaves differ.
  --live: for baseline + each variant: /clear-avatars, import the copy, GET /avatars/state, export GLB
    (/export) to out/e02/<name>.glb, and compare the GLB .bin sha256 with the baseline's.

STEPS (live) per variant: clear -> import-avatar-avt (import_avatar) -> /avatars/state -> /export glb.
  (Re-saving the .avt via /export-avatar-avt is optional: --reexport-avt.)

EXPECTED OUTCOME
  * every variant's GLB bin sha == baseline's                -> hypothesis holds: .avt flags cannot trigger deformation. Close lane K.
  * a variant's bin sha differs                              -> CLO re-derives geometry from those fields on load: new route. Run dandiff
                                                                 on the re-exported .avt and record max position delta.
  * baseline differs from a previous un-patched export       -> export non-determinism; repeat baseline twice before concluding.
RECORD: hashes, GLB vertex counts, state property dicts, any dialog, plugin trace_log BEGIN/END lines.
"""
import hashlib
import io
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

OUT = os.path.join(C.OUT_DIR, "e02")

VARIANTS = {
    "baseline": {},
    "mode1": {"enLastUpdateMode": 1},
    "mode2": {"enLastUpdateMode": 2},
    "unlinked": {"bHeightLinked": False},
    "mode1_unlinked": {"enLastUpdateMode": 1, "bHeightLinked": False},
}


def split_avt(raw):
    zs = raw.find(b"PK\x03\x04")
    if zs < 0:
        raise SystemExit("not an .avt container (no ZIP signature)")
    return raw[:zs], zipfile.ZipFile(io.BytesIO(raw[zs:]))


def patch_dan(dan, edits, g):
    """Same-size in-place edits for leaves whose path ends with /<field>. Returns (bytes, report)."""
    buf, rep = bytearray(dan), []
    leaves = g.leaf_map(bytes(dan))
    for field, val in edits.items():
        hits = [(p, o, s, t) for p, (o, s, t) in leaves.items() if p.endswith("/" + field)]
        if not hits:
            rep.append({"field": field, "error": "leaf not found"})
            continue
        for p, o, s, t in hits:
            old = bytes(buf[o:o + s])
            if t == g.T_INT and s == 4:
                new = struct.pack("<i", int(val))
            elif t == g.T_BOOL and s == 1:
                new = bytes([1 if val else 0])
            else:
                rep.append({"field": field, "path": p, "error": f"unsupported type {t} size {s}"})
                continue
            buf[o:o + s] = new
            rep.append({"field": field, "path": p, "old": old.hex(), "new": new.hex()})
    return bytes(buf), rep


def build_variant(avt_path, name, edits, g):
    raw = open(avt_path, "rb").read()
    prefix, z = split_avt(raw)
    out = io.BytesIO()
    report = []
    with zipfile.ZipFile(out, "w") as w:
        for zi in z.infolist():
            data = z.read(zi)
            if zi.filename.lower().endswith(".dan") and edits:
                data, report = patch_dan(data, edits, g)
            ni = zipfile.ZipInfo(zi.filename, zi.date_time)
            ni.compress_type, ni.comment, ni.extra = zi.compress_type, zi.comment, zi.extra
            ni.create_system, ni.external_attr, ni.internal_attr, ni.flag_bits = (
                zi.create_system, zi.external_attr, zi.internal_attr, zi.flag_bits)
            w.writestr(ni, data)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"{name}.avt")
    with open(dst, "wb") as f:
        f.write(prefix + out.getvalue())
    return dst, report


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt", required=True, help="source .avt (read only)")
    ap.add_argument("--reexport-avt", action="store_true")
    args = ap.parse_args()
    g = C.avs_grammar()
    rec = C.Recorder("e02_avt_patch_redeform", args)
    made = {}
    for name, edits in VARIANTS.items():
        dst, rep = build_variant(args.avt, name, edits, g)
        made[name] = dst
        rec.step(f"prepare[{name}]", file=dst, sha256_16=hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16],
                 patches=rep)
    rec.note("Verify with: python -I rev-eng/scripts/avs_grammar.py dandiff out/e02/baseline.avt out/e02/<variant>.avt")
    if not args.live:
        rec.note("PREPARE ONLY (no --live): plugin not contacted.")
        rec.finish("prepared")
        return
    C.preflight(rec)
    shas = {}
    for name, path in made.items():
        C.run_cmd(rec, f"clear[{name}]", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
        C.run_cmd(rec, f"import[{name}]", "/import-avatar-avt", {"path": path.replace("\\", "/")}, args.queue_timeout)
        C.avatar_state(rec, name)
        ex = C.export_scene(rec, f"export[{name}]", os.path.join(OUT, f"{name}.glb"))
        if ex.get("bytes"):
            row = C.glb_summary([ex["path"]])[0]
            shas[name] = row.get("bin_sha")
            rec.step(f"glb[{name}]", **{k: row.get(k) for k in ("bin_sha", "verts", "tris", "bin_len")})
        if args.reexport_avt:
            C.run_cmd(rec, f"export-avt[{name}]", "/export-avatar-avt",
                      {"path": os.path.join(OUT, f"{name}.reexport.avt").replace("\\", "/")}, args.queue_timeout)
    base = shas.get("baseline")
    verdict = {n: ("same-as-baseline" if s == base else "DIFFERENT") for n, s in shas.items()}
    rec.note(f"verdict per variant: {verdict}")
    rec.finish(str(verdict))


if __name__ == "__main__":
    C.guarded(main)
