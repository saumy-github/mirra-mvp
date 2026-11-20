"""k_callers.py - find direct callers (E8/E9 rel32) of RVAs, and 8-byte absolute pointers to them (vtables) in the exe. Usage: k_callers.py rva..."""
import sys,re,struct,mmap
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
f=open(EXE,"rb"); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
pe=struct.unpack_from("<I",m,0x3c)[0]; ns=struct.unpack_from("<H",m,pe+6)[0]; osz=struct.unpack_from("<H",m,pe+20)[0]
S=[]
for i in range(ns):
    o=pe+24+osz+40*i; n=m[o:o+8].rstrip(b"\0").decode(); vsz,va,rsz,rp=struct.unpack_from("<IIII",m,o+8); S.append((n,va,vsz,rp,rsz))
text=[s for s in S if s[0]==".text"][0]; tb=m[text[3]:text[3]+text[4]]
T={int(a,16) for a in sys.argv[1:]}
for mm in re.finditer(rb"[\xe8\xe9]",tb):
    i=mm.start()
    if i+5>len(tb): continue
    t=text[1]+i+5+struct.unpack_from("<i",tb,i+1)[0]
    if t in T: print("%s %x -> %x"%("call" if tb[i]==0xe8 else "jmp ",text[1]+i,t))
for t in T:
    pat=struct.pack("<Q",0x140000000+t)
    for mm in re.finditer(re.escape(pat),m):
        off=mm.start()
        for n,va,vsz,rp,rsz in S:
            if rp<=off<rp+rsz: print("ptr  %s rva %x -> %x"%(n,va+off-rp,t))
