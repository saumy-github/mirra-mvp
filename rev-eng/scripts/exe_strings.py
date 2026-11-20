"""Scan the CLO exe for ASCII/UTF-16 strings matching plugin-API related patterns (read-only)."""
import re, sys, mmap
p = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
pats = [rb"DoFunction\w*", rb"GetActionName", rb"GetObjectNameTreeToAddAction", rb"GetPositionIndexToAddAction", rb"CLOAPIInterface\w*",
        rb"(?:Set|Get)(?:Utility|Pattern|Fabric|Import|Export|Gui|Rest)API", rb"[\w\/:.-]*[Pp]lugin[\w\/:.-]*\.dll", rb"CLOAPI::\w+",
        rb"ExportGLTF\w*", rb"ExportGLB\w*", rb"ImportAvatarMeasurement\w*", rb"AddSeamlinePairGroup\w*"]
out = {}
with open(p, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
    for pat in pats:
        seen = {}
        for mt in re.finditer(pat, m):
            s = mt.group().decode('latin1')
            if len(s) < 200: seen.setdefault(s, mt.start())
        out[pat.decode()] = seen
for k, v in out.items():
    print(f"## {k}  ({len(v)} unique)")
    for s, o in sorted(v.items())[:40]: print(f"  0x{o:08X}  {s}")
