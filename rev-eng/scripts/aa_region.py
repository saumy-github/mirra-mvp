import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn11 as d, pdata_fn as p
txt=open(os.path.join(d.CACHE,"..","disasm5","4086000_1d000.txt")).read()
ins=d.parse(txt)
import collections
fns=collections.OrderedDict()
for a,mn,op in ins:
    r=int(a,16)-d.BASE
    e=p.fn(r)
    if e: fns.setdefault(e[0],[]).append((a,mn,op))
for s,l in fns.items():
    strs=[];calls=set()
    for a,mn,op in l:
        for h in re.findall(r"\b([0-9A-F]{16})h?\b",op):
            v=int(h,16)
            if not (d.BASE<=v<d.BASE+0x10000000): continue
            if mn=="call": calls.add(v-d.BASE); continue
            if mn.startswith("j"): continue
            st=d.cstr(v)
            if st: strs.append(st[2:40])
    print("%x size %x n=%d strs=%s calls=%s"%(s,p.fn(s)[1]-s,len(l),strs[:12],sorted(calls)[:14]))
