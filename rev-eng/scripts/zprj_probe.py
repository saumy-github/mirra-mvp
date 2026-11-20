"""zprj_probe.py - read-only inspector for CLO project containers (.zprj, nested .zpac/.pos/.vmp/...).
Stdlib only. Run with:  python -I zprj_probe.py <info|tree|diff> ...

  info FILE.zprj                 header + member table (nested containers expanded) + garment summary
  tree FILE.zprj MEMBER [--path P] [--depth N]
        MEMBER addresses nested members with '!' e.g.  simulation.zpac!simulation.pac
        P is a '/' path into the typed stream (digits index lists), e.g. mapPatternEditor/mapPatternList/listPattern/0
  diff A.zprj B.zprj [--max N]   member-level diff (sizes/hashes) + typed-leaf diff for stream members
                                 (the big *_0.avt is compared by hash only; use avs_grammar.py dandiff for .dan)

Container knowledge (see findings/23_zprj_garment_structure.md):
  CLO container := 0x00 16B magic ' ZPRJ       CLO ' (4-char type, space padded to 12, then 'CLO ')
                   0x10 u32 version  0x14 u32 ?  0x18 u32 png_off  0x1C u32 png_len
                   0x20 u32 body_off 0x24 u32 body_len  ... ; body is a ZIP ('PK') or a raw typed stream (.pos/.vmp inner)
  typed stream  := avs_grammar block grammar (also 0x05 u32, 0x07 f64, 0x0d m3, 0x15 arr, 0x17 ? kept as Raw)
"""
import sys, os, io, struct, zipfile, hashlib, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs_grammar as g  # noqa: E402

MAGIC_TAIL = b'CLO '


def clo_header(b):
    """Return dict for a CLO container header or None."""
    if len(b) < 0x28 or b[12:16] != MAGIC_TAIL:
        return None
    kind = b[:12].decode('latin1').strip()
    ver, u14, png_off, png_len, body_off, body_len = struct.unpack_from('<6I', b, 0x10)
    ms = struct.unpack_from('<Q', b, 0x28)[0]
    return dict(kind=kind, version=ver, u14=u14, png_off=png_off, png_len=png_len, body_off=body_off,
                body_len=body_len, ts_ms=ms)


def clo_body(b):
    h = clo_header(b)
    if h:
        if b[h['body_off']:h['body_off'] + 4] == b'PK\x03\x04':
            return h, b[h['body_off']:h['body_off'] + h['body_len'] if h['body_len'] else None], 'zip'
        return h, b[h['body_off']:h['body_off'] + h['body_len']], 'stream'
    return None, b, None


def classify(name, b):
    if b[:4] == b'\x89PNG': return 'png'
    if b[:2] == b'\xff\xd8': return 'jpeg'
    if b[:10] == b'#?RADIANCE': return 'hdr'
    if b[:1] in b'{[' : return 'json'
    if b[:5] == b'<?xml' or b[:1] == b'<': return 'xml'
    if b[:8] == b'Version:': return 'text(|^^|)'
    h = clo_header(b)
    if h:
        return 'CLO-%s(%s)' % (h['kind'], clo_body(b)[2])
    try:
        g.parse(b)
        return 'typed-stream'
    except Exception:
        return 'binary'


def open_zip(b):
    h, body, kind = clo_body(b)
    if kind == 'zip' or b[:4] == b'PK\x03\x04':
        return zipfile.ZipFile(io.BytesIO(body if kind else b))
    zs = b.find(b'PK\x03\x04')
    return zipfile.ZipFile(io.BytesIO(b[zs:])) if zs >= 0 else None


def read_member(path, member):
    """member 'a!b!c' : a is a member of the outer zprj, b a member of a's inner zip, ... Returns bytes."""
    data = open(path, 'rb').read()
    parts = member.split('!')
    cur = data
    for k, p in enumerate(parts):
        z = open_zip(cur)
        if z is None:
            raise KeyError('not a container before %r' % p)
        cur = z.read(p)
    return cur


def stream_of(b):
    """bytes of a typed stream inside raw/CLO-wrapped data."""
    h, body, kind = clo_body(b)
    return body if kind == 'stream' else b


