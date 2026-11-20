import sys,struct
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import avs_grammar as g
d=g.load_dan(sys.argv[1])
out=[]
g.index_block(d,0,len(d),"",out,minsize=int(sys.argv[2]))
TN=g.TYPE_NAMES
for p,off,sz,ty,dep in out:
    print("%-95s %10d %s"%(p,sz,TN.get(ty,hex(ty))))
