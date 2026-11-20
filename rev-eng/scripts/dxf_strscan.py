import re,sys,os,mmap,struct
EXE=r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
f=open(EXE,'rb'); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
pe=struct.unpack_from("<I",m,0x3c)[0]; ns=struct.unpack_from("<H",m,pe+6)[0]; osz=struct.unpack_from("<H",m,pe+20)[0]
secs=[]
for i in range(ns):
    o=pe+24+osz+40*i; n=m[o:o+8].rstrip(b"\0").decode(); vsz,va,rsz,rp=struct.unpack_from("<IIII",m,o+8); secs.append((n,va,vsz,rp,rsz))
def rva(off):
    for n,va,vsz,rp,rsz in secs:
        if rp<=off<rp+rsz: return va+off-rp,n
pats=sys.argv[1:]
for p in pats:
    for mm in re.finditer(p.encode(),m,re.I):
        s=mm.start()
        a=s
        while a>0 and 32<=m[a-1]<127: a-=1
        e=s
        while e<len(m) and 32<=m[e]<127: e+=1
        r=rva(a)
        print(p,hex(r[0]) if r else None,r[1] if r else None,m[a:e][:100].decode())
