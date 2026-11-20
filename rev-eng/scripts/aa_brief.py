import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn11 as d
rva=int(sys.argv[1],16); mb=int(sys.argv[2],16)
rows,calls,strs,globs=d.analyse(rva,mb)
for a,mn,op,n in rows:
    keep = mn in("call","cmp","sub","jmp","ret","test","lea","cmovbe","movsd","movss","comiss","comisd","imul","mulss","mulsd","jb","ja") or mn.startswith("j") or n
    if keep: print("%s %-6s %-44s ;%s"%(a[-6:],mn,op,n))
