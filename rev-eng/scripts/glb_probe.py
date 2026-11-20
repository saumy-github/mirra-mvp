"""glb_probe.py - stdlib probe for glTF files (true binary GLB or text glTF-with-.bin saved as .glb).
Usage: python -I glb_probe.py info FILE | summary FILE... (one-line TSV) | diff A B
"""
import sys, json, struct, hashlib, os

def load(p):
    raw = open(p, 'rb').read()
    if raw[:4] == b'glTF':
        ver, total = struct.unpack_from('<II', raw, 4)
        off, chunks = 12, []
        while off < len(raw):
            ln, ty = struct.unpack_from('<I4s', raw, off)
            chunks.append((ty.decode('latin1'), off + 8, ln))
            off += 8 + ln
        js = next(c for c in chunks if c[0] == 'JSON')
        j = json.loads(raw[js[1]:js[1] + js[2]])
        binc = next((c for c in chunks if c[0].startswith('BIN')), None)
        bin_bytes = raw[binc[1]:binc[1] + binc[2]] if binc else b''
        return dict(kind='GLB v%d' % ver, raw=raw, json=j, bin=bin_bytes, chunks=chunks, total=total)
    j = json.loads(raw.decode('utf-8'))
    bp = None
    for b in j.get('buffers', []):
        if 'uri' in b and not b['uri'].startswith('data:'):
            bp = os.path.join(os.path.dirname(p), b['uri'])
    bb = open(bp, 'rb').read() if bp and os.path.exists(bp) else b''
    return dict(kind='glTF-text', raw=raw, json=j, bin=bb, chunks=[], bin_path=bp)

def stats(g):
    j = g['json']
    acc = j.get('accessors', [])
    verts = tris = 0
    for m in j.get('meshes', []):
        for pr in m['primitives']:
            verts += acc[pr['attributes']['POSITION']]['count']
            if 'indices' in pr: tris += acc[pr['indices']]['count'] // 3
    return verts, tris

def pos_bounds(g):
    j = g['json']; acc = j['accessors']; lo = [1e9] * 3; hi = [-1e9] * 3
    for m in j.get('meshes', []):
        for pr in m['primitives']:
            a = acc[pr['attributes']['POSITION']]
            if 'min' in a:
                lo = [min(x, y) for x, y in zip(lo, a['min'])]; hi = [max(x, y) for x, y in zip(hi, a['max'])]
    return lo, hi

def info(p):
    g = load(p); j = g['json']
    print(p, g['kind'], 'bytes', len(g['raw']), 'sha256', hashlib.sha256(g['raw']).hexdigest()[:16])
    print('chunks', g['chunks'], 'bin bytes', len(g['bin']), 'bin sha', hashlib.sha256(g['bin']).hexdigest()[:16])
    print('asset', j.get('asset'))
    for k in ('scenes', 'nodes', 'meshes', 'skins', 'materials', 'textures', 'images', 'accessors', 'bufferViews', 'buffers', 'animations', 'samplers', 'cameras'):
        print('  %-12s %d' % (k, len(j.get(k, []))))
    print('extensionsUsed', j.get('extensionsUsed'), 'extensionsRequired', j.get('extensionsRequired'))
    print('top-level keys', sorted(j.keys()))
    print('verts, tris', stats(g), 'POSITION bounds', pos_bounds(g))
    ex = [(i, n.get('name'), n['extras']) for i, n in enumerate(j.get('nodes', [])) if 'extras' in n]
    print('node extras', ex[:5], '| scene extras', [s.get('extras') for s in j.get('scenes', [])], '| asset extras', j.get('asset', {}).get('extras'))
    print('meshes:')
    for i, m in enumerate(j.get('meshes', [])):
        print('   [%d] %s prims=%d attrs=%s' % (i, m.get('name'), len(m['primitives']), sorted(m['primitives'][0]['attributes'])))
    print('materials:', [(m.get('name'), 'pbr' in str(m) and list(m.get('pbrMetallicRoughness', {}).keys())) for m in j.get('materials', [])][:20])
    print('images:', [(im.get('name'), im.get('uri', '')[:40], im.get('mimeType')) for im in j.get('images', [])][:30])
    for s in j.get('skins', []): print('skin joints', len(s['joints']), 'skeleton', s.get('skeleton'))

def summary(paths):
    print('path\tkind\tbytes\tjson_sha\tbin_len\tbin_sha\tnodes\tmeshes\tverts\ttris\tskins\tmats\timages')
    for p in paths:
        try: g = load(p)
        except Exception as e: print(p, 'ERR', e); continue
        j = g['json']; v, t = stats(g)
        canon = json.dumps(j, sort_keys=True).encode()
        print('\t'.join(map(str, [p, g['kind'], len(g['raw']), hashlib.sha256(canon).hexdigest()[:10], len(g['bin']), hashlib.sha256(g['bin']).hexdigest()[:10], len(j.get('nodes', [])), len(j.get('meshes', [])), v, t, len(j.get('skins', [])), len(j.get('materials', [])), len(j.get('images', []))])))

def diff(a, b):
    A, B = load(a), load(b)
    ja, jb = json.dumps(A['json'], sort_keys=True, indent=1).splitlines(), json.dumps(B['json'], sort_keys=True, indent=1).splitlines()
    import difflib
    d = [l for l in difflib.unified_diff(ja, jb, lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
    print('JSON canonical diff lines:', len(d)); print('\n'.join(d[:60]))
    x, y = A['bin'], B['bin']
    if len(x) == len(y):
        n = sum(1 for i in range(len(x)) if x[i] != y[i]); print('bin same length', len(x), 'differing bytes', n)
    else: print('bin lengths differ', len(x), len(y))

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'info': info(sys.argv[2])
    elif c == 'summary': summary(sys.argv[2:])
    elif c == 'diff': diff(sys.argv[2], sys.argv[3])
