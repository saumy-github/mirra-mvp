import sys, re, os
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
NOISE = ('70d91b8','70d91f4','70d9780','8237590','4e10dd0','4e10fb0','1bdd3c0','5ef27e0')
rva = int(sys.argv[1],16); size=int(sys.argv[2],16) if len(sys.argv)>2 else 0x800
for l in d.disasm(rva,size):
    if re.search(r'\bcall\b|\bj\w+\s', l) or '"' in l or 'ret' in l.split(':',1)[1][:5]:
        if any(n in l for n in NOISE): continue
        if re.search(r'movups|movsd', l) and 'Marvelous::' in l: 
            m=re.search(r'A"(.*)"',l); print(l.split(':')[0]+': STR', m.group(1)[:80] if m else ''); continue
        if re.search(r'movups|movsd', l): continue
        print(l)
