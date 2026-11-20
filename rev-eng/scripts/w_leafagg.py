import sys,re,collections
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import avs_grammar as g
d=g.load_dan(sys.argv[1])
out=[];g.index_block(d,0,len(d),"",out,minsize=int(sys.argv[2]))
agg=collections.defaultdict(lambda:[0,0,set()])
for p,off,sz,ty,dep in out:
    if ty in (0x16,) or (ty==0x14 and sz>4 and d[off+4]==0x16): continue
    leaf=re.sub(r"\[\d+\]","[]",p.split("/")[-1])
    if ty==0x14: leaf+="(list)"
    a=agg[leaf];a[0]+=1;a[1]+=sz;a[2].add(g.TYPE_NAMES.get(ty,hex(ty)))
for k,(n,s,t) in sorted(agg.items(),key=lambda x:-x[1][1]): print("%-40s n=%4d total=%10d %s"%(k,n,s,t))
