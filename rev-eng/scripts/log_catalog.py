"""log_catalog.py - (lane J) map CLOAPI wrapper functions -> referenced strings (RIP-relative lea scan, no disassembler).
Writes raw/log_catalog.json and raw/python_prefix_strings.txt. Read-only on the exe. Usage: python -I scripts/log_catalog.py"""
import json, mmap, struct, os, re
EXE = r"C:\Program Files\Clo Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "..", "raw")
BASE = 0x140000000
f = open(EXE, "rb"); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
pe = struct.unpack_from("<I", m, 0x3c)[0]; ns = struct.unpack_from("<H", m, pe+6)[0]; osz = struct.unpack_from("<H", m, pe+20)[0]
SECS = []
for i in range(ns):
    o = pe+24+osz+40*i
    nm = m[o:o+8].rstrip(b"\0").decode(); vsz, va, rsz, rp = struct.unpack_from("<IIII", m, o+8)
    SECS.append((nm, va, vsz, rp, rsz))
def off(rva):
    for n, va, vsz, rp, rsz in SECS:
        if va <= rva < va+max(vsz, rsz) and rva-va < rsz: return rp+rva-va
def cstr(rva, maxn=400):
    o = off(rva)
    if o is None: return None
    b = m[o:o+maxn]; e = b.find(b"\0")
    if e < 3: return None
    s = b[:e]
    if all(32 <= c < 127 or c in (9, 10, 13) for c in s): return s.decode()
    return None
def wstr(rva, maxn=400):
    o = off(rva)
    if o is None: return None
    b = m[o:o+maxn]
    for i in range(0, len(b)-1, 2):
        if b[i:i+2] == b"\0\0": b = b[:i]; break
    else: return None
    if len(b) < 6: return None
    try: s = b.decode("utf-16le")
    except Exception: return None
    return s if all(32 <= ord(c) < 127 for c in s) else None
vt = json.load(open(os.path.join(RAW, "exe_vtables.json")))
text = [s for s in SECS if s[0] == ".text"][0]
tbuf = m[text[3]:text[3]+text[4]]
funcs = {}
for cls, v in vt.items():
    for s in v["slots"]:
        if s["rva"] not in funcs: funcs[s["rva"]] = (cls, s["slot"])
order = sorted(funcs)
res = []
for i, r in enumerate(order):
    cls, slot = funcs[r]
    start = r - text[1]
    lim = min(start+0x3000, len(tbuf))
    # cut at 4+ int3 following ret/jmp
    seg = bytes(tbuf[start:lim]); cut = len(seg)
    # end of function: first int3 that directly follows ret (c3) or a jmp (e9 rel32 / ff 25 rel32); stop earlier at next vtable function
    for p in range(16, len(seg)):
        if seg[p] == 0xCC and (seg[p-1] == 0xC3 or seg[p-5] == 0xE9 or seg[p-6:p-4] == bytes([255, 37])):
            cut = p; break
    if i+1 < len(order): cut = min(cut, order[i+1]-r)
    seg = seg[:cut]
    strs = []; seen = set(); calls = []
    for j in range(len(seg)-7):
        if seg[j] in (0x48, 0x4c) and seg[j+1] == 0x8d and (seg[j+2] & 0xC7) == 0x05:
            disp = struct.unpack_from("<i", seg, j+3)[0]
            t = r + j + 7 + disp
            s = cstr(t) or wstr(t)
            if s and t not in seen: seen.add(t); strs.append((hex(t), s))
        if seg[j] == 0xe8:
            calls.append(r+j+5+struct.unpack_from("<i", seg, j+1)[0])
    res.append(dict(rva=hex(r), cls=cls, slot=slot, size=cut, strings=strs, calls=[hex(c) for c in calls]))
json.dump(res, open(os.path.join(RAW, "log_catalog.json"), "w"), indent=1)
print("funcs", len(res), "with strings", sum(1 for x in res if x["strings"]))
print("span", hex(order[0]), hex(order[-1]))
# [Python] strings globally (ASCII + UTF-16)
out = []
for pat, kind in ((rb"\[Python\][ -~]{0,300}", "A"), (re.escape("[Python]".encode("utf-16le")) + rb"(?:[ -~]\x00){0,300}", "W")):
    for mt in re.finditer(pat, m):
        raw = mt.group(0)
        s = raw.decode("utf-16le") if kind == "W" else raw.decode()
        # file offset -> rva
        fo = mt.start(); rva = None
        for n, va, vsz, rp, rsz in SECS:
            if rp <= fo < rp+rsz: rva = va+fo-rp; break
        out.append((rva, kind, s))
open(os.path.join(RAW, "python_prefix_strings.txt"), "w").write("\n".join("%s\t%s\t%s" % (hex(a) if a else "?", k, s) for a, k, s in out))
print("python strings", len(out))
