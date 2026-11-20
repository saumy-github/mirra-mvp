import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d, re
# slice.py fnRVA size lo hi  [filter noise]
rva=int(sys.argv[1],16); size=int(sys.argv[2],16); lo=int(sys.argv[3],16); hi=int(sys.argv[4],16)
for l in d.disasm(rva,size):
    a=int(l.split(':')[0],16)
    if lo<=a<=hi and not re.search(r'lock|\bnop\b|xadd', l): print(l)
