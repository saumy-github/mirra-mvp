import sys,struct,os,re,bisect,pickle
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn4 as d, pdata_fn as P
t=[s for s in d.SECS if s[0]==".text"][0]
buf=bytes(d._m[t[3]:t[3]+t[4]])
rev={}
for m in re.finditer(rb"[\xe8\xe9]",buf):
    i=m.start()
    if i+5>len(buf): continue
    tg=t[1]+i+5+struct.unpack_from("<i",buf,i+1)[0]
    e=P.fn(tg)
    if not e or e[0]!=tg: continue
    c=P.fn(t[1]+i)
    if not c or c[0]==tg: continue
    rev.setdefault(tg,set()).add(c[0])
pickle.dump(rev,open(os.path.join(os.path.dirname(__file__),'..','raw','disasm5','revgraph.pkl'),'wb'))
print(len(rev))
