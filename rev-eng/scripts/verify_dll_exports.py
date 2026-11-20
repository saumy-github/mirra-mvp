"""Lane M: map thunk names to export RVAs in app CLOAPIInterface.dll and show first stub bytes."""
import struct, json
P = r"C:\Program Files\CLO Standalone OnlineAuth\CLOAPIInterface.dll"
d = open(P,'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
n = struct.unpack_from('<H', d, pe+6)[0]; opt = struct.unpack_from('<H', d, pe+20)[0]
secs=[struct.unpack_from('<8sIIII', d, pe+24+opt+i*40) for i in range(n)]
def off(r):
    for nm,vs,va,rs,rp in secs:
        if va<=r<va+max(vs,rs): return rp+r-va
def cstr(r):
    o=off(r); return d[o:d.index(b'\0',o)].decode()
exp = struct.unpack_from('<I', d, pe+24+112)[0]
eo=off(exp)
nf,nn,aof,aon,aoo = struct.unpack_from('<IIIII', d, eo+20)
byname={}
for i in range(nn):
    nm = cstr(struct.unpack_from('<I', d, off(aon)+4*i)[0])
    ordn = struct.unpack_from('<H', d, off(aoo)+2*i)[0]
    rva = struct.unpack_from('<I', d, off(aof)+4*ordn)[0]
    byname[nm]=rva
print('exports',nn)
t = json.load(open(r'C:\D-drive-data\mirra-mvp\rev-eng\raw\verify_thunks.json'))
rows=[]
for cls in ('Pattern','Utility'):
    for i,r,tg,nm in t[cls][2]:
        rva = byname.get(nm[1])
        b = d[off(rva):off(rva)+12].hex() if rva else None
        rows.append((cls,i,nm[1].split("@")[0][1:],rva,b))
        print(cls,i,nm[1].split('@')[0][1:],hex(rva) if rva else None,b)
# group stub byte patterns
from collections import Counter
print(Counter(r[4] for r in rows))
print('--- follow jmp')
c=Counter()
for cls,i,nm,rva,b in rows:
    o=off(rva); rel=struct.unpack_from('<i',d,o+1)[0]; tg=rva+5+rel
    body=d[off(tg):off(tg)+10].hex(); c[body]+=1
    print(cls,i,nm,hex(tg),body)
print(c)
