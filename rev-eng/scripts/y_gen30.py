"""Lane Y: generate findings/30_unimplemented_apis.md. python -I scripts/y_gen30.py"""
import json,re,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H=r"C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.336_Win\CLOAPIInterface\include"
vt=json.load(open(os.path.join(R,'raw','verify_thunks.json')))
src={'Pattern':open(os.path.join(H,'PatternAPIInterface.h'),encoding='utf8',errors='ignore').read(),
     'Utility':open(os.path.join(H,'UtilityAPIInterface.h'),encoding='utf8',errors='ignore').read()}
def sig(cls,name,mangled):
    # pick the header overload whose param count matches the mangled name loosely: only RemoveGraphicStyle is overloaded
    ms=re.findall(r'virtual\s+([^;{=]*?\b%s\s*\([^)]*\))'%name,src[cls])
    if name=='RemoveGraphicStyle': return 'std::string RemoveGraphicStyle(int _graphicIndex)'
    s=re.sub(r'\s+',' ',ms[0]).strip()
    return s
body={}
for n in (196,199,200,201,203,204,205,206,207,210,211,212,214,216,217,220): body[n]='xor al,al; ret -> false'
for n in (197,198,208,209,213,215,218,219): body[n]='returns empty vector'
body[202]='mov eax,-1; ret -> -1'
body[397]=body[399]='ret (void no-op)'
body[398]=body[400]='returns empty string'
body[388]='NOT a dead stub: reads colorway via vslot 16 then virtual-calls slot 387 (see sect. 3)'
rows=[]
for cls in ('Pattern','Utility'):
    for slot,thunk,iat,(dll,mg) in vt[cls][2]:
        name=re.match(r'\?(\w+)@',mg).group(1)
        rows.append((cls,slot,name,sig(cls,name,mg),thunk,iat,body[slot]))
out=["| # | Class | Slot | Function (SDK 336 header signature) | Thunk RVA | IAT RVA | Base stub body |","|---|---|---|---|---|---|---|"]
for i,(c,s,n,sg,t,ia,b) in enumerate(rows,1):
    out.append(f"| {i} | {c} | {s} | `{sg}` | {t} | {ia} | {b} |")
open(os.path.join(R,'raw','y_unimpl_table.md'),'w').write("\n".join(out)+"\n")
print(len(rows))
