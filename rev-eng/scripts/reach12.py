"""reach9.py - static direct-call reachability (E8/E9 rel32 only; virtual calls NOT followed) from API roots to modal-dialog sinks.
Usage: python -I reach9.py <maxdepth> <root_rva_hex>... """
import sys,os,struct,bisect,importlib.util
spec=importlib.util.spec_from_file_location('d',os.path.join(os.path.dirname(os.path.abspath(__file__)),'disasm_fn12.py'))
d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
p=[s for s in d.SECS if s[0]==".pdata"][0]
b=d.read_va(d.BASE+p[1],p[2]); ent=[struct.unpack_from("<III",b,i) for i in range(0,len(b)-11,12)]; starts=[e[0] for e in ent]
tx=[s for s in d.SECS if s[0]==".text"][0]; code=d.read_va(d.BASE+tx[1],tx[2])
def callees(f):
    i=bisect.bisect_right(starts,f)-1
    if i<0 or ent[i][0]!=f: 
        # not a pdata start: scan 0x400 bytes
        lo,hi=f,f+0x200
    else: lo,hi=ent[i][0],ent[i][1]
    out=set()
    for a in range(lo-tx[1],hi-tx[1]-4):
        if code[a] in (0xE8,0xE9):
            t=tx[1]+a+5+struct.unpack_from("<i",code,a+1)[0]
            if tx[1]<=t<tx[1]+tx[2]: out.add(t)
    return out
SINKS={0x4b786c0:"QuestionBox2 vtbl+0x10 (btn-set code)",0x4b78600:"MsgBox(info) vtbl+0x20",0x4b78650:"QuestionBox vtbl+8",0x4b6be20:"DisplayMessageBox helper",0x4b7bd50:"Assert/E11000 error box",0x4b77c50:"GPU-err box?",0x1db4010:"'File not saved. Do you want to save?'"}
maxd=int(sys.argv[1])
for r in sys.argv[2:]:
    root=int(r,16); seen={root:None}; fr=[root]; found={}
    for dep in range(maxd):
        nf=[]
        for f in fr:
            for c in callees(f):
                if c in seen: continue
                seen[c]=f; nf.append(c)
                if c in SINKS and c not in found: found[c]=dep+1
        fr=nf
    print("ROOT %s visited=%d"%(r,len(seen)))
    for s,dep in found.items():
        path=[];x=s
        while x is not None: path.append(hex(x)); x=seen[x]
        print("   SINK %x (%s) depth %d: %s"%(s,SINKS[s],dep," <- ".join(path)))
    if not found: print("   no sink within depth",maxd)
