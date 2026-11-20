import sys
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import disasm_fn as d
a=int(sys.argv[1],16); n=int(sys.argv[2],16)
for x in d.parse(d.run_dumpbin(a,n)): print(x[0][-9:],x[1],x[2])
