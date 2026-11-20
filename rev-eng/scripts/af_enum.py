import sys,os,re,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import abi_check as A
vt=json.load(open(os.path.join(A.RAW,"abi_exe_vtables_cache.json")))["vt"]
th=json.load(open(os.path.join(A.RAW,"verify_thunks.json")))
out=[]
for cls in ["Pattern","Utility","Import","Export","Fabric","Gui"]:
    p=os.path.join(A.DEF_SDK,"CLOAPIInterface","include",cls+"APIInterface.h")
    raw=open(p,encoding="utf8",errors="ignore").read()
    names=A.header_virtuals(A.DEF_SDK,cls); slots,n=A.slot_model(names)
    thunk={t[0] for t in th[cls][2]}
    key=[k for k in vt if k.startswith(cls+"API")][0]
    # signatures
    t=A.strip_comments(raw)
    sigs=re.findall(r'virtual\s+([^;{]*?)\b(\w+)\s*\(([^)]*)\)\s*(?:const)?\s*(?:\{[^}]*\}|;)',t,flags=re.S)
    for ret,nm,args in sigs:
        if re.search(r'Grad|Rule|SizeGroup|Size|Rule',nm):
            for s in slots.get(nm,[]):
                e=vt[key]["slots"][s]
                out.append((cls,s,nm,' '.join(ret.split()),' '.join(args.split()),'THUNK' if s in thunk else 'impl',hex(e["rva"])))
seen=set()
for o in sorted(out):
    print('|'.join(map(str,o)))
