"""k_xref2.py - broad rip-relative xref finder (any opcode with modrm mod=00 rm=101) for given .rdata RVAs, lane K.
Usage: k_xref2.py 0xRVA...   Prints text RVA of the modrm byte -1.. and 3 preceding bytes (hex). Includes SSE inline-string loads."""
import sys,re,struct,mmap
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
f=open(EXE,"rb"); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
pe=struct.unpack_from("<I",m,0x3c)[0]; ns=struct.unpack_from("<H",m,pe+6)[0]; osz=struct.unpack_from("<H",m,pe+20)[0]
for i in range(ns):
    o=pe+24+osz+40*i; n=m[o:o+8].rstrip(b"\0").decode(); vsz,va,rsz,rp=struct.unpack_from("<IIII",m,o+8)
    if n==".text": tva,trp,trs=va,rp,rsz
tb=m[trp:trp+trs]
T=set(int(a,16) for a in sys.argv[1:])
# window of tolerance: strings may be addressed at start or at +8/+16 for 16-byte chunked copies
W={}
for t in T:
    for k in range(0,0x40,8): W[t+k]=(t,k)
rx=re.compile(rb"[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]",re.S)
for mm in rx.finditer(tb):
    p=mm.start()
    if p+5>len(tb): continue
    d=struct.unpack_from("<i",tb,p+1)[0]
    # next ip depends on trailing imm (0..4 bytes): try 0 and 1,4
    for imm in (0,1,4):
        t=tva+p+5+imm+d
        if t in W:
            base,k=W[t]
            print("str 0x%x+%d  insn_bytes=%s at 0x%x"%(base,k,tb[max(0,p-3):p+1].hex(),tva+p-3))
