"""avt_probe.py - stdlib probe for CLO .avt / .zprj (custom header + embedded ZIP) and .avs.
Usage: python -I avt_probe.py info FILE | diff A B | strings FILE [member]
Read-only. Never writes next to inputs.
"""
import sys, struct, zipfile, io, hashlib, re

def read(p):
    with open(p, 'rb') as f: return f.read()

def parse_header(raw):
    """Return dict describing the pre-zip prefix."""
    h = {'magic_text': raw[:16].decode('latin1'), 'u32_at_0x10': list(struct.unpack_from('<9I', raw, 0x10))}
    n = struct.unpack_from('<I', raw, 0x40)[0]
    h['uid_len'] = n
    h['uid'] = raw[0x44:0x44 + n].decode('latin1', 'replace')
    return h

def zip_start(raw):
    return raw.find(b'PK\x03\x04')

def members(raw):
    zs = zip_start(raw)
    if zs < 0: return zs, []
    z = zipfile.ZipFile(io.BytesIO(raw[zs:]))
    return zs, z.infolist(), z

def feature_block(dan, marker=b'listFeatureValues', off=273, n=57):
    i = dan.find(marker)
    if i < 0: return None, []
    s = i + len(marker) + off
    return s, [struct.unpack_from('<f', dan, s + 4 * k)[0] for k in range(n)]

def info(p):
    raw = read(p)
    print('file', p, 'size', len(raw), 'sha256', hashlib.sha256(raw).hexdigest())
    print('first16', raw[:16])
    if raw[:2] == b'\x03\x0a' or b'listFeatureValues' in raw[:600]:
        print('looks like bare .dan/.avs stream; marker at', raw.find(b'listFeatureValues'))
        s, v = feature_block(raw, off=0) if False else (None, [])
        # avs: float block located heuristically
        m = raw.find(b'listFeatureValues')
        for o in range(m, m + 400):
            a, b = struct.unpack_from('<2f', raw, o)
            if 100 < a < 250 and 30 < b < 200:
                print('float block offset', o, [round(struct.unpack_from('<f', raw, o + 4 * k)[0], 3) for k in range(57)])
                break
        return
    zs = zip_start(raw)
    print('zip_start', zs, 'prefix_len', zs)
    if zs > 0:
        print('header', parse_header(raw))
    if zs < 0: return
    z = zipfile.ZipFile(io.BytesIO(raw[zs:]))
    for zi in z.infolist():
        print('  member %-50s comp=%d csize=%d usize=%d crc=%08x hdr_off=%d' % (zi.filename, zi.compress_type, zi.compress_size, zi.file_size, zi.CRC, zi.header_offset + zs))
        if zi.filename.endswith('.dan'):
            d = z.read(zi)
            s, v = feature_block(d)
            print('    .dan feature block @', s, [round(x, 3) for x in v])

def diff(a, b):
    ra, rb = read(a), read(b)
    print('size', len(ra), len(rb), 'equal' if ra == rb else 'differ')
    za, zb = zip_start(ra), zip_start(rb)
    print('prefix', za, zb, 'prefix_equal', ra[:za] == rb[:zb] if za == zb else False)
    if za == zb and ra[:za] != rb[:zb]:
        d = [i for i in range(za) if ra[i] != rb[i]]
        print(' prefix diff offsets', d[:40], 'count', len(d))
    A = {zi.filename: (zi, zipfile.ZipFile(io.BytesIO(ra[za:])).read(zi)) for zi in zipfile.ZipFile(io.BytesIO(ra[za:])).infolist()}
    B = {zi.filename: (zi, zipfile.ZipFile(io.BytesIO(rb[zb:])).read(zi)) for zi in zipfile.ZipFile(io.BytesIO(rb[zb:])).infolist()}
    for k in sorted(set(A) | set(B)):
        if k not in A or k not in B: print(' only in one:', k); continue
        x, y = A[k][1], B[k][1]
        if x == y: print(' same  ', k, len(x)); continue
        dif = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
        print(' DIFF  %s len %d/%d, %d differing bytes, first offsets %s' % (k, len(x), len(y), len(dif), dif[:12]))
        if k.endswith('.dan'):
            sa, va = feature_block(x); sb, vb = feature_block(y)
            for i, (p, q) in enumerate(zip(va, vb)):
                if abs(p - q) > 1e-6: print('    feature[%d] %.4f -> %.4f' % (i, p, q))

def strings(p, member=None, minlen=6):
    raw = read(p); zs = zip_start(raw)
    data = raw
    if zs >= 0 and member:
        data = zipfile.ZipFile(io.BytesIO(raw[zs:])).read(member)
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data):
        print(m.start(), m.group().decode())

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'info': info(sys.argv[2])
    elif c == 'diff': diff(sys.argv[2], sys.argv[3])
    elif c == 'strings': strings(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
