import sys,mmap,struct,re
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import disasm_fn as d
disp=bytes.fromhex(sys.argv[1])
t=[s for s in d.SECS if s[0]==".text"][0]
data=d._m[t[3]:t[3]+t[4]]
for m in re.finditer(re.escape(disp),data):
    o=m.start(); va=d.BASE+t[1]+o
    print(hex(va), data[max(0,o-3):o+8].hex())
