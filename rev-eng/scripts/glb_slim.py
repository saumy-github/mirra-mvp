"""glb_slim.py - offline stdlib-only glTF 2.0 / GLB rewriter that shrinks CLO avatar exports.

Input : binary GLB, or text glTF (CLO "result_avatar.glb") with external .bin and external image files.
Output: always a single binary .glb (images embedded as bufferViews).

Usage: python -I glb_slim.py IN [-o OUT.glb] [--drop-mesh Hair,shoes_r,shoes_l] [--weld] [--u16-indices]
                              [--weights-u8] [--joints-u8] [--recompress-images] [--report] [--no-validate]
Without -o only the analysis/validation report of IN is printed.
--recompress-images: NOT possible with stdlib (no JPEG/PNG re-encoder); only prints image sizes.
Validity is checked ONLY by this script's own validator (no external glTF validator is used).
"""
import sys, os, json, struct, base64, copy, argparse

CT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}


# ---------------------------------------------------------------- loading
def load(path):
    raw = open(path, 'rb').read()
    base = os.path.dirname(os.path.abspath(path))
    ext_sizes = 0
    if raw[:4] == b'glTF':
        off, j, binc = 12, None, None
        while off < len(raw):
            ln, ty = struct.unpack_from('<I4s', raw, off)
            body = raw[off + 8:off + 8 + ln]
            if ty == b'JSON': j = json.loads(body.decode('utf-8'))
            elif ty.startswith(b'BIN') and binc is None: binc = body
            off += 8 + ln
        kind = 'GLB'
    else:
        j = json.loads(raw.decode('utf-8')); binc = None; kind = 'glTF-text'
    bufs = []
    for i, b in enumerate(j.get('buffers', [])):
        u = b.get('uri')
        if u is None:
            bufs.append(binc or b'')
        elif u.startswith('data:'):
            bufs.append(base64.b64decode(u.split(',', 1)[1]))
        else:
            d = open(os.path.join(base, u), 'rb').read(); ext_sizes += len(d); bufs.append(d)
    images = []   # bytes per image (resolved) , mime
    for im in j.get('images', []):
        if 'uri' in im:
            u = im['uri']
            if u.startswith('data:'):
                d = base64.b64decode(u.split(',', 1)[1]); mime = u[5:].split(';')[0]
            else:
                p = os.path.join(base, u.replace('%20', ' '))
                d = open(p, 'rb').read(); ext_sizes += len(d)
                mime = im.get('mimeType') or MIME.get(os.path.splitext(u)[1].lower(), 'application/octet-stream')
            images.append((d, mime))
        else:
            bv = j['bufferViews'][im['bufferView']]
            o = bv.get('byteOffset', 0)
            images.append((bufs[bv['buffer']][o:o + bv['byteLength']], im.get('mimeType', 'image/png')))
    return dict(j=j, bufs=bufs, images=images, kind=kind, size=len(raw), ext_size=ext_sizes, path=path)


def acc_raw(m, ai):
    """Tightly packed element bytes of accessor ai (de-strided)."""
    j = m['j']; a = j['accessors'][ai]
    if 'sparse' in a: raise ValueError('sparse accessor %d unsupported' % ai)
    esz = CT[a['componentType']][1] * NC[a['type']]
    n = a['count']
    if 'bufferView' not in a: return bytes(n * esz)
    bv = j['bufferViews'][a['bufferView']]
    buf = m['bufs'][bv['buffer']]
    o = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    st = bv.get('byteStride') or esz
    if st == esz: return bytes(buf[o:o + n * esz])
    return b''.join(buf[o + i * st:o + i * st + esz] for i in range(n))


