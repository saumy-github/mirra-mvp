"""xref_rip.py <RVA>... - find `lea reg,[rip+disp]` references from .text to given RVAs (static scan; lea only)."""
import sys,struct,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn as d
text=[s for s in d.SECS if s[0]==".text"][0]
buf=bytes(d._m[text[3]:text[3]+text[4]])
want={int(a,16):[] for a in sys.argv[1:]}
for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]",buf):
    i=m.start()
    if i+7>len(buf): continue
    disp=struct.unpack_from("<i",buf,i+3)[0]
    t=text[1]+i+7+disp
    if t in want: want[t].append(hex(text[1]+i))
for t,h in want.items(): print(hex(t),h)
