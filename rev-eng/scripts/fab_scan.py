import json, sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
v=json.load(open(os.path.join(os.path.dirname(__file__),'..','raw','exe_vtables.json')))
k=sys.argv[1]; lo=int(sys.argv[2]); hi=int(sys.argv[3]); pat=sys.argv[4] if len(sys.argv)>4 else ''
def full(va):
    o=d.rva2off(va-d.BASE); d.f.seek(o); b=d.f.read(400); return b.split(b'\0')[0].decode('latin1')
for s in v[k]['slots'][lo:hi]:
    if s['bytes'].startswith('ff25'): print(s['slot'],'THUNK'); continue
    nm=''
    for l in d.disasm(s['rva'],0x300):
        m=re.search(r'\[0000000(14[0-9A-F]{7})h\] ; \[\.rdata \w+\] A"[^"]*(?:Marvelous|__cdecl)',l)
        if m: nm=full(int(m.group(1),16)); break
    nm=nm.replace('class std::basic_string<char,struct std::char_traits<char>,class std::allocator<char> >','string').replace('class std::basic_string<wchar_t,struct std::char_traits<wchar_t>,class std::allocator<wchar_t> >','wstring')
    if pat in nm: print(s['slot'],hex(s['rva']),nm[:200])
