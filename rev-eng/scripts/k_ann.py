"""k_ann.py - annotate a raw dumpbin listing (lane K): python -I k_ann.py <dump.txt> -> stdout with string/call notes"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn as d
for ln in open(sys.argv[1]):
    m=d.LINE.match(ln)
    if not m: continue
    a,mn,op=m.groups(); note=""
    for h in re.findall(r"\b([0-9A-F]{16})h?\b",op):
        v=int(h,16)
        if not (d.BASE<=v<d.BASE+0x10000000): continue
        if mn=="call" and op.strip()==h: note="call 0x%x"%(v-d.BASE)
        elif mn.startswith("j"): continue
        else:
            s=d.cstr(v)
            note="%x %s"%(v-d.BASE,repr(s) if s else "")
    print("%s %-6s %-44s ; %s"%(a[-8:],mn,op,note))
