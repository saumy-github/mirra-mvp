"""disasm_fn2.py RVA [maxbytes] [name]  -- dumpbin disasm of one fn, cached in raw/disasm2/, annotates string refs. stdlib only."""
import sys, os, re, struct, subprocess
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
DUMP = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\dumpbin.exe"
BASE = 0x140000000
OUT = os.path.join(os.path.dirname(__file__), '..', 'raw', 'disasm2')
os.makedirs(OUT, exist_ok=True)
f = open(EXE, 'rb'); hdr = f.read(0x1000)
pe = struct.unpack_from('<I', hdr, 0x3c)[0]
n = struct.unpack_from('<H', hdr, pe+6)[0]; opt = struct.unpack_from('<H', hdr, pe+20)[0]
secs = []
for i in range(n):
    nm, vs, va, rs, rp = struct.unpack_from('<8sIIII', hdr, pe+24+opt+i*40)
    secs.append((nm.rstrip(b'\0').decode(), va, max(vs, rs), rp, rs))
def rva2off(r):
    for nm, va, sz, rp, rs in secs:
        if va <= r < va+min(sz, rs if rs else sz): return rp + r - va
    return None
def secname(r):
    for nm, va, sz, rp, rs in secs:
        if va <= r < va+sz: return nm
def readstr(va):
    r = va - BASE; o = rva2off(r)
    if o is None or secname(r) in ('.text',): return None
    f.seek(o); b = f.read(160)
    m = re.match(rb'[\x20-\x7e]{3,}', b)
    if m: return 'A"' + m.group().decode() + '"'
    m = re.match(rb'(?:[\x20-\x7e]\x00){3,}', b)
    if m: return 'W"' + m.group().decode('utf-16le') + '"'
    return None
def disasm(rva, size, name=None):
    path = os.path.join(OUT, '%x_%x.txt' % (rva, size))
    if not os.path.exists(path):
        a = BASE + rva
        r = subprocess.run([DUMP, '/disasm:nobytes', '/range:0x%x,0x%x' % (a, a+size), EXE], capture_output=True, text=True)
        open(path, 'w').write(r.stdout)
    lines = open(path).read().splitlines()
    out = []; ret_seen = False
    for l in lines:
        m = re.match(r'\s+([0-9A-F]{16}):\s+(.*)', l)
        if not m: continue
        va = int(m.group(1), 16); ins = m.group(2)
        note = ''
        for h in re.findall(r'\b(0000000[0-9A-F]{9})h?\b', ins):
            v = int(h, 16)
            if BASE <= v < BASE + 0x10000000 + 0x20000000:
                s = readstr(v)
                sn = secname(v-BASE)
                note += ' ; [%s %x]%s' % (sn, v-BASE, (' ' + s) if s else '')
        out.append('%x: %s%s' % (va-BASE, ins, note))
    # trim at padding after ret/jmp
    res = []
    for i, l in enumerate(out):
        res.append(l)
        if i+1 < len(out) and re.search(r'\bint\s+3\b', out[i+1]) and re.search(r'\b(ret|jmp)\b', l) and 'int' not in l:
            # padding: stop only if next 2 are int3
            if i+2 < len(out) and re.search(r'\bint\s+3\b', out[i+2]): break
    return res
if __name__ == '__main__':
    rva = int(sys.argv[1], 16); size = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x800
    print('\n'.join(disasm(rva, size)))
