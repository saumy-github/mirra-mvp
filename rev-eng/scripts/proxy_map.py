"""proxy_map.py (lane J) - map '[Python] <Name>' Qt-info trace strings to the code sites that emit them and to the
CLOAPI APICommand::Get*API + vtable slot they forward to. Static scan only. Writes raw/python_proxy_map.json.
Usage: python -I scripts/proxy_map.py"""
import re, mmap, struct, json, os, collections
EXE = r"C:\Program Files\Clo Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "..", "raw")
f = open(EXE, "rb"); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
pe = struct.unpack_from("<I", m, 0x3c)[0]; ns = struct.unpack_from("<H", m, pe+6)[0]; osz = struct.unpack_from("<H", m, pe+20)[0]
S = {}
for i in range(ns):
    o = pe+24+osz+40*i; nm = m[o:o+8].rstrip(b"\0").decode(); vsz, va, rsz, rp = struct.unpack_from("<IIII", m, o+8); S[nm] = (va, rp, rsz)
tva, trp, trsz = S[".text"]; tbuf = m[trp:trp+trsz]
# IAT names for CLOAPIInterface.dll Get*API
opt = pe+24; impdir = struct.unpack_from("<I", m, opt+112+8)[0]
def fo(r):
    for nm, (va, rp, rsz) in S.items():
        if va <= r < va+rsz: return rp+r-va
iat = {}
p = impdir
while True:
    oft, ts, fc, nmr, ft = struct.unpack_from("<IIIII", m, fo(p))
    if nmr == 0: break
    dll = m[fo(nmr):fo(nmr)+60].split(b"\0")[0].decode()
    if dll.lower() == "cloapiinterface.dll":
        k = 0
        while True:
            th = struct.unpack_from("<Q", m, fo(oft)+8*k)[0]
            if th == 0: break
            nmx = m[fo(th & 0x7fffffff)+2:fo(th & 0x7fffffff)+90].split(b"\0")[0].decode()
            iat[ft+8*k] = nmx; k += 1
    p += 20
json.dump({hex(k): v for k, v in iat.items()}, open(os.path.join(RAW, "cloapi_iat.json"), "w"), indent=1)
pys = []
for l in open(os.path.join(RAW, "python_prefix_strings.txt")):
    a, k, s = l.rstrip("\n").split("\t", 2)
    if a != "?" and k == "A" and re.fullmatch(r"\[Python\] [~A-Za-z0-9_]+ ?", s): pys.append((int(a, 16), s.strip()[9:]))
want = {a: n for a, n in pys}
sites = collections.defaultdict(list)
for mt in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", tbuf):
    j = mt.start(); t = tva+j+7+struct.unpack_from("<i", tbuf, j+3)[0]
    if t in want: sites[t].append(tva+j)
out = []
for t, n in sorted(want.items()):
    for site in sites.get(t, []):
        seg = bytes(tbuf[site-tva:site-tva+0x90])
        api = None; slot = None
        for mt in re.finditer(rb"\xff\x15", seg):
            tgt = site + mt.start() + 6 + struct.unpack_from("<i", seg, mt.start()+2)[0]
            if tgt in iat and iat[tgt].startswith("?Get") and "API@APICommand" in iat[tgt]:
                api = re.match(r"\?Get(\w+)API@", iat[tgt]).group(1)
                tail = seg[mt.end()+4:]
                # first indirect call through [reg+disp8/32] afterwards
                v = re.search(rb"\x41?\xff[\x50-\x57]([\x00-\xff])|\x41?\xff[\x90-\x97](.{4})", seg[mt.start()+6:], re.S)
                if v:
                    slot = (v.group(1)[0] if v.group(1) else struct.unpack("<i", v.group(2))[0]) // 8
                break
        out.append(dict(name=n, string_rva=hex(t), site=hex(site), api=api, slot=slot))
json.dump(out, open(os.path.join(RAW, "python_proxy_map.json"), "w"), indent=1)
print(len(out), "sites;", sum(1 for x in out if x["api"]), "with API;", sum(1 for x in out if x["slot"] is not None), "with slot")
print(collections.Counter(x["api"] for x in out))
