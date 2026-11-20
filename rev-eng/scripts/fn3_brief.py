"""fn3_brief.py RVA [maxbytes] : disasm_fn3 --full output minus shared_ptr refcount noise (lock xadd / vtable release calls)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disasm_fn3 as D
rva = int(sys.argv[1], 16); mb = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1400
rows, calls, strs, globs = D.analyse(rva, mb)
skip = 0
for i, (a, mn, op, n) in enumerate(rows):
    if "xadd" in op or "xadd" in mn or (mn == "lock"):
        continue
    if mn == "call" and op.startswith("qword ptr [r"): continue
    print("%s  %-7s %-38s %s" % (a[-8:], mn, op, ("; " + n) if n else ""))
