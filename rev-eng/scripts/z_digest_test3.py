import sys,hashlib,struct,itertools
SALT=b"scrampling&$%!@#mvfileheader"
def tryfile(p):
    b=open(p,'rb').read()
    zo=struct.unpack_from('<I',b,0x20)[0]
    dig=b[zo-64:zo].decode()
    # header offset table @0x89 : find pairs
    regions={}
    # candidate regions: json blob = from last PNG end to zo-68
    import re
    last=[m.end() for m in re.finditer(b'IEND\xaeB`\x82',b[:zo])][-1]
    regions['after_last_png']=b[last:zo-68]
    regions['after_last_png_to_zo-4']=b[last:zo-4]
    j=b.find(b'{',last)
    regions['from_first_brace']=b[j:zo-68]
    # json exact: last '}' in region
    e=b.rfind(b'}',0,zo-68)
    regions['json_all_braces']=b[j:e+1]
    k=b.find(b'{\n "',last)
    regions['json_main']=b[k:e+1]
    regions['hdr_0_to_0x105']=b[:0x105]
    regions['hdr_0_to_zo-68']=b[:zo-68]
    regions['hdr_0x40_to_zo-68']=b[0x40:zo-68]
    regions['png0']=b[struct.unpack_from('<I',b,0x18)[0]:][:struct.unpack_from('<I',b,0x1c)[0]]
    n=0
    for name,r in regions.items():
        for pre in (b'',):
            for variant,data in (('r',r),('r+salt',r+SALT),('salt+r',SALT+r),('r+salt+nul',r+SALT+b'\0'),('r_utf16',r.decode('latin1').encode('utf-16le')),('r+salt16',r+SALT.decode().encode('utf-16le')),
                                  ('r|rstrip',r.rstrip(b'\0\n')+SALT)):
                for a in ('sha256','sha3_256','blake2s'):
                    for hh in (1,0):
                        h=hashlib.new(a,data).hexdigest()
                        if dig in (h,h.upper()): print('HIT',p,name,variant,a); n+=1
    print(p.split('/')[-1],'hits',n,'dig',dig[:16],'regions',{k:len(v) for k,v in regions.items()})
for p in sys.argv[1:]: tryfile(p)
