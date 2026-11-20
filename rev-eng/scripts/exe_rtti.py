"""RTTI/vtable recovery for the CLO exe (stdlib, mmap). Caches to raw/exe_rtti_cache.json.
Usage: python -I exe_rtti.py [exe]   -> raw/exe_vtables.json
"""
import mmap, struct, re, json, os, sys
EXE = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")
CACHE = os.path.join(RAW, "exe_rtti_cache.json")
f = open(EXE, 'rb'); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
pe = struct.unpack_from('<I', m, 0x3c)[0]
nsec = struct.unpack_from('<H', m, pe+6)[0]; opt = struct.unpack_from('<H', m, pe+20)[0]
BASE = struct.unpack_from('<Q', m, pe+24+24)[0]
secs = []
for i in range(nsec):
    nm, vs, va, rs, rp = struct.unpack_from('<8sIII I', m, pe+24+opt+i*40)[:5] if False else struct.unpack_from('<8sIIII', m, pe+24+opt+i*40)
    secs.append((nm.rstrip(b'\0').decode(), va, max(vs, rs), rp, rs))
def off(rva):
    for nm, va, sz, rp, rs in secs:
        if va <= rva < va+sz: return rp + rva - va if rva-va < rs else None
    return None
def rva_of(o):
    for nm, va, sz, rp, rs in secs:
        if rp <= o < rp+rs: return va + o - rp
def u32(r): o = off(r); return struct.unpack_from('<I', m, o)[0]
def u64(r): o = off(r); return struct.unpack_from('<Q', m, o)[0]
def read_name(tdrva):
    o = off(tdrva+16); e = m.find(b'\0', o, o+512); return m[o:e].decode('latin1')
def find_all(pat, lo, hi):
    p = lo
    while True:
        p = m.find(pat, p, hi)
        if p < 0: return
        yield p; p += 1
def sect(name):
    for s in secs:
        if s[0] == name: return s
def build():
    # 1. type descriptors with API-related names: scan whole raw image for ".?AV...@@" strings
    out = {"types": {}, "cols": {}}
    pat = re.compile(rb'\.\?A[VU][A-Za-z0-9_@?$]*?API[A-Za-z0-9_@?$]*@@\x00')
    for nm, va, sz, rp, rs in secs:
        if nm not in ('.data', '.rdata'): continue
        for mt in pat.finditer(m[rp:rp+rs]):
            name = mt.group().rstrip(b'\0').decode()
            td = va + (mt.start()+rp - rp) - 16
            out["types"][name] = td
    # 2. COLs: sig=1 , any offset; search for typedesc rva following 3 u32
    rd = sect('.rdata'); 
    for name, td in out["types"].items():
        for off0 in (0,):
            pt = struct.pack('<IIII', 1, 0, 0, td)
            for p in find_all(pt, rd[3], rd[3]+rd[4]):
                out["cols"].setdefault(name, []).append(rva_of(p))
    # 3. CHD base classes for each COL
    out["bases"] = {}
    for name, cols in out["cols"].items():
        c = cols[0]; chd = u32(c+16)
        n = u32(chd+8); arr = u32(chd+12)
        bl = []
        for i in range(n):
            bcd = u32(arr+4*i); bl.append(read_name(u32(bcd)))
        out["bases"][name] = bl
    return out
def vtable_of(col):
    pat = struct.pack('<Q', BASE+col)
    rd = sect('.rdata')
    return [rva_of(p)+8 for p in find_all(pat, rd[3], rd[3]+rd[4])]
if __name__ == '__main__':
    if os.path.exists(CACHE): C = json.load(open(CACHE))
    else:
        C = build(); json.dump(C, open(CACHE, 'w'))
    print(len(C["types"]), "types", len(C["cols"]), "with COL")
    for n, b in C["bases"].items(): print(n, b[1:])

def derived_vtables():
    C = json.load(open(CACHE)); res = {}
    for n in C["cols"]:
        if n.startswith('.?AV') and n.endswith('API@Marvelous@@') and 'Helper' not in n:
            cls = n[4:-2]
            vts = vtable_of(C["cols"][n][0])
            if not vts: continue
            v = vts[0]; slots = []; i = 0
            while True:
                p = u64(v+8*i) if off(v+8*i) is not None else 0
                r = p - BASE
                if not (p > BASE and off(r) is not None and any(s[0]=='.text' and s[1] <= r < s[1]+s[2] for s in secs)): break
                o = off(r); b = bytes(m[o:o+16]); tgt = None
                if b[0] == 0xE9: tgt = r + 5 + struct.unpack_from('<i', b, 1)[0]
                slots.append({"slot": i, "rva": r, "bytes": b.hex(), "jmp_target": tgt})
                i += 1
            res[cls] = {"vtable_rva": v, "n_slots": len(slots), "all_vtables": vts, "slots": slots}
    return res
if __name__ == '__main__':
    R = derived_vtables(); json.dump(R, open(os.path.join(RAW, "exe_vtables.json"), 'w'), indent=1)
    for k, v in R.items(): print(k, hex(v["vtable_rva"]), v["n_slots"], len(v["all_vtables"]))
