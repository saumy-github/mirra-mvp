"""avs_grammar.py - parser/writer for CLO's typed property stream (.avs, .dan, .osw).
Usage: python -I avs_grammar.py roundtrip FILE...   | tree FILE [out.json] | dan FILE.avt
Stdlib only. Read-only on inputs.

Grammar (little endian), decoded from CLO_Male_Default.avs and verified by byte-exact round trip:
  block   := u8 n | u8 namelen[n] | u8 type[n] | u32 size[n] | (name[n_i] value[n_i])*   (names/values interleaved)
  value   := raw bytes of length size[i], interpreted by type[i]
  type 0x01 bool(u8)  0x04 int32  0x06 float32  0x0f string (utf8, size=bytes)
       0x14 list  := u32 count | u8 elemtype | u32 elemsize[count] | elem*   (elem payload per elemtype)
       0x16 struct:= nested block
  Unknown types are kept as raw bytes (so round trip is always exact).
"""
import sys, struct, json, zipfile, io

T_BOOL, T_INT, T_FLOAT, T_STR, T_LIST, T_STRUCT = 1, 4, 6, 0x0f, 0x14, 0x16

class Raw:
    def __init__(self, t, b): self.t, self.b = t, b
    def __repr__(self): return 'Raw(0x%02x,%dB)' % (self.t, len(self.b))

def parse_block(buf, off, end):
    n = buf[off]; p = off + 1
    nl = list(buf[p:p+n]); p += n
    ty = list(buf[p:p+n]); p += n
    sz = list(struct.unpack_from('<%dI' % n, buf, p)); p += 4 * n
    fields = []
    for i in range(n):
        name = bytes(buf[p:p+nl[i]]).decode('latin1'); p += nl[i]
        fields.append((name, ty[i], parse_value(buf, p, ty[i], sz[i])))
        p += sz[i]
    if p != end: raise ValueError('block end mismatch %d != %d' % (p, end))
    return fields

def parse_value(buf, p, t, s):
    b = bytes(buf[p:p+s])
    if t == T_BOOL and s == 1: return b[0] != 0 if b[0] in (0, 1) else Raw(t, b)
    if t == T_INT and s == 4: return struct.unpack('<i', b)[0]
    if t == T_FLOAT and s == 4: return ('f', struct.unpack('<f', b)[0], b.hex())
    if t == T_STR: return ('s', b)
    if t == T_STRUCT: return parse_block(buf, p, p + s)
    if t == T_LIST:
        c = struct.unpack_from('<I', buf, p)[0]
        if s == 4 and c == 0: return ('L', None, [])
        et = buf[p+4]
        es = struct.unpack_from('<%dI' % c, buf, p+5); q = p + 5 + 4 * c
        items = []
        for e in es:
            items.append(parse_value(buf, q, et, e)); q += e
        if q != p + s: raise ValueError('list size mismatch')
        return ('L', et, items)
    return Raw(t, b)

def enc_value(t, v):
    if isinstance(v, Raw): return v.b
    if t == T_BOOL: return bytes([1 if v else 0])
    if t == T_INT: return struct.pack('<i', v)
    if t == T_FLOAT: return bytes.fromhex(v[2])
    if t == T_STR: return v[1]
    if t == T_STRUCT: return enc_block(v)
    if t == T_LIST:
        _, et, items = v
        if et is None: return struct.pack('<I', 0)
        enc = [enc_value(et, x) for x in items]
        return struct.pack('<I', len(items)) + bytes([et]) + b''.join(struct.pack('<I', len(e)) for e in enc) + b''.join(enc)
    raise ValueError(t)

def enc_block(fields):
    names = [f[0].encode('latin1') for f in fields]
    vals = [enc_value(f[1], f[2]) for f in fields]
    return (bytes([len(fields)]) + bytes(len(x) for x in names) + bytes(f[1] for f in fields) +
            b''.join(struct.pack('<I', len(v)) for v in vals) + b''.join(n + v for n, v in zip(names, vals)))

TYPE_NAMES = {1: 'bool', 4: 'int32', 5: 'uint32', 6: 'float32', 0x0a: 'vec2f', 0x0b: 'vec3f', 0x0c: 'vec4f',
              0x0e: 'mat4f', 0x0f: 'string', 0x14: 'list', 0x15: 'array', 0x16: 'struct'}
