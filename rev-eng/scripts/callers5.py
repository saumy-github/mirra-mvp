import sys,struct,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn4 as d, pdata_fn as P
t=[s for s in d.SECS if s[0]==".text"][0]
buf=bytes(d._m[t[3]:t[3]+t[4]])
want={int(a,16) for a in sys.argv[1:]}
res={w:[] for w in want}
for m in re.finditer(rb"[\xe8\xe9]",buf):
    i=m.start()
    if i+5>len(buf): continue
    tgt=t[1]+i+5+struct.unpack_from("<i",buf,i+1)[0]
    if tgt in want: res[tgt].append(t[1]+i)
for w,l in res.items():
    print(hex(w),[(hex(x),(lambda e:hex(e[0]) if e else None)(P.fn(x))) for x in l][:25])
