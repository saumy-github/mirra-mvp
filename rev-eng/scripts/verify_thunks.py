"""Lane M: independent thunk scan. Reads exe directly (stdlib). python -I scripts/verify_thunks.py"""
import struct, re, sys, json
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
d = open(EXE,'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
n = struct.unpack_from('<H', d, pe+6)[0]; opt = struct.unpack_from('<H', d, pe+20)[0]
secs=[]
for i in range(n):
    nm,vs,va,rs,rp = struct.unpack_from('<8sIIII', d, pe+24+opt+i*40)
    secs.append((nm.rstrip(b'\0').decode(),va,vs,rp,rs))
def off(r):
    for nm,va,vs,rp,rs in secs:
        if va<=r<va+max(vs,rs): return rp+r-va
def rd(r,k): o=off(r); return d[o:o+k]
oh = pe+24
impdir = struct.unpack_from('<I', d, oh+112+8)[0]
iat = {}
p=impdir
while True:
    oft,ts,fc,nm,ft = struct.unpack('<IIIII', rd(p,20))
    if nm==0: break
    dll = rd(nm,64).split(b'\0')[0].decode()
    i=0
    while True:
        e = struct.unpack('<Q', rd((oft or ft)+8*i,8))[0]
        if e==0: break
        nmx = ('ord%d'%(e&0xffff)) if e>>63 else rd((e&0x7fffffff)+2,300).split(b'\0')[0].decode()
        iat[ft+8*i]=(dll,nmx); i+=1
    p+=20
VT = {'Export':0x89687b8,'Utility':0x8968ba0,'Fabric':0x89770d8,'Gui':0x89866a0,'Import':0x8989348,'Pattern':0x898ba50,'Rest':0x899ae98}
def undname(m):
    return m
out={}
for cls,vt in VT.items():
    # RTTI check: COL at vt-8
    col = struct.unpack('<Q', rd(vt-8,8))[0]-0x140000000
    tdrva = struct.unpack_from('<I', rd(col,16), 12)[0]
    tname = rd(tdrva+16,80).split(b'\0')[0].decode()
    slots=[]; k=0
    while True:
        v = struct.unpack('<Q', rd(vt+8*k,8))[0]
        # stop when value is not code pointer in .text
        r = v-0x140000000
        if not (0<=r<0x9000000) or off(r) is None or [s for s in secs if s[0]=='.text' and s[1]<=r<s[1]+s[2]]==[]: break
        slots.append(r); k+=1
    th=[]
    for i,r in enumerate(slots):
        b = rd(r,6)
        if b[:2]==b'\xff\x25':
            disp = struct.unpack('<i', b[2:6])[0]
            tgt = r+6+disp
            th.append((i,r,tgt,iat.get(tgt)))
    out[cls]=(tname,len(slots),th)
    print(cls,tname,'slots',len(slots),'thunks',len(th))
    for i,r,t,nm in th: print('  slot %d rva %#x iat %#x %s'%(i,r,t,nm))
json.dump({c:[v[0],v[1],[[i,hex(r),hex(t),nm] for i,r,t,nm in v[2]]] for c,v in out.items()}, open(r'C:\D-drive-data\mirra-mvp\rev-eng\raw\verify_thunks.json','w'), indent=1)
