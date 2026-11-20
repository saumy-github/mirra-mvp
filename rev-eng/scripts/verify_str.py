"""verify_str.py VA... : print string/double/float at exe VAs (stdlib). Lane M."""
import struct, sys, re
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
d = open(EXE,'rb').read(); pe = struct.unpack_from('<I', d, 0x3c)[0]
n = struct.unpack_from('<H', d, pe+6)[0]; opt = struct.unpack_from('<H', d, pe+20)[0]
secs=[struct.unpack_from('<8sIIII', d, pe+24+opt+i*40) for i in range(n)]
def off(r):
    for nm,vs,va,rs,rp in secs:
        if va<=r<va+max(vs,rs): return rp+r-va
for a in sys.argv[1:]:
    v=int(a,16); o=off(v-0x140000000)
    b=d[o:o+32]
    m=re.match(rb'[\x20-\x7e]{1,40}',b)
    print(a, b[:16].hex(), 'str=%r'%(m.group().decode() if m else None), 'f32=%r f64=%r'%(struct.unpack('<f',b[:4])[0], struct.unpack('<d',b[:8])[0]))
