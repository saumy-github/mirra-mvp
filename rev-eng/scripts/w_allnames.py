import sys,re,collections
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import avs_grammar as g
d=g.load_dan(sys.argv[1])
out=[];g.index_block(d,0,len(d),"",out,minsize=0)
agg=collections.OrderedDict()
for p,off,sz,ty,dep in out:
    leaf=re.sub(r"\[\d+\]","[]",p.split("/")[-1])
    a=agg.setdefault(leaf,[0,0,g.TYPE_NAMES.get(ty,hex(ty))]);a[0]+=1;a[1]+=sz
for k,(n,s,t) in agg.items(): print("%-36s n=%5d total=%10d %s"%(k,n,s,t))
