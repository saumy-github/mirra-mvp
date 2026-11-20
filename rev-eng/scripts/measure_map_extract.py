"""measure_map_extract.py <start_rva> <size_hex> - extract (key string, index) pairs from an Avatar-ctor-like function.
Key strings live at .rdata 0x89104c0..0x8910870 (table of 'Name_Type' literals). In the init-list code each node is
{std::string key (0x20) ; int idx}, so the first `mov dword ptr [..],imm` after the key literal load is its index."""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import disasm_fn as d
B=0x140000000
# key table
blob=d.read_va(B+0x89104c0,0x8910870-0x89104c0)
keys={}
pos=0
for m in re.finditer(rb"[\x20-\x7e]+\x00",blob):
    keys[0x89104c0+m.start()]=m.group()[:-1].decode()
start=int(sys.argv[1],16); size=int(sys.argv[2],16)
ins=d.parse(d.run_dumpbin(B+start,size))
pend=None; out=[]
for a,mn,op in ins:
    for h in re.findall(r"\b(14[0-9A-F]{7})h?\b|\b([0-9A-F]{16})h?\b",op):
        pass
    m=re.search(r"\[0000000(14[0-9A-F]{7})h\]",op)
    if m and mn in("lea","movups","movsd","movdqa","movzx","mov"):
        v=int(m.group(1),16)-B
        if v in keys and pend is None:
            pend=keys[v]
    m=re.match(r"dword ptr \[rbp\+([0-9A-F]+)h\],([0-9A-F]+)(h?)$",op.strip())
    if mn=="mov" and m and pend:
        out.append((pend,int(m.group(2),16) if m.group(3) else int(m.group(2)),a[-8:])); pend=None
for k,i,a in out: print("%-34s %3d  (0x%x)  @%s"%(k,i,i,a))
print(len(out),"pairs")
