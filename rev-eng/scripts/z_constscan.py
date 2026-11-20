import sys,os,struct,bisect
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import pdata_fn as P, disasm_fn10 as d
t=[s for s in d.SECS if s[0]==".text"][0]
b=d.read_va(d.BASE+t[1],t[2])
consts={'md5_init':0x67452301,'md5_T1':0xd76aa478,'md5_T2':0xe8c7b756,'sha256_K0':0x428a2f98,'sha256_H0':0x6a09e667,'sha1_K':0x5a827999,'sha1_H4':0xc3d2e1f0,'crc32_poly':0xedb88320,'crc32_t1':0x77073096}
for n,c in consts.items():
    pat=struct.pack('<I',c); i=0; seen={}
    while True:
        i=b.find(pat,i)
        if i<0: break
        rva=t[1]+i; e=P.fn(rva)
        seen.setdefault(e[0] if e else None,0); seen[e[0] if e else None]+=1; i+=1
    print(n,[(hex(k) if k else None,v) for k,v in sorted(seen.items(),key=lambda x:(x[0] is None,x[0] or 0))][:25])
# also rdata
for s in d.SECS:
    if s[0] in('.rdata','.data'):
        bb=d.read_va(d.BASE+s[1],s[2])
        for n,c in consts.items():
            pat=struct.pack('<I',c); i=bb.find(pat)
            cnt=bb.count(pat)
            if cnt: print(s[0],n,'count',cnt,'first rva',hex(s[1]+i))
