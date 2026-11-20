import json,re,sys
H=r"C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.336_Win\CLOAPIInterface\include"
def hdr(cls):
    out=[]
    for l in open(H+"\\"+cls+"Interface.h",encoding='utf8',errors='ignore'):
        mm=re.match(r'\s*virtual\s+.*?(\w+)\s*\(',l)
        if mm: out.append(mm.group(1))
    return out
def named(cls):
    d=json.load(open(r"C:\D-drive-data\mirra-mvp\rev-eng\raw\vtable_app.json"))[cls+'Interface']
    res={}
    for s in d:
        t=s['demangled'] or (s['candidates'][0] if s['candidates'] else None)
        if t:
            m=re.search(r'CLOAPI::\w+::(\w+)\(',t)
            if m: res.setdefault(m.group(1),[]).append(s['slot'])
    return res
if __name__=='__main__':
    cls,a,b=sys.argv[1],sys.argv[2],sys.argv[3]
    h=hdr(cls); n=named(cls)
    i=h.index(a); j=h.index(b)
    for x in h[i:j+1]: print(x,n.get(x))
