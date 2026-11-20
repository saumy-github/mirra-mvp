"""Lane M: recompute MSVC x64 layout of ImportExportOption from the header text (stdlib)."""
import re, sys
SZ = {'bool':(1,1),'int':(4,4),'float':(4,4),'unsigned int':(4,4),'WELD_TYPE':(4,4),'TEXTURE_SAVE_METHOD':(4,4),'ALEMBIC_TYPE':(4,4),'std::string':(32,8)}
def layout(path):
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    s = next(i for i,l in enumerate(lines) if 'class ImportExportOption' in l)
    e = next(i for i in range(s,len(lines)) if re.match(r'\s*ImportExportOption\(\)', lines[i]))
    off = 8; mx = 8; res=[]  # vptr
    for l in lines[s:e]:
        l = l.split('//')[0].strip()
        m = re.match(r'(?:EXPORT_PYTHON\s+)?(std::vector<[^>]+>|std::string|unsigned int|\w+)\s+(\w+)\s*;', l)
        if not m: continue
        t, n = m.groups()
        sz,al = (24,8) if t.startswith('std::vector') else SZ[t]
        off = (off+al-1)//al*al; res.append((hex(off),t,n,sz)); off += sz; mx=max(mx,al)
    tot = (off+mx-1)//mx*mx
    return res, off, tot
for v in ('224','336'):
    p = r'C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.%s_Win\CLOAPIInterface\include\CloApiData.h' % v
    res, end, tot = layout(p)
    print('SDK',v,'fields',len(res),'end',hex(end),'sizeof',tot,hex(tot))
    for r in res[-8:]: print('  ',r)