def walk_members(data, prefix='', depth=0, out=None):
    out = [] if out is None else out
    z = open_zip(data)
    if z is None: return out
    for zi in z.infolist():
        d = z.read(zi)
        fmt = classify(zi.filename, d)
        out.append((prefix + zi.filename, zi.file_size, zi.compress_size, fmt, hashlib.sha1(d).hexdigest()[:10]))
        if fmt.startswith('CLO-') and fmt.endswith('(zip)') and depth < 2 and not zi.filename.endswith('.avt'):
            walk_members(d, prefix + zi.filename + '!', depth + 1, out)
    return out


# ---------------------------------------------------------------- typed-stream flatten / show
def fmt_raw(v):
    b = v.b
    t = v.t
    try:
        if t == 5 and len(b) == 4: return 'u32 %d' % struct.unpack('<I', b)[0]
        if t == 7 and len(b) == 8: return 'f64 %g' % struct.unpack('<d', b)[0]
        if t in (0x0a, 0x0b, 0x0c, 0x0d, 0x0e) and len(b) % 4 == 0:
            return 'f32x%d %s' % (len(b) // 4, [round(x, 4) for x in struct.unpack('<%df' % (len(b) // 4), b)])
        if t == 0x15 and len(b) >= 5:
            n, et = struct.unpack_from('<I', b)[0], b[4]
            if et in (4, 5, 6) and len(b) == 5 + 4 * n:
                vals = struct.unpack_from('<%d%s' % (n, 'iIf'[et - 4]), b, 5)
                return 'arr<%s>[%d] %s%s' % ('i32 u32 f32'.split()[et - 4], n, list(vals[:12]), '...' if n > 12 else '')
    except Exception:
        pass
    return 'raw0x%x %dB %s' % (t, len(b), b[:16].hex())


def fmt_leaf(v):
    if isinstance(v, g.Raw): return fmt_raw(v)
    if isinstance(v, bool): return str(v)
    if isinstance(v, int): return str(v)
    if isinstance(v, tuple) and v[0] == 'f': return '%.6g' % v[1]
    if isinstance(v, tuple) and v[0] == 's':
        b = v[1]
        if len(b) > 64: return 'bytes[%d] sha1=%s' % (len(b), hashlib.sha1(b).hexdigest()[:10])
        return repr(b.decode('latin1'))
    return repr(v)


def nav(fields, path):
    cur = fields
    for p in [x for x in path.split('/') if x]:
        if isinstance(cur, tuple) and cur[0] == 'L':
            cur = cur[2][int(p)]
        elif isinstance(cur, list):
            for n, t, v in cur:
                if n == p: cur = v; break
            else: raise KeyError(p)
        else: raise KeyError(p)
    return cur


def show(v, name, ind, depth, out):
    pad = ' ' * ind
    if isinstance(v, list):
        out.append('%s%s {map %d}' % (pad, name, len(v)))
        if depth > 0:
            for n, t, x in v: show(x, n, ind + 2, depth - 1, out)
    elif isinstance(v, tuple) and v[0] == 'L':
        out.append('%s%s [list %d x type %s]' % (pad, name, len(v[2]), hex(v[1]) if v[1] else '-'))
        if depth > 0:
            for k, x in enumerate(v[2]): show(x, '[%d]' % k, ind + 2, depth - 1, out)
    else:
        out.append('%s%s = %s' % (pad, name, fmt_leaf(v)))


def flatten(v, path, out):
    if isinstance(v, list):
        for n, t, x in v: flatten(x, path + '/' + n, out)
    elif isinstance(v, tuple) and v[0] == 'L':
        for k, x in enumerate(v[2]): flatten(x, '%s[%d]' % (path, k), out)
        out[path + '#len'] = str(len(v[2]))
    else:
        out[path] = fmt_leaf(v)


# ---------------------------------------------------------------- garment summary
def u32(v): return struct.unpack('<I', v.b)[0] if isinstance(v, g.Raw) and len(v.b) == 4 else v
def S(v): return v[1].decode('latin1') if isinstance(v, tuple) and v[0] == 's' else v


def get(f, k):
    try: return nav(f, k)
    except Exception: return None


def garment_summary(pac, pos=None):
    t = g.parse(pac)
    L = []
    pl = nav(t, 'mapPatternEditor/mapPatternList')
    pats = nav(pl, 'listPattern')[2]
    L.append('patterns: %d  seams: %d  fabrics: %d' % (len(pats), len(nav(t, 'mapPatternEditor/mapSeamLinePairGroup/listSeamLinePairGroup')[2]), len(nav(t, 'listFabric')[2])))
    for i, p in enumerate(pats):
        sh2 = nav(p, 'mapShape2D'); mesh = nav(p, 'mapFabricShape2D/mapMesh2D')
        pts = [struct.unpack('<2f', nav(q, 'v2Position').b) for q in nav(sh2, 'listPoint')[2]]
        xs = [a for a, b in pts]; ys = [b for a, b in pts]
        p3 = nav(p, 'baPosition3D')[1]
        L.append('  [%d] sdk_name=%s arrange=%s/%s uuid=%s pts=%d bbox2D_mm=%.1fx%.1f mesh=%dv/%dt fabricIdx=%d edgeLen=%g 3Dverts=%d' % (
            i, S(nav(p, 'mapElement/qsName')), S(nav(p, 'mapArrange/qsName')), S(nav(p, 'mapArrange/qsPanName')),
            S(nav(p, 'qsUuid'))[:8], len(pts), max(xs) - min(xs), max(ys) - min(ys), u32(nav(mesh, 'uiVertexCount2D')),
            u32(nav(mesh, 'uiTriangleCount')), u32(nav(p, 'mapFabricShape2D/iFabricIndex')), nav(p, 'fEdgeLength')[1], len(p3) // 12))
    for i, it in enumerate(nav(t, 'mapPatternEditor/mapSeamLinePairGroup/listSeamLinePairGroup')[2]):
        a = nav(it, 'listParamLineGroup0')[2][0]; b = nav(it, 'listParamLineGroup1')[2][0]
        d = lambda x: 'pat%d.line%d[%.0f->%.0f]' % (u32(nav(x, 'uiSelfIndex')), u32(nav(x, 'uiStartIndex')), nav(x, 'fRatioStart')[1], nav(x, 'fRatioEnd')[1])
        L.append('  seam[%d] %s : %s <-> %s' % (i, S(nav(it, 'mapElement/qsName')), d(a), d(b)))
    for fi, f in enumerate(nav(t, 'listFabric')[2]):
        fm = nav(nav(nav(nav(f, 'mapColorwayInfo'), 'listColorwayInfo')[2][0], 'listMaterial2D')[2][0], 'listFaceMaterial')[2][0]
        bc = struct.unpack('<3f', nav(fm, 'v3BaseColor').b)
        tex = [S(nav(x, 'qsFileName')) for x in nav(fm, 'listTexture')[2]]
        ph = nav(f, 'mapPhysical')
        L.append('  fabric[%d] %s uiID=%d baseColor(rgb/255)=%s hex=%s rough/gloss=%g metal=%s texture=%s' % (
            fi, S(nav(f, 'qsName')), u32(nav(f, 'uiID')), [round(c, 4) for c in bc], ''.join('%02X' % round(c * 255) for c in bc),
            nav(fm, 'fGlossiness')[1], nav(fm, 'bMetal'), tex))
        L.append('    physical: name=%s Su=%g Sv=%g Bu=%g density=%g friction=%g thickness=%g' % (
            S(nav(ph, 'qsPhysicalPropertyName')), nav(ph, 'fSuK')[1], nav(ph, 'fSvK')[1], nav(ph, 'fBuK')[1], nav(ph, 'fDensity')[1], nav(ph, 'fFriction')[1], nav(ph, 'fThickness')[1]))
    cw = nav(t, 'mapColorWay/listColorway')[2]
    L.append('  colorways: %s' % [(S(nav(c, 'qsName')), S(nav(c, 'qsUuid'))) for c in cw])
    smp = nav(t, 'mapSMP')
    L.append('  sim(mapSMP): gravity=%g timestep=%g subSteps=%d threads=%d pinching.density=%g' % (
        nav(smp, 'mapDeforMarvelProperty/fGravity_y')[1], nav(smp, 'fEntireTimeStep')[1], u32(nav(smp, 'uiSubStepCount')), u32(nav(smp, 'uiThreadCount')), nav(smp, 'mapPinchingOverride/fDensity')[1]))
    av = nav(t, 'mapAvatar')
    fv = nav(av, 'mapResizingAvatar/listFeatureValues')[2]
    L.append('  avatar link: mapAvatar.qsAvatarID=%s mapPose.qsAvatarID=%s featureValues[%d] h=%.2f chest=%.2f waist=%.2f hip=%.2f' % (
        S(nav(av, 'qsAvatarID')), S(nav(t, 'mapPatternEditor/mapPose/qsAvatarID')), len(fv), fv[0][1], fv[2][1], fv[6][1], fv[8][1]))
    return L


def cmd_info(path):
    raw = open(path, 'rb').read()
    h = clo_header(raw)
    print('FILE', path, len(raw), 'B')
    print('header', h, 'ts=', __import__('datetime').datetime.fromtimestamp(h['ts_ms'] / 1000, __import__('datetime').timezone.utc).isoformat() if h else '')
    print('id string @0x40:', raw[0x44:0x44 + struct.unpack_from('<I', raw, 0x40)[0]])
    rows = walk_members(clo_body(raw)[1] if h else raw)
    print('%-52s %10s %10s  %-22s %s' % ('member', 'size', 'zip', 'format', 'sha1[:10]'))
    for n, s, c, f, hs in rows: print('%-52s %10d %10d  %-22s %s' % (n, s, c, f, hs))
    pac = [n for n, *_ in rows if n.endswith('.pac')]
    if pac:
        pos = [n for n, *_ in rows if n.endswith('.pos')]
        print('\nGARMENT SUMMARY (%s)' % pac[0])
        print('\n'.join(garment_summary(stream_of(read_member(path, pac[0])))))
    else:
        print('\n(no .zpac/.pac member: avatar-only project)')
    osw = [n for n, *_ in rows if n.endswith('.osw')]
    if osw:
        t = g.parse(read_member(path, osw[0]))
        print('\nosw links: avatars=%s cloth=%s counts avatar/cloth/prop=%s' % (
            [S(x) for x in nav(t, 'listAvatarFilePath')[2]], S(get(t, 'qsClothFilePath')),
            (u32(get(t, 'uiAvatarCount')), u32(get(t, 'uiClothLink')), u32(get(t, 'uiScenePropCount')))))


def cmd_tree(path, member, tpath='', depth=2):
    b = read_member(path, member)
    t = g.parse(stream_of(b))
    v = nav(t, tpath) if tpath else t
    out = []
    if isinstance(v, list):
        for n, ty, x in v: show(x, n, 0, depth, out)
    else:
        show(v, tpath or '.', 0, depth, out)
    print('\n'.join(out))


def cmd_diff(a, b, mx=60):
    ra, rb = open(a, 'rb').read(), open(b, 'rb').read()
    ma = {n: (s, f, h) for n, s, c, f, h in walk_members(clo_body(ra)[1])}
    mb = {n: (s, f, h) for n, s, c, f, h in walk_members(clo_body(rb)[1])}
    for n in sorted(set(ma) | set(mb)):
        if n not in ma or n not in mb: print('ONLY_IN_%s %s' % ('A' if n in ma else 'B', n)); continue
        if ma[n][2] != mb[n][2]: print('DIFF %-50s size %d -> %d  %s' % (n, ma[n][0], mb[n][0], ma[n][1]))
    for n in sorted(set(ma) & set(mb)):
        if ma[n][2] == mb[n][2] or ma[n][1] not in ('typed-stream', 'CLO-POS(stream)', 'CLO-VMP(zip)', 'CLO-ZPAC(zip)') or n.endswith('.avt'): continue
        fa, fb = {}, {}
        try:
            for src, dst in ((a, fa), (b, fb)):
                parts = n.split('!')
                if ma[n][1].startswith('CLO-ZPAC'):
                    continue
                flatten(g.parse(stream_of(read_member(src, n))), '', dst)
        except Exception as e:
            print('  (cannot flatten %s: %s)' % (n, e)); continue
        ks = [k for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]
        print('  stream %s: %d differing leaves' % (n, len(ks)))
        for k in ks[:mx]: print('    %s: %s -> %s' % (k, fa.get(k), fb.get(k)))


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    if a[0] == 'info': cmd_info(a[1])
    elif a[0] == 'tree':
        tp, dp = '', 2
        if '--path' in a: tp = a[a.index('--path') + 1]
        if '--depth' in a: dp = int(a[a.index('--depth') + 1])
        cmd_tree(a[1], a[2], tp, dp)
    elif a[0] == 'diff':
        cmd_diff(a[1], a[2], int(a[a.index('--max') + 1]) if '--max' in a else 60)
    else: print(__doc__)


if __name__ == '__main__':
    main()
