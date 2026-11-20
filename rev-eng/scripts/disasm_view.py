"""disasm_view.py <RVA> - compact view of a function (calls, compares, jumps, resolved data refs) using disasm_fn.analyse()."""
import sys,re
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); sys.argv=sys.argv[:1]+sys.argv[1:]
import disasm_fn as d
rva=int(sys.argv[1],16)
rows,calls,strs,gl=d.analyse(rva,0x2000)
skip=re.compile(r"cmp .*(,0Fh|,1000h|,1Fh)$|70d91f4|70d9780|8237590|^(movups|movaps|movdqu|xorps|nop|int)")
for a,mn,op,n in rows:
    line=f"{mn} {op}"
    if skip.search(line) or skip.search(n): continue
    if mn in("call",) or mn.startswith("j") or mn in("cmp","test","ret","lea","xchg") or n or re.search(r"\b(ecx|edx|r8d|r9d|cl|dl|r8b|r9b),",op) and mn=="mov":
        print(a[-8:],f"{mn:6}",op[:60],"|",n[:150])
