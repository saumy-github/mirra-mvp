import sys, re, os
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
rva=int(sys.argv[1],16); size=int(sys.argv[2],16) if len(sys.argv)>2 else 0x1000
lines=d.disasm(rva,size)
st=0
for i,l in enumerate(lines):
    if '4e10fb0' in l: st=i; break
NOISE=('70d91b8','70d91f4','70d9780','8237590','4e10dd0','4e10fb0','1bdd3c0','5ef27e0','1c09700','1c09730','1d68be0','1d68bd0','1c0f060','1c0f420','1c0f560')
n=0
for l in lines[st:]:
    ins=l.split(':',1)[1]
    if re.search(r'lock|xadd', ins): continue
    if any(x in l for x in NOISE): continue
    if re.search(r'call +(?!qword ptr \[(rax|rdx|rcx|rbx|rdi)(\+8)?\])', ins) or re.search(r'\] [AW]"', l) or re.search(r'\bcmp +(e|r)\w+, ?[0-9A-Fa-f]+h?$',ins) and not re.search(r'1000h|1Fh|, ?1$|0Fh',ins) or 'ret' in ins[:12] or re.search(r'mul|div|sqrt|cvt',ins) or re.search(r'call +qword ptr \[r\w+\+[0-9A-F]{2,}h\]',ins):
        print(l)
