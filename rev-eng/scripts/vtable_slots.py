"""Recover vtable slot order of CLOAPI::*APIInterface from a CLOAPIInterface.dll (stdlib only).
Method = export; vtable entries point at the real function, exports at a jmp thunk (E9 rel32) or the function itself.
Usage: vtable_slots.py <dll> <exports.txt> <out.json>"""
import struct, re, sys, json, subprocess
dll, exp, out = sys.argv[1:4]
UN = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\undname.exe"
d = open(dll,'rb').read(); pe = struct.unpack_from('<I', d, 0x3c)[0]
n = struct.unpack_from('<H', d, pe+6)[0]; opt = struct.unpack_from('<H', d, pe+20)[0]
base = struct.unpack_from('<Q', d, pe+24+24)[0]
secs = [struct.unpack_from('<8sIIII', d, pe+24+opt+i*40) for i in range(n)]
def off(rva):
    for nm,vs,va,rs,rp in secs:
        if va <= rva < va+max(vs,rs): return rp + rva - va
    return None
def q(rva): o = off(rva); return None if o is None else struct.unpack_from('<Q', d, o)[0]
def resolve(rva):
    o = off(rva)
    if o is not None and d[o] == 0xE9: return rva + 5 + struct.unpack_from('<i', d, o+1)[0]
    return rva
ex = {}
for l in open(exp, encoding='utf8', errors='ignore'):
    m = re.match(r"\s+(\d+)\s+[0-9A-F]+\s+([0-9A-F]{8})\s+(\S+)", l)
    if m: ex[m.group(3)] = int(m.group(2),16)
def undec(s):
    o = subprocess.run([UN, s], capture_output=True, text=True).stdout
    m = re.search(r'is :- "(.*)"', o); return m.group(1) if m else s
func_by_rva = {}
for nm, rva in ex.items():
    if '@@' in nm and not nm.startswith('??_7'): func_by_rva.setdefault(resolve(rva), []).append(nm)
res = {}
vrvas = sorted(r for n_, r in ex.items() if n_.startswith('??_7'))
for nm, rva in ex.items():
    m = re.match(r"\?\?_7(\w+)@CLOAPI@@6B@", nm)
    if not m: continue
    cls = m.group(1); slots = []; i = 0
    nxt = [r for r in vrvas if r > rva]; limit = ((nxt[0] - 8 - rva)//8) if nxt else 600
    while True:
        v = q(rva + 8*i)
        if v is None or v < base: break
        r = v - base
        if off(r) is None: break
        names = func_by_rva.get(r) or func_by_rva.get(resolve(r)) or []
        names = [x for x in names if f"@{cls}@CLOAPI@@" in x]   # same-class only (ICF folds stubs across classes)
        slots.append([names, r])
        i += 1
        if i >= limit: break
    res[cls] = slots
sig = {}
for cls, sl in res.items():
    sig[cls] = []
    for i,(nms,r) in enumerate(sl):
        sig[cls].append({"slot": i, "rva": r, "n_candidates": len(nms), "sym": nms[0] if len(nms)==1 else None,
                         "candidates": [undec(x) for x in nms] if len(nms)>1 else [],
                         "demangled": undec(nms[0]) if len(nms)==1 else None})
json.dump(sig, open(out,'w'), indent=1)
for c,s in sig.items(): print(c, len(s), "slots; unique:", sum(1 for x in s if x['sym']), "ambiguous(ICF):", sum(1 for x in s if x['n_candidates']>1), "none:", sum(1 for x in s if x['n_candidates']==0))
