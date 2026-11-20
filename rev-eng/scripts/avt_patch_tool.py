"""avt_patch_tool.py - CLO container (.avt/.zprj/.zpac) patcher. Stdlib only. Default is --dry-run.
Usage:
  python -I avt_patch_tool.py list IN [--grep TXT]           list .dan leaves (off,size,type,path)
  python -I avt_patch_tool.py meshes IN                      qsName / bVisible per mesh transformer
  python -I avt_patch_tool.py features IN                    listFeatureValues floats
  python -I avt_patch_tool.py patch IN OUT [--set-feature IDX=VAL]... [--hide NAME]... [--show NAME]... [--write]
Rules: same-length in-place edits only; header prefix kept except 0x24 (ZIP length), digest recomputed
(SHA-256(file[0:zo-68]+salt), findings/31). Header region length never changes (checked). Writes only if all
round-trip checks pass. This does NOT make CLO re-deform the mesh from floats (findings 13/19)."""
import sys, struct, zipfile, io, hashlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs_grammar as g
SALT = b"scrampling&$%!@#mvfileheader"


def split(raw):
    zo, zl = struct.unpack_from('<II', raw, 0x20)
    if raw[zo:zo+4] != b'PK\x03\x04':
        raise SystemExit('no PK at header ZIP offset 0x%x' % zo)
    if struct.unpack_from('<I', raw, zo-68)[0] != 64:
        raise SystemExit('bad digest record length')
    return zo, zl


def digest_ok(raw):
    zo, _ = split(raw)
    return raw[zo-64:zo] == hashlib.sha256(raw[:zo-68] + SALT).hexdigest().encode()


def read_zip(raw, zo):
    z = zipfile.ZipFile(io.BytesIO(raw[zo:]))
    infos = z.infolist()
    return infos, [z.read(i) for i in infos]


def dan_index(infos):
    c = [k for k, i in enumerate(infos) if i.filename.lower().endswith('.dan')]
    if len(c) != 1:
        raise SystemExit('expected exactly 1 .dan member, found %d' % len(c))
    return c[0]


def list_edits(dan, feats, hide, show):
    """return list of (abs_off, new_bytes, description)."""
    lm = g.leaf_map(dan)
    edits = []
    if feats:
        off, sz, ty = lm['/mapResizingAvatar/listFeatureValues']
        c = struct.unpack_from('<I', dan, off)[0]
        base = off + 5 + 4*c
        for idx, val in feats:
            if not 0 <= idx < c:
                raise SystemExit('feature index %d out of range (count %d)' % (idx, c))
            old = struct.unpack_from('<f', dan, base+4*idx)[0]
            edits.append((base+4*idx, struct.pack('<f', val), 'feature[%d] %.6g -> %.6g' % (idx, old, val)))
    for names, flag in ((hide, 0), (show, 1)):
        for nm in names:
            hit = 0
            for p, (o, s, t) in lm.items():
                if p.startswith('/mapTransformer3D') and p.endswith('/mapElement/qsName') and dan[o:o+s] == nm.encode():
                    bp = p[:-len('qsName')] + 'bVisible'
                    if bp not in lm or lm[bp][1] != 1:
                        raise SystemExit('no 1-byte bVisible for ' + p)
                    bo = lm[bp][0]
                    hit += 1
                    edits.append((bo, bytes([flag]), 'bVisible[%s @%d] %d -> %d' % (nm, bo, dan[bo], flag)))
            if not hit:
                raise SystemExit('mesh qsName not found: ' + nm)
    return edits


