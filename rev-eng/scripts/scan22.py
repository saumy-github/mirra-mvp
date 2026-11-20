import sys,struct,re
sys.path.insert(0,'.')
import disasm_fn22 as d
m=d._m
text=[s for s in d.SECS if s[0]=='.text'][0]
name,va,vsz,rptr,rsz,ch=text
data=bytes(m[rptr:rptr+rsz])
def callers(target):
    out=[]
    for i in re.finditer(b'\xe8',data):
        p=i.start()
        if p+5>len(data):continue
        rel=struct.unpack_from('<i',data,p+1)[0]
        if va+p+5+rel==target: out.append(va+p)
    return out
def rip_refs(target):
    out=[]
    # lea/mov with modrm rip-rel: find 4-byte disp where next-ip+disp==target; scan all positions with opcode check
    for p in range(0,len(data)-4):
        rel=struct.unpack_from('<i',data,p)[0]
        # instruction end could be p+4 (+imm0..) assume p+4
        if va+p+4+rel==target and data[p-1] in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d) and data[p-2] in (0x8d,0x8b,0x89,0x3b,0x39,0x83,0x81):
            out.append(va+p-3)
    return out
if __name__=='__main__':
    for a in sys.argv[1:]:
        t=int(a,16)
        if sys.argv[0] and a.startswith('c'): pass
    print('callers 3bcdbd0',[hex(x) for x in callers(0x3bcdbd0)])
    for t in (0x884cb30,0x884c128,0x884c100):
        print(hex(t),[hex(x) for x in rip_refs(t)])
