import sys,struct,os,bisect
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn4 as d
p=[s for s in d.SECS if s[0]==".pdata"][0]
b=d.read_va(d.BASE+p[1],p[2])
ent=[struct.unpack_from("<III",b,i) for i in range(0,len(b)-11,12)]
starts=[e[0] for e in ent]
def fn(rva):
    i=bisect.bisect_right(starts,rva)-1
    return ent[i] if i>=0 and ent[i][0]<=rva<ent[i][1] else None
if __name__=="__main__":
    for a in sys.argv[1:]:
        e=fn(int(a,16)); print(a, e and "%x-%x size %x"%(e[0],e[1],e[1]-e[0]))