def build_zip(infos, datas):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w') as z:
        for i, d in zip(infos, datas):
            zi = zipfile.ZipInfo(i.filename, i.date_time)
            zi.compress_type = i.compress_type
            zi.external_attr = i.external_attr
            zi.create_system = i.create_system
            zi.comment = i.comment
            zi.extra = i.extra
            if i.compress_type == zipfile.ZIP_DEFLATED:
                z.writestr(zi, d, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            else:
                z.writestr(zi, d, compress_type=i.compress_type)
    return bio.getvalue()


def patch(src, dst, feats, hide, show, write):
    raw = open(src, 'rb').read()
    zo, zl = split(raw)
    print('input: %d bytes, zip_off %d, hdr zip_len %d (real %d), digest_ok=%s' % (len(raw), zo, zl, len(raw)-zo, digest_ok(raw)))
    infos, datas = read_zip(raw, zo)
    k = dan_index(infos)
    dan = datas[k]
    if g.enc_block(g.parse(dan)) != dan:
        raise SystemExit('FAIL: .dan does not re-encode byte-identically')
    edits = list_edits(dan, feats, hide, show)
    nd = bytearray(dan)
    for off, nb, desc in edits:
        nd[off:off+len(nb)] = nb
        print('  edit @%d len %d: %s' % (off, len(nb), desc))
    nd = bytes(nd)
    datas2 = list(datas)
    datas2[k] = nd
    zb = build_zip(infos, datas2)
    hdr = bytearray(raw[:zo])
    struct.pack_into('<I', hdr, 0x24, len(zb))
    hdr[zo-64:zo] = hashlib.sha256(bytes(hdr[:zo-68]) + SALT).hexdigest().encode()
    if len(hdr) != zo:
        raise SystemExit('FAIL: header length changed')
    out = bytes(hdr) + zb
    # ---- verification (re-parse the output)
    errs = []
    zo2, zl2 = split(out)
    if zo2 != zo:
        errs.append('zip_off changed')
    if zl2 != len(out) - zo2:
        errs.append('0x24 != real zip len')
    if not digest_ok(out):
        errs.append('digest verify failed')
    other_hdr = [i for i in range(zo-68) if out[i] != raw[i] and not (0x24 <= i < 0x28)]
    if other_hdr:
        errs.append('unexpected header byte changes: %s' % other_hdr[:8])
    z2 = zipfile.ZipFile(io.BytesIO(out[zo2:]))
    bad = z2.testzip()
    if bad is not None:
        errs.append('testzip failed: ' + str(bad))
    if [i.filename for i in z2.infolist()] != [i.filename for i in infos]:
        errs.append('member order/names differ')
    for i, (n, d0) in enumerate(zip(z2.infolist(), datas)):
        if i != k and z2.read(n) != d0:
            errs.append('member %s content differs' % n.filename)
    d2 = z2.read(z2.infolist()[k])
    changed = []
    if len(d2) != len(dan):
        errs.append('.dan length changed')
    else:
        changed = [i for i in range(len(dan)) if dan[i] != d2[i]] if dan != d2 else []
    if g.enc_block(g.parse(d2)) != d2:
        errs.append('.dan re-encode mismatch')
    exp = set(o + j for o, nb, _ in edits for j in range(len(nb)))
    if not set(changed) <= exp:
        errs.append('bytes differ outside intended edits: %d' % len(set(changed) - exp))
    if d2 != nd:
        errs.append('.dan readback != intended bytes')
    print('diff report: .dan bytes changed %d (intended window %d bytes); header changes: 0x24 + digest only' % (len(changed), len(exp)))
    print('out: %d bytes, new 0x24=%d, new digest %s...' % (len(out), zl2, hdr[zo-64:zo].decode()[:16]))
    if errs:
        print('VERIFY FAILED:')
        for e in errs:
            print('  -', e)
        raise SystemExit(2)
    print('VERIFY OK')
    if write:
        open(dst, 'wb').write(out)
        print('wrote', dst)
    else:
        print('dry-run: nothing written (use --write)')


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return
    cmd, src = a[0], a[1]
    if cmd in ('list', 'meshes', 'features'):
        raw = open(src, 'rb').read()
        zo, _ = split(raw)
        infos, datas = read_zip(raw, zo)
        dan = datas[dan_index(infos)]
        lm = g.leaf_map(dan)
        if cmd == 'list':
            gr = a[a.index('--grep')+1] if '--grep' in a else ''
            for p, (o, s, t) in lm.items():
                if gr in p:
                    print(o, s, hex(t), p)
        elif cmd == 'meshes':
            for p, (o, s, t) in lm.items():
                if p.endswith('/mapElement/qsName') and '/mapTransformer3D' in p:
                    bp = p[:-6] + 'bVisible'
                    has = bp in lm
                    print('%-24s bVisible@%s=%s depth=%d' % (dan[o:o+s].decode('latin1')[:24], lm[bp][0] if has else '-', dan[lm[bp][0]] if has else '-', p.count('/')))
        else:
            o, s, t = lm['/mapResizingAvatar/listFeatureValues']
            c = struct.unpack_from('<I', dan, o)[0]
            for i in range(c):
                print(i, g.FEATURE_NAMES.get(i, '?'), round(struct.unpack_from('<f', dan, o+5+4*c+4*i)[0], 4))
    elif cmd == 'patch':
        dst = a[2]
        feats, hide, show = [], [], []
        i = 3
        while i < len(a):
            if a[i] == '--set-feature':
                k, v = a[i+1].split('=')
                feats.append((int(k), float(v)))
                i += 2
            elif a[i] == '--hide':
                hide.append(a[i+1])
                i += 2
            elif a[i] == '--show':
                show.append(a[i+1])
                i += 2
            else:
                i += 1
        patch(src, dst, feats, hide, show, '--write' in a)


if __name__ == '__main__':
    main()
