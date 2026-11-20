import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
# rd.py RVA fmt count   (fmt: f float, d double, q qword, i dword)
r=int(sys.argv[1],16); fmt=sys.argv[2]; n=int(sys.argv[3]) if len(sys.argv)>3 else 1
sz=struct.calcsize('<'+fmt); o=d.rva2off(r); d.f.seek(o)
for i in range(n): print(hex(r+i*sz), struct.unpack('<'+fmt, d.f.read(sz))[0])