def unpack(fmt_c, data):
    return list(struct.unpack('<%d%s' % (len(data) // CT_size(fmt_c), fmt_c), data))


def CT_size(c): return struct.calcsize('<' + c)


# ---------------------------------------------------------------- stats / validation
def mesh_stats(m):
    j = m['j']; acc = j.get('accessors', []); res = []
    for mi, me in enumerate(j.get('meshes', [])):
        pos = set(); tris = 0
        for p in me['primitives']:
            pos.add(p['attributes']['POSITION'])
            if 'indices' in p:
                if p.get('mode', 4) == 4: tris += acc[p['indices']]['count'] // 3
            elif p.get('mode', 4) == 4:
                tris += acc[p['attributes']['POSITION']]['count'] // 3
        res.append((me.get('name', 'mesh%d' % mi), sum(acc[a]['count'] for a in pos), tris, len(me['primitives'])))
    return res


def validate(m):
    j = m['j']; errs = []; warns = []
    acc = j.get('accessors', []); bvs = j.get('bufferViews', [])
    for i, bv in enumerate(bvs):
        if bv['buffer'] >= len(m['bufs']): errs.append('bufferView %d: buffer missing' % i); continue
        o = bv.get('byteOffset', 0)
        if o + bv['byteLength'] > len(m['bufs'][bv['buffer']]): errs.append('bufferView %d exceeds buffer' % i)
        if o % 4: errs.append('bufferView %d offset %d not 4-aligned' % (i, o))
    for i, a in enumerate(acc):
        esz = CT[a['componentType']][1] * NC[a['type']]
        if 'bufferView' in a:
            bv = bvs[a['bufferView']]; st = bv.get('byteStride') or esz
            end = a.get('byteOffset', 0) + st * (a['count'] - 1) + esz if a['count'] else 0
            if end > bv['byteLength']: errs.append('accessor %d exceeds bufferView %d' % (i, a['bufferView']))
            if (bv.get('byteOffset', 0) + a.get('byteOffset', 0)) % CT[a['componentType']][1]:
                errs.append('accessor %d misaligned for component size' % i)
            if bv.get('byteStride') and bv['byteStride'] % 4 and bv.get('target') == 34962:
                errs.append('bufferView %d byteStride not multiple of 4' % a['bufferView'])
    nnodes = len(j.get('nodes', []))
    for si, s in enumerate(j.get('skins', [])):
        for jn in s['joints']:
            if not (0 <= jn < nnodes): errs.append('skin %d joint node %d missing' % (si, jn))
    skin_len = {}
    for ni, n in enumerate(j.get('nodes', [])):
        if 'mesh' in n and 'skin' in n: skin_len[n['mesh']] = len(j['skins'][n['skin']]['joints'])
        for c in n.get('children', []):
            if not (0 <= c < nnodes): errs.append('node %d child %d missing' % (ni, c))
        if 'mesh' in n and n['mesh'] >= len(j.get('meshes', [])): errs.append('node %d mesh missing' % ni)
    wsum_bad = 0; wsum_n = 0; wmax = 0.0
    for mi, me in enumerate(j.get('meshes', [])):
        for pi, p in enumerate(me['primitives']):
            at = p['attributes']; n = acc[at['POSITION']]['count']
            for k, ai in at.items():
                if acc[ai]['count'] != n: errs.append('mesh %d prim %d %s count %d != POSITION %d' % (mi, pi, k, acc[ai]['count'], n))
                esz = CT[acc[ai]['componentType']][1] * NC[acc[ai]['type']]
                if esz % 4 and not acc[ai].get('bufferView') is None and not bvs[acc[ai]['bufferView']].get('byteStride'):
                    warns.append('attr %s elem %d B not 4-aligned w/o stride' % (k, esz))
            if 'indices' in p:
                a = acc[p['indices']]; c = CT[a['componentType']][0]
                if c not in 'BHI': errs.append('mesh %d prim %d bad index type' % (mi, pi)); continue
                ix = unpack(c, acc_raw(m, p['indices']))
                if ix and max(ix) >= n: errs.append('mesh %d prim %d index %d >= vertices %d' % (mi, pi, max(ix), n))
                if p.get('mode', 4) == 4 and len(ix) % 3: errs.append('mesh %d prim %d index count %% 3' % (mi, pi))
            sets = sorted(k for k in at if k.startswith('JOINTS_'))
            for k in sets:
                a = acc[at[k]]; mx = max(unpack(CT[a['componentType']][0], acc_raw(m, at[k])) or [0])
                if mi in skin_len and mx >= skin_len[mi]: errs.append('mesh %d %s joint index %d >= skin joints %d' % (mi, k, mx, skin_len[mi]))
            wk = sorted(k for k in at if k.startswith('WEIGHTS_'))
            if wk:
                if len(wk) != len(sets): errs.append('mesh %d JOINTS/WEIGHTS set count differ' % mi)
                cols = []
                for k in wk:
                    a = acc[at[k]]; c, sz = CT[a['componentType']]
                    v = unpack(c, acc_raw(m, at[k]))
                    if c != 'f': v = [x / (2 ** (8 * sz) - 1) for x in v]
                    cols.append(v)
                for vi in range(n):
                    s = sum(sum(col[vi * 4:vi * 4 + 4]) for col in cols)
                    wsum_n += 1
                    d = abs(s - 1.0); wmax = max(wmax, d)
                    if d > 1e-3: wsum_bad += 1
    if wsum_bad: errs.append('%d of %d vertices have weight sum off by >1e-3 (max dev %.5f)' % (wsum_bad, wsum_n, wmax))
    return errs, sorted(set(warns)), wmax


# ---------------------------------------------------------------- output builder
class Out:
    def __init__(self):
        self.bin = bytearray(); self.views = []; self.accs = []

    def view(self, data, target=None):
        while len(self.bin) % 4: self.bin.append(0)
        v = {'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data)}
        if target: v['target'] = target
        self.bin += data; self.views.append(v); return len(self.views) - 1

    def acc(self, data, ct, ty, count, norm=False, target=None, mm=None):
        a = {'bufferView': self.view(data, target), 'componentType': ct, 'count': count, 'type': ty}
        if norm: a['normalized'] = True
        if mm: a.update(mm)
        self.accs.append(a); return len(self.accs) - 1


def quant_weights(vals, sz):
    """vals: list of floats (flat, 4 per vertex) -> bytes of u8 with exact per-vertex sum 255."""
    out = bytearray(len(vals))
    for i in range(0, len(vals), 4):
        w = vals[i:i + 4]; s = sum(w)
        if s <= 0: continue
        sc = [x / s * 255.0 for x in w]; fl = [int(x) for x in sc]
        rem = 255 - sum(fl)
        for k in sorted(range(4), key=lambda k: sc[k] - fl[k], reverse=True)[:rem]: fl[k] += 1
        out[i:i + 4] = bytes(fl)
    return bytes(out)


# ---------------------------------------------------------------- drop meshes
def drop_meshes(j, names):
    meshes = j.get('meshes', [])
    drop = {i for i, me in enumerate(meshes) if any(me.get('name', '') == nm or me.get('name', '').startswith(nm + '_') for nm in names)}
    missing = {nm for nm in names if not any(meshes[i].get('name', '') == nm or meshes[i].get('name', '').startswith(nm + '_') for i in drop)}
    keepm = [i for i in range(len(meshes)) if i not in drop]
    mmap = {o: n for n, o in enumerate(keepm)}
    j['meshes'] = [meshes[i] for i in keepm]
    nodes = j.get('nodes', [])
    joints = {x for s in j.get('skins', []) for x in s['joints']}
    rem = set()
    for i, n in enumerate(nodes):
        if n.get('mesh') in drop:
            del n['mesh']; n.pop('skin', None)
            if not n.get('children') and i not in joints and not (set(n) - {'name', 'translation', 'rotation', 'scale', 'matrix'}):
                rem.add(i)
    keepn = [i for i in range(len(nodes)) if i not in rem]; nmap = {o: n for n, o in enumerate(keepn)}
    new_nodes = []
    for i in keepn:
        n = nodes[i]
        if 'mesh' in n: n['mesh'] = mmap[n['mesh']]
        if 'children' in n:
            n['children'] = [nmap[c] for c in n['children'] if c in nmap]
            if not n['children']: del n['children']
        new_nodes.append(n)
    j['nodes'] = new_nodes
    for sc in j.get('scenes', []): sc['nodes'] = [nmap[c] for c in sc.get('nodes', []) if c in nmap]
    used_skins = sorted({n['skin'] for n in new_nodes if 'skin' in n}); smap = {o: n for n, o in enumerate(used_skins)}
    skins = j.get('skins', [])
    j['skins'] = [skins[i] for i in used_skins]
    for s in j['skins']:
        s['joints'] = [nmap[x] for x in s['joints']]
        if 'skeleton' in s: s['skeleton'] = nmap.get(s['skeleton'], s['joints'][0] if s['joints'] else 0)
    for n in new_nodes:
        if 'skin' in n: n['skin'] = smap[n['skin']]
    if not j['skins']: j.pop('skins')
    for an in j.get('animations', []):
        ch = [c for c in an['channels'] if c['target'].get('node') in nmap or 'node' not in c['target']]
        for c in ch:
            if 'node' in c['target']: c['target']['node'] = nmap[c['target']['node']]
        us = sorted({c['sampler'] for c in ch}); sm = {o: n for n, o in enumerate(us)}
        an['samplers'] = [an['samplers'][i] for i in us]
        for c in ch: c['sampler'] = sm[c['sampler']]
        an['channels'] = ch
    # GC materials -> textures -> samplers/images
    mats = j.get('materials', [])
    um = sorted({p['material'] for me in j['meshes'] for p in me['primitives'] if 'material' in p}); mm = {o: n for n, o in enumerate(um)}
    j['materials'] = [mats[i] for i in um]
    for me in j['meshes']:
        for p in me['primitives']:
            if 'material' in p: p['material'] = mm[p['material']]
    tex_refs = []
    def walk(o, key=''):
        if isinstance(o, dict):
            if 'index' in o and 'texture' in key.lower(): tex_refs.append(o)
            for k, v in o.items(): walk(v, k)
        elif isinstance(o, list):
            for v in o: walk(v, key)
    for mt in j['materials']: walk(mt)
    texs = j.get('textures', [])
    ut = sorted({r['index'] for r in tex_refs}); tm = {o: n for n, o in enumerate(ut)}
    for r in tex_refs: r['index'] = tm[r['index']]
    j['textures'] = [texs[i] for i in ut]
    return drop, missing, j


def gc_images(j, images):
    """Remap texture.source / sampler; return new images list (bytes, mime)."""
    ims = j.get('images', []); sps = j.get('samplers', [])
    ui = sorted({t['source'] for t in j['textures'] if 'source' in t}); im = {o: n for n, o in enumerate(ui)}
    us = sorted({t['sampler'] for t in j['textures'] if 'sampler' in t}); sm = {o: n for n, o in enumerate(us)}
    for t in j['textures']:
        if 'source' in t: t['source'] = im[t['source']]
        if 'sampler' in t: t['sampler'] = sm[t['sampler']]
    j['images'] = [ims[i] for i in ui]
    if sps: j['samplers'] = [sps[i] for i in us]
    for k in ('textures', 'images', 'samplers', 'materials'):
        if k in j and not j[k]: del j[k]
    return [images[i] for i in ui]


# ---------------------------------------------------------------- rewrite
def rewrite(m, o, log):
    j = copy.deepcopy(m['j']); images = m['images']
    if o.drop_mesh:
        _, missing, j = drop_meshes(j, set(o.drop_mesh))
        if missing: log('WARN: mesh names not found: %s' % sorted(missing))
        if 'textures' in j or m['j'].get('textures'):
            j.setdefault('textures', []); images = gc_images(j, images)
    m2 = dict(m, j=m['j'])   # accessor reads use the ORIGINAL accessor tables
    A = m['j']['accessors']; out = Out()
    memo_copy = {}

    def copy_acc(ai, target=None):
        if ai in memo_copy: return memo_copy[ai]
        a = A[ai]; mm = {k: a[k] for k in ('min', 'max') if k in a}
        r = out.acc(acc_raw(m2, ai), a['componentType'], a['type'], a['count'], a.get('normalized', False), target, mm)
        memo_copy[ai] = r; return r

    groups = {}
    for me in j.get('meshes', []):
        for p in me['primitives']:
            groups.setdefault(tuple(sorted(p['attributes'].items())), []).append(p)
    for key, prims in groups.items():
        attrs = dict(key); n = A[attrs['POSITION']]['count']
        data = {}
        for k, ai in attrs.items():
            a = A[ai]; data[k] = [acc_raw(m2, ai), a['componentType'], a['type'], a.get('normalized', False), A[ai]]
        octs = {}
        idx = {}   # prim id -> list of ints or None
        for p in prims:
            if 'indices' in p:
                c = CT[A[p['indices']]['componentType']][0]
                idx[id(p)] = unpack(c, acc_raw(m2, p['indices']))
                octs[id(p)] = A[p['indices']]['componentType']
            else:
                idx[id(p)] = None
        has_targets = any('targets' in p for p in prims)
        if o.weld and not has_targets:
            es = {k: CT[d[1]][1] * NC[d[2]] for k, d in data.items()}
            cols = [[d[0][i * es[k]:(i + 1) * es[k]] for i in range(n)] for k, d in data.items()]
            seen = {}; remap = [0] * n; order = []
            for i, row in enumerate(zip(*cols)):
                t = seen.get(row)
                if t is None: t = seen[row] = len(order); order.append(i)
                remap[i] = t
            if len(order) < n:
                for k, d in data.items(): d[0] = b''.join(cols[list(data).index(k)][i] for i in order)
                for p in prims:
                    ix = idx[id(p)] if idx[id(p)] is not None else list(range(n))
                    idx[id(p)] = [remap[x] for x in ix]
                n = len(order)
            elif any(idx[id(p)] is None for p in prims):
                for p in prims:
                    if idx[id(p)] is None: idx[id(p)] = list(range(n))
        # quantise
        new_attr = {}
        for k, d in data.items():
            raw, ct, ty, norm, oa = d; mm = {}
            if k.startswith('WEIGHTS_') and o.weights_u8 and ct != 5121:
                c, sz = CT[ct]; v = unpack(c, raw)
                if c != 'f': v = [x / (2 ** (8 * sz) - 1) for x in v]
                raw = quant_weights(v, sz); ct = 5121; norm = True
            elif k.startswith('JOINTS_') and o.joints_u8 and ct == 5123:
                v = unpack('H', raw)
                if (max(v) if v else 0) < 256: raw = bytes(v); ct = 5121
            elif k == 'POSITION' and ct == 5126:
                v = unpack('f', raw)
                mm = {'min': [min(v[i::3]) for i in range(3)], 'max': [max(v[i::3]) for i in range(3)]} if v else {}
            else:
                mm = {kk: oa[kk] for kk in ('min', 'max') if kk in oa}
            new_attr[k] = out.acc(raw, ct, ty, n, norm, 34962, mm)
        icache = {}
        for p in prims:
            ix = idx[id(p)]
            p['attributes'] = dict(new_attr)
            if 'targets' in p:
                p['targets'] = [{k: copy_acc(v, 34962) for k, v in t.items()} for t in p['targets']]
            if ix is None: continue
            if o.u16_indices and n < 65535: ct = 5123
            else: ct = max(octs.get(id(p), 5123), 5125 if (n >= 65535 or (ix and max(ix) > 65535)) else 0)
            c = {5121: 'B', 5123: 'H', 5125: 'I'}[ct]
            p['indices'] = out.acc(struct.pack('<%d%s' % (len(ix), c), *ix), ct, 'SCALAR', len(ix), False, 34963)
    # remaining accessors: skins, animations
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s: s['inverseBindMatrices'] = copy_acc(s['inverseBindMatrices'])
    for an in j.get('animations', []):
        for sm in an['samplers']:
            sm['input'] = copy_acc(sm['input']); sm['output'] = copy_acc(sm['output'])
    # images embedded
    for k, im in enumerate(j.get('images', [])):
        d, mime = images[k]
        im.pop('uri', None); im['bufferView'] = out.view(d); im['mimeType'] = mime
    j['accessors'] = out.accs; j['bufferViews'] = out.views
    while len(out.bin) % 4: out.bin.append(0)
    j['buffers'] = [{'byteLength': len(out.bin)}]
    if not j['accessors']: del j['accessors']
    return j, bytes(out.bin), images


def write_glb(path, j, binb):
    js = json.dumps(j, separators=(',', ':')).encode('utf-8')
    js += b' ' * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(binb)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js)
        f.write(struct.pack('<I4s', len(binb), b'BIN\0')); f.write(binb)
    return total


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('-o', '--output')
    ap.add_argument('--drop-mesh', type=lambda s: [x for x in s.split(',') if x])
    for f in ('weld', 'u16-indices', 'weights-u8', 'joints-u8', 'recompress-images', 'report', 'no-validate'):
        ap.add_argument('--' + f, action='store_true')
    o = ap.parse_args()
    m = load(o.input)
    print('INPUT %s [%s] file=%d B%s' % (o.input, m['kind'], m['size'], (' + external %d B (bin+images)' % m['ext_size']) if m['ext_size'] else ''))
    isz = [(len(d), mime) for d, mime in m['images']]
    if o.recompress_images or o.report:
        print('images: %d, total %d B %s' % (len(isz), sum(s for s, _ in isz), isz if len(isz) < 30 else ''))
        if o.recompress_images: print('--recompress-images: SKIPPED (stdlib has no JPEG/PNG encoder); sizes reported only')
    if o.report:
        print('before per-mesh (name, distinct verts, tris, prims):')
        for s in mesh_stats(m): print('  %-16s v=%-8d t=%-8d p=%d' % s)
        if not o.no_validate:
            e, w, wm = validate(m); print('validate(input): %d errors, %d warnings, max weight-sum dev %.6f' % (len(e), len(w), wm))
            for x in e[:20] + w[:5]: print('   ', x)
    if o.output:
        j, binb, _ = rewrite(m, o, print)
        os.makedirs(os.path.dirname(os.path.abspath(o.output)), exist_ok=True)
        tot = write_glb(o.output, j, binb)
        print('OUTPUT %s %d B  (bin %d B, json %d B)' % (o.output, tot, len(binb), len(json.dumps(j, separators=(',', ':')))))
        if o.report:
            m2 = load(o.output)
            print('after per-mesh:')
            for s in mesh_stats(m2): print('  %-16s v=%-8d t=%-8d p=%d' % s)
            if not o.no_validate:
                e, w, wm = validate(m2); print('validate(output): %d errors, %d warnings, max weight-sum dev %.6f' % (len(e), len(w), wm))
                for x in e[:20] + w[:5]: print('   ', x)
                # geometry equivalence: weld must keep triangle count and bounds
            print('reduction vs input file: %.1f%%' % (100.0 * (1 - tot / m['size'])))
            print('reduction vs input incl. external bin+images: %.1f%%' % (100.0 * (1 - tot / (m['size'] + m['ext_size']))))


if __name__ == '__main__':
    main()