# type 0x15 'array' := u32 count | u8 elemtype | count*elemsize packed (verified sizes 9/13/17/21/25 etc.)

def index_block(buf, off, end, path, out, minsize=0, maxdepth=99, depth=0):
    """Streaming walk recording (path, abs_offset_of_value, size, type, name) without building objects."""
    n = buf[off]; p = off + 1
    nl = buf[p:p+n]; p += n
    ty = buf[p:p+n]; p += n
    sz = struct.unpack_from('<%dI' % n, buf, p); p += 4 * n
    for i in range(n):
        name = bytes(buf[p:p+nl[i]]).decode('latin1'); p += nl[i]
        if sz[i] >= minsize: out.append((path + '/' + name, p, sz[i], ty[i], depth))
        if ty[i] == T_STRUCT and depth < maxdepth:
            index_block(buf, p, p + sz[i], path + '/' + name, out, minsize, maxdepth, depth + 1)
        elif ty[i] == T_LIST and depth < maxdepth and sz[i] > 4:
            c = struct.unpack_from('<I', buf, p)[0]; et = buf[p+4]
            es = struct.unpack_from('<%dI' % c, buf, p+5); q = p + 5 + 4 * c
            if et in (T_STRUCT,):
                for k, e in enumerate(es):
                    index_block(buf, q, q + e, '%s/%s[%d]' % (path, name, k), out, minsize, maxdepth, depth + 1); q += e
        p += sz[i]

def parse(buf): return parse_block(buf, 0, len(buf))

def to_json(v):
    if isinstance(v, Raw): return {'raw_type': v.t, 'hex': v.b.hex()}
    if isinstance(v, tuple):
        if v[0] == 'f': return round(v[1], 6)
        if v[0] == 's': return v[1].decode('utf8', 'replace')
        if v[0] == 'L': return [to_json(x) for x in v[2]]
    if isinstance(v, list): return {n: to_json(x) for n, t, x in v}
    return v

# listFeatureValues index -> name (cm). Matched by value against default-avatar-csv.csv (mm/10) of the male default;
# 0,1 and the '?' entries are not in that CSV. INFERENCE, see findings/13.
FEATURE_NAMES = {0: 'Total Height', 1: '? (70.0; weight kg?)', 2: 'Bust/Chest Circumference', 3: 'Mid Neck Circumference',
    4: 'Neck Base Circumference', 5: 'Under Bust Circumference', 6: 'Waist Circumference', 7: 'High Hip Circumference',
    8: 'Low Hip Circumference', 9: 'Thigh Circumference', 10: 'Mid Thigh Circumference', 11: 'Knee Circumference',
    12: 'Calf Circumference', 13: 'Ankle Circumference', 14: 'Armhole Circumference', 15: 'Bicep Circumference (approx)',
    16: 'Elbow Circumference', 17: 'Wrist Circumference', 18: 'HPS Height', 19: 'Shoulder Height', 20: 'Shoulder Drop',
    21: 'Bust Height', 22: 'Under Bust Height', 23: 'Waist Height', 24: 'High Hip Height', 25: 'Low Hip Height',
    26: 'Inseam Height', 27: 'Thigh Height', 28: 'Mid Thigh Height', 29: 'Knee Height', 30: 'Calf Height', 31: 'Ankle Height',
    32: '? (30.8)', 33: '? (20.1)', 34: 'Across Front', 35: 'Across Back', 36: 'Across Shoulder (Curvilinear)',
    37: 'Across Shoulder (CB Neck)', 38: 'CF Neck to Across Front', 39: 'CB Neck to Across Back', 40: 'CF Neck to Waist',
    41: 'CB Neck to Waist', 42: 'Waist to High Hip', 43: 'Waist to Low Hip', 44: 'Apex to Apex', 45: 'HPS to Apex',
    46: 'Halter', 47: 'Arm Length', 48: '? (86.7)', 49: 'Total Rise', 50: 'Front Rise', 51: 'Back Rise', 52: '? (29.0)',
    53: '? (23.0)', 54: '? (13.7)', 55: 'Front Vertical Trunk', 56: 'Back Vertical Trunk', 57: 'Vertical Trunk',
    58: 'Hand Length', 59: 'Head Circumference', 60: '? (30.0)', 61: '? (30.0)', 62: '? (0.0; cup-size extension)',
    63: '? (0.0)', 64: '? (0.0)', 65: '? (50.0)', 66: '? (50.0)'}

