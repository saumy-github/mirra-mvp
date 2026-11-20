"""k_strscan.py - find NUL-delimited ASCII strings in the CLO exe and their rip-relative code xrefs (lane K).
Usage: python -I k_strscan.py [--sub] needle...   (exact-match by default; --sub = substring match of whole string)
Xrefs: any `lea/mov r64,[rip+disp]` (48/4C 8D|8B modrm&C7==05) whose target is the string start."""
import sys, re, struct, mmap, bisect
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
f=open(EXE,"rb"); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
pe=struct.unpack_from("<I",m,0x3c)[0]; ns=struct.unpack_from("<H",m,pe+6)[0]; osz=struct.unpack_from("<H",m,pe+20)[0]
S=[]
for i in range(ns):
    o=pe+24+osz+40*i; n=m[o:o+8].rstrip(b"\0").decode(); vsz,va,rsz,rp=struct.unpack_from("<IIII",m,o+8); S.append((n,va,vsz,rp,rsz))
def o2r(off):
    for n,va,vsz,rp,rsz in S:
        if rp<=off<rp+rsz: return va+off-rp
args=[a for a in sys.argv[1:] if not a.startswith("--")]
sub="--sub" in sys.argv
text=[s for s in S if s[0]==".text"][0]
tb=m[text[3]:text[3]+text[4]]
whole=None
targets={}
for a in args:
    pat=re.compile((b"[\x20-\x7e]*" if sub else b"")+re.escape(a.encode())+(b"[\x20-\x7e]*" if sub else b"")+b"\x00")
    for mm in pat.finditer(m):
        off=mm.start()
        if off>0 and m[off-1:off]!=b"\0": 
            continue
        rva=o2r(off)
        if rva is None: continue
        targets[rva]=mm.group()[:-1].decode()
print("strings:",len(targets))
# one pass for rip-rel lea/mov
xr={}
rx=re.compile(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]|[\x48\x4c]\x8b[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", re.S)
for mm in rx.finditer(tb):
    i=mm.start()
    d=struct.unpack_from("<i",tb,i+3)[0]
    t=text[1]+i+7+d
    if t in targets: xr.setdefault(t,[]).append(text[1]+i)
for rva,s in sorted(targets.items()):
    print("0x%x  %r  xrefs=%s"%(rva,s[:90]," ".join("0x%x"%x for x in xr.get(rva,[])[:16])))
