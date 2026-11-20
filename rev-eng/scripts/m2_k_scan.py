import sys,struct,mmap,os
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import pdata_fn as P, disasm_fn4 as d
def calls(a,b):
    out=[]
    data=d.read_va(d.BASE+a,b-a)
    for i in range(len(data)-4):
        if data[i] in (0xe8,0xe9):
            t=a+i+5+struct.unpack_from("<i",data,i+1)[0]
            if 0x1000<=t<0x8000000 and P.fn(t): out.append((a+i,data[i],t))
    return out
def fnr(x):
    e=P.fn(x); return e
C=[0x50a6a64,0x50c3ad6,0x50ee542,0x50fd450,0x50fda06,0x55fa13c,0x584b13e,0x62079b7]
cf={}
for c in C:
    e=P.fn(c); cf[c]=(e[0],e[1]); print("caller %x in fn %x-%x"%(c,e[0],e[1]))
for name,a in (("loader",0x50f5c00),("wrapper510cd70",0x510cd70)):
    e=P.fn(a); lo,hi=e[0],e[1]; print(name,hex(lo),hex(hi))
    cs=calls(lo,hi)
    tg={t for _,_,t in cs}
    print(" total E8/E9 w/ valid fn target (heuristic, may include false positives):",len(cs),"; direct 511a1b0:",0x511a1b0 in tg)
    # first-level callee fns that contain a caller of 511a1b0
    for t in sorted(tg):
        e2=P.fn(t)
        for c,(l,h) in cf.items():
            if e2 and e2[0]==l: print("  first-level callee %x is fn containing driver caller %x"%(t,c))
    # first-level callees whose own body directly calls 511a1b0 (any, including thunks)
    n=0
    for t in sorted(tg):
        e2=P.fn(t)
        if e2 and e2[0]==t:
            if 0x511a1b0 in {x for _,_,x in calls(e2[0],e2[1])}: print("  callee %x directly calls driver"%t); n+=1
    print(" callees directly calling driver:",n, " distinct callees:",len(tg))
