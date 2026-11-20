import sys,struct,re,os
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import pdata_fn as P, disasm_fn4 as d
m=d._m; BASE=d.BASE
# import map
pe=struct.unpack_from("<I",m,0x3c)[0]
def rva2off(r):
    for n,va,vsz,rp,rsz,ch in d.SECS:
        if va<=r<va+max(vsz,rsz): return rp+r-va
opt=pe+24; impdir=struct.unpack_from("<I",m,opt+112+8)[0]
IAT={}
p=impdir
while True:
    oft,ts,fc,nm,ft=struct.unpack_from("<IIIII",m,rva2off(p))
    if nm==0: break
    dll=bytes(m[rva2off(nm):rva2off(nm)+64]).split(b"\0")[0].decode()
    i=0
    while True:
        e=struct.unpack_from("<Q",m,rva2off((oft or ft)+8*i))[0]
        if e==0: break
        if e>>63: name="ord%d"%(e&0xffff)
        else:
            o=rva2off(e&0x7fffffff)+2; name=bytes(m[o:o+300]).split(b"\0")[0].decode()
        IAT[ft+8*i]=dll+"!"+name; i+=1
    p+=20
print("IAT entries",len(IAT))
KW=re.compile(r"processEvents|sendPostedEvents|QEventLoop|exec@|QCoreApplication|QApplication|QDialog|QMessageBox|repaint|QWidget@@QEAAXXZ",re.I)
def body(a,b): return d.read_va(BASE+a,b-a)
def scan(lo,hi):
    data=body(lo,hi); E8=[];FF=[];n=0
    i=0
    while i<len(data)-5:
        b=data[i]
        if b==0xe8:
            t=lo+i+5+struct.unpack_from("<i",data,i+1)[0]
            if P.fn(t) and P.fn(t)[0]==t: E8.append((lo+i,t))
        elif b==0xff and data[i+1] in (0x15,) :
            t=lo+i+6+struct.unpack_from("<i",data,i+2)[0]
            if t in IAT: FF.append((lo+i,IAT[t]))
        i+=1
    return E8,FF
def thunk(t):
    x=body(t,t+6)
    if x[:2]==b"\xff\x25":
        r=t+6+struct.unpack_from("<i",x,2)[0]; return IAT.get(r)
root=P.fn(0x607f070); print("Simulate",hex(root[0]),hex(root[1]))
E8,FF=scan(root[0],root[1])
print("E8 targets",len(E8),"IAT direct calls",len(FF))
for a,n in FF: print("  IAT call %x %s"%(a,n))
seen=set()
hits=[]
for a,t in E8:
    th=thunk(t)
    f=P.fn(t)
    print("  %x call %x (fn %x-%x)%s"%(a,t,f[0],f[1]," THUNK->"+th if th else ""))
    if th and KW.search(th): hits.append((t,th))
    if t in seen: continue
    seen.add(t)
    if th: continue
    e2,f2=scan(f[0],f[1])
    for aa,n in f2:
        if KW.search(n): hits.append((aa,n))
    # thunks one level more
    for aa,tt in e2:
        th2=thunk(tt)
        if th2 and KW.search(th2): hits.append((aa,"via %x -> %s"%(tt,th2)))
    print("     callee %x: %d E8 callees, IAT calls: %s"%(t,len(e2),sorted(set(n.split('!')[0]+'!'+n.split('!')[1][:40] for _,n in f2))[:8]))
print("KEYWORD HITS (processEvents/exec/QCoreApplication etc.):",hits)