def collapse_json(js):
    import re
    return re.sub(r'\[\s+([^\[\]{}]*?)\s+\]', lambda m: '[' + ' '.join(m.group(1).split()) + ']', js)

def main():
    cmd = sys.argv[1]
    if cmd == 'roundtrip':
        ok = bad = 0
        for f in sys.argv[2:]:
            d = open(f, 'rb').read()
            try:
                if enc_block(parse(d)) == d: ok += 1
                else: bad += 1; print('MISMATCH', f)
            except Exception as e: bad += 1; print('ERR', f, e)
        print('ok', ok, 'bad', bad)
    elif cmd == 'tree':
        d = open(sys.argv[2], 'rb').read()
        tree = to_json(parse(d))
        mv = tree.get('MVresizingMap', {})
        if 'listFeatureValues' in mv:
            tree['_feature_index_map'] = {str(i): {'name': FEATURE_NAMES.get(i, '?'), 'value_cm': v}
                                           for i, v in enumerate(mv['listFeatureValues'])}
        js = collapse_json(json.dumps(tree, indent=1))
        if len(sys.argv) > 3: open(sys.argv[3], 'w').write(js)
        else: print(js)

if __name__ == '__main__': main()


# ---------------------------------------------------------------- .dan helpers (lane F)
def load_dan(path):
    """Return .dan bytes from an .avt/.zprj (first *.dan member) or the file itself if it is a bare stream."""
    raw = open(path, 'rb').read()
    zs = raw.find(b'PK\x03\x04')
    if raw[:4] == b'PK\x03\x04' or (zs > 0 and raw[:3] == b' AV'):
        z = zipfile.ZipFile(io.BytesIO(raw[zs:]))
        for zi in z.infolist():
            if zi.filename.lower().endswith('.dan'): return z.read(zi)
    return raw

def leaf_map(d):
    """path -> (offset, size, type) for every non-container leaf (struct children and struct-list items expanded)."""
    out = []
    index_block(d, 0, len(d), '', out)
    cont = set()
    for path, off, sz, ty, dep in out:
        if ty == T_STRUCT: cont.add(path)
    res = {}
    for path, off, sz, ty, dep in out:
        if ty == T_STRUCT: continue
        if ty == T_LIST and sz > 4 and d[off+4] == T_STRUCT: continue
        res[path] = (off, sz, ty)
    return res

def dan_diff(a, b, floats=True):
    la, lb = leaf_map(a), leaf_map(b)
    rows = []
    for p in sorted(set(la) | set(lb)):
        if p not in la or p not in lb: rows.append((p, 'only_in_' + ('A' if p in la else 'B'), 0, 0)); continue
        oa, sa, ta = la[p]; ob, sb, tb = lb[p]
        x, y = a[oa:oa+sa], b[ob:ob+sb]
        if x == y: continue
        if len(x) != len(y): rows.append((p, 'size %d->%d' % (sa, sb), 0, 0)); continue
        nd = sum(1 for i in range(len(x)) if x[i] != y[i])
        mx = 0.0
        if floats and len(x) % 4 == 0 and ta in (T_STR, 0x0b, 0x0c, 0x0e, T_FLOAT, 0x0a):
            n = len(x) // 4
            fa, fb = struct.unpack('<%df' % n, x), struct.unpack('<%df' % n, y)
            mx = max(abs(u - v) for u, v in zip(fa, fb) if u == u and v == v)
        rows.append((p, 'bytes_diff', nd, mx))
    return rows

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'dandiff':
    # usage: dandiff A B [minbytes]  -> prints only leaves with >= minbytes differing bytes (default 1) + totals
    a, b = load_dan(sys.argv[2]), load_dan(sys.argv[3])
    mb = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    rows = dan_diff(a, b)
    print('len', len(a), len(b), 'leaves differing', len(rows), 'total differing bytes', sum(r[2] for r in rows))
    for r in rows:
        if r[1] != 'bytes_diff' or r[2] >= mb:
            try: print('%-14s %8s %12.6g  %s' % (r[1], r[2], r[3], r[0].replace('/listChildrenTransformer3D', '/LCT')))
            except OSError: break
