"""xref_dialog9.py - find dialog-text strings in the exe and the functions that reference them (lea rip-rel scan).
Usage: python -I xref_dialog9.py <regex> [maxhits]"""
import sys,os,re,struct,bisect,importlib.util
spec=importlib.util.spec_from_file_location('d',os.path.join(os.path.dirname(os.path.abspath(__file__)),'disasm_fn9.py'))
d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
pat=re.compile(sys.argv[1].encode(),re.I)
mx=int(sys.argv[2]) if len(sys.argv)>2 else 60
p=[s for s in d.SECS if s[0]==".pdata"][0]
b=d.read_va(d.BASE+p[1],p[2]); ent=[struct.unpack_from("<III",b,i) for i in range(0,len(b)-11,12)]; starts=[e[0] for e in ent]
def fn(rva):
    i=bisect.bisect_right(starts,rva)-1
    return ent[i][0] if i>=0 and ent[i][0]<=rva<ent[i][1] else None
rd=[s for s in d.SECS if s[0]==".rdata"][0]
data=d.read_va(d.BASE+rd[1],rd[2])
hits=[]
for m in re.finditer(rb"[\x20-\x7e]{12,400}\x00",data):
    if pat.search(m.group()): hits.append((rd[1]+m.start(),m.group()[:-1].decode()))
tx=[s for s in d.SECS if s[0]==".text"][0]
code=d.read_va(d.BASE+tx[1],tx[2])
targets={h[0]:h[1] for h in hits[:mx]}
found={}
for i in range(len(code)-7):
    if code[i] in (0x48,0x4c) and code[i+1]==0x8d and (code[i+2]&0xC7)==0x05:
        rel=struct.unpack_from("<i",code,i+3)[0]
        t=tx[1]+i+7+rel
        if t in targets: found.setdefault(t,[]).append(tx[1]+i)
for t,s in targets.items():
    print("%x %r"%(t,s[:150]))
    for a in found.get(t,[]): print("     ref @%x fn %s"%(a,hex(fn(a)) if fn(a) else '?'))
