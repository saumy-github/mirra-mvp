"""Lane Y: scan exe for ascii + utf16 strings matching patterns. python -I scripts/y_strscan.py regex [maxhits]"""
import re,sys,mmap
EXE=r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
pat=sys.argv[1]; mx=int(sys.argv[2]) if len(sys.argv)>2 else 60
d=open(EXE,'rb').read()
import struct
pe=struct.unpack_from('<I',d,0x3c)[0]; n=struct.unpack_from('<H',d,pe+6)[0]; opt=struct.unpack_from('<H',d,pe+20)[0]
secs=[struct.unpack_from('<8sIIII',d,pe+24+opt+i*40) for i in range(n)]
def rva(o):
    for nm,vs,va,rs,rp in secs:
        if rp<=o<rp+rs: return va+o-rp
    return -1
seen=0
for m in re.finditer(rb'[\x20-\x7e]{4,300}',d):
    s=m.group().decode()
    if re.search(pat,s,re.I):
        print('A %08x'%rva(m.start()),s[:200]); seen+=1
        if seen>=mx: break
seen=0
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,300}',d):
    s=m.group().decode('utf-16le')
    if re.search(pat,s,re.I):
        print('W %08x'%rva(m.start()),s[:200]); seen+=1
        if seen>=mx: break
