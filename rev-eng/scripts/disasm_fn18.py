"""disasm_fn.py - disassemble one function of the CLO exe with dumpbin, annotate it.
Usage: python -I disasm_fn.py <RVA hex, e.g. 0x5fad0e0> [maxbytes=0x1400] [--md]
 - runs dumpbin /disasm:nobytes on a bounded range, caches raw output in raw/disasm/<rva>.txt
 - cuts the function at the first int3/padding run after a ret/jmp (heuristic; cold chunks not followed)
 - resolves RIP-relative / absolute data refs (dumpbin already prints absolute VAs) to strings in the PE
   (ASCII, UTF-16LE, or 16-byte inline xmm copies), lists call targets (first-level thunk resolved),
   global (.data) references, stack-cookie noted.
"""
import sys, os, re, struct, subprocess, mmap
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
DUMPBIN = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\dumpbin.exe"
BASE = 0x140000000
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "raw", "disasm18")
COOKIE = 0x14A172D40

_f = open(EXE, "rb"); _m = mmap.mmap(_f.fileno(), 0, access=mmap.ACCESS_READ)
_pe = struct.unpack_from("<I", _m, 0x3c)[0]
_ns = struct.unpack_from("<H", _m, _pe + 6)[0]
_osz = struct.unpack_from("<H", _m, _pe + 20)[0]
SECS = []
for i in range(_ns):
    o = _pe + 24 + _osz + 40 * i
    name = _m[o:o+8].rstrip(b"\0").decode()
    vsz, va, rsz, rptr = struct.unpack_from("<IIII", _m, o + 8)
    ch = struct.unpack_from("<I", _m, o + 36)[0]
    SECS.append((name, va, vsz, rptr, rsz, ch))

def sec_of(va):
    r = va - BASE
    for s in SECS:
        if s[1] <= r < s[1] + max(s[2], s[4]):
            return s
def read_va(va, n):
    s = sec_of(va)
    if not s or s[0].startswith(".bss"): return None
    off = s[3] + (va - BASE - s[1])
    if off - s[3] >= s[4]: return None
    return bytes(_m[off:off+n])

def cstr(va):
    b = read_va(va, 400)
    if not b: return None
    m = re.match(rb"[\x20-\x7e\t\r\n]{3,}", b)
    if m and (len(m.group()) < len(b) and b[len(m.group())] == 0 or len(m.group()) >= 390):
        return "A:" + m.group().decode()
    m = re.match(rb"(?:[\x20-\x7e]\x00){3,}", b)
    if m: return "W:" + m.group().decode("utf-16le")
    return None
def inline16(va):
    b = read_va(va, 16)
    if not b: return None
    t = re.sub(rb"[^\x20-\x7e]", b".", b).decode()
    return t if sum(c != "." for c in t) >= 6 else None

def run_dumpbin(start, size):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "%x_%x.txt" % (start - BASE, size))
    if not os.path.exists(p):
        out = subprocess.run([DUMPBIN, "/nologo", "/disasm:nobytes", "/range:0x%x,0x%x" % (start, start + size), EXE],
                             capture_output=True, text=True).stdout
        open(p, "w").write(out)
    return open(p).read()

LINE = re.compile(r"^\s+([0-9A-F]{16}): (\S+)\s*(.*)$")
def parse(txt):
    return [m.groups() for m in map(LINE.match, txt.splitlines()) if m]

def cut(ins):
    """Stop at first ret/jmp/int3 that is not followed by code reached via a forward jump seen so far."""
    out = []; maxt = 0
    for a, mn, op in ins:
        av = int(a, 16)
        if mn == "int" and av >= maxt: break
        if av > maxt and out and out[-1][1] in ("ret", "int") and mn not in ("int", "nop"):
            break
        out.append((a, mn, op))
        if mn.startswith("j") and re.fullmatch(r"[0-9A-F]{16}", op.strip()):
            t = int(op.strip(), 16)
            if t > maxt: maxt = t
    return out

def thunk(va):
    b = read_va(va, 8)
    if not b: return None
    if b[0] == 0xE9:
        return "jmp->%x" % (va + 5 + struct.unpack_from("<i", b, 1)[0])
    if b[:2] == b"\xff\x25":
        p = va + 6 + struct.unpack_from("<i", b, 2)[0]
        q = read_va(p, 8)
        return "jmp[iat %x]->%s" % (p, "%x" % struct.unpack("<Q", q)[0] if q else "?")
    return None

def analyse(rva, maxb=0x1400):
    start = BASE + rva
    ins = cut(parse(run_dumpbin(start, maxb)))
    calls = {}; strs = []; globs = {}; rows = []
    for a, mn, op in ins:
        note = ""
        for h in re.findall(r"\b([0-9A-F]{16})h?\b", op):
            v = int(h, 16)
            if not (BASE <= v < BASE + 0x10000000): continue
            if mn == "call" and op.strip() == h:
                t = thunk(v); calls.setdefault(v, [0, t]); calls[v][0] += 1
                note = "call 0x%x" % (v - BASE) + (" (%s)" % t if t else ""); continue
            if v == COOKIE: note = "stack cookie"; continue
            s = sec_of(v)
            sn = s[0] if s else "?"
            if mn in ("jmp",) or mn.startswith("j"): continue
            st = cstr(v) or inline16(v)
            if st:
                strs.append((a, v, st)); note = "%s %x -> %r" % (sn, v - BASE, st)
            else:
                globs.setdefault(v, [sn, 0]); globs[v][1] += 1
                note = "%s %x" % (sn, v - BASE)
        rows.append((a, mn, op, note))
    return rows, calls, strs, globs

def main():
    rva = int(sys.argv[1], 16)
    maxb = int(sys.argv[2], 16) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 0x1400
    rows, calls, strs, globs = analyse(rva, maxb)
    if "--full" in sys.argv:
        for a, mn, op, n in rows: print("%s  %-8s %-40s ; %s" % (a[-9:], mn, op, n))
    print("== %d instructions, ends %s" % (len(rows), rows[-1][0][-9:] if rows else "?"))
    seen = []
    print("== strings")
    for a, v, s in strs:
        if any(x.endswith(s[2:]) or x == s for x in seen): continue
        seen.append(s); print("  %s  ref %x  %s" % (a[-9:], v - BASE, s))
    print("== calls (rva: count, thunk)"); [print("  %x: x%d %s" % (v - BASE, c, t or "")) for v, (c, t) in sorted(calls.items())]
    print("== data refs"); [print("  %x %s x%d" % (v - BASE, s, c)) for v, (s, c) in sorted(globs.items())]
if __name__ == "__main__":
    main()
