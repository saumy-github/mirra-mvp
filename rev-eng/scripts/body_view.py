import sys, re, os
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
NOISE = ('70d91b8','70d91f4','70d9780','8237590','4e10dd0','4e10fb0','1bdd3c0','5ef27e0','1c09700','1c09730','1d68be0','1d68bd0')
rva = int(sys.argv[1],16); size=int(sys.argv[2],16) if len(sys.argv)>2 else 0xA00
lines = d.disasm(rva,size)
start=0
for i,l in enumerate(lines):
    if '4e10fb0' in l: start=i; break
# skip string cleanup: find first 70d91f4 call after start then +6
for i in range(start,len(lines)):
    if '70d91f4' in lines[i]: start=i+1; break
for l in lines[start:]:
    ins=l.split(':',1)[1]
    if re.search(r'lock|xadd', ins): continue
    if any(n in l for n in NOISE): continue
    if re.search(r'\bcall\b|\bj[a-z]+\b|cmp|test|movss|movsd|movaps|mulss|divss|cvt|ret|lea .*\[0000|\[0000|\[r\w+\+[0-9A-F]{3,}h\]|\[r\w+\+[0-9A-F]{3,}h\]', ins):
        print(l)
