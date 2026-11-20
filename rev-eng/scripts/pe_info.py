"""Minimal PE section/import summary (stdlib only)."""
import struct, sys
def info(p):
    d = open(p,'rb').read(); pe = struct.unpack_from('<I', d, 0x3c)[0]
    n = struct.unpack_from('<H', d, pe+6)[0]; opt = struct.unpack_from('<H', d, pe+20)[0]
    ts = struct.unpack_from('<I', d, pe+8)[0]
    s = pe+24+opt; out=[]
    for i in range(n):
        nm, vs, va, rs, rp = struct.unpack_from('<8sIIII', d, s+i*40)
        out.append((nm.rstrip(b'\0').decode(), vs, rs))
    return len(d), ts, out
for p in sys.argv[1:]:
    print(p); l, ts, secs = info(p); print(' size', l, 'timestamp', ts, secs)
