import sys,re
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import disasm_fn as d
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
b=d.read_va(d.BASE+lo,hi-lo)
for m in re.finditer(rb"[\x20-\x7e]{3,}",b):
    print(hex(lo+m.start()),m.group().decode()[:160])
