import sys,hashlib,zipfile,io,struct
sys.path.insert(0,'rev-eng/scripts')
from z_digest_test import parse
def cands(b,h):
    zo=h['zo']; z=b[zo:]
    yield 'zip',z
    yield 'zip_exact',b[zo:zo+h['zl']]
    yield 'whole',b
    yield 'prefix',b[:zo]
    yield 'prefix_nodigest',b[:zo-68]
    yield 'png',b[h['po']:h['po']+h['pl']]
    yield 'hdr0x40',b[:0x40]
    yield 'afterhdr_to_zip',b[0x40:zo-68]
    yield 'zip_noeocd',z
    try:
        zf=zipfile.ZipFile(io.BytesIO(z))
        for i in zf.infolist():
            yield 'm:'+i.filename,zf.read(i)
        yield 'concat_members',b''.join(zf.read(i) for i in zf.infolist())
        yield 'dan',b''.join(zf.read(i) for i in zf.infolist() if i.filename.endswith('.dan'))
        yield 'names',''.join(i.filename for i in zf.infolist()).encode()
    except Exception as e: print('zip err',e)
algs=['md5','sha1','sha224','sha256','sha384','sha512','sha3_256','blake2s','blake2b']
for p in sys.argv[1:]:
    b=open(p,'rb').read(); h=parse(b); zo=h['zo']
    dig=b[zo-64:zo].decode()
    print(p,dig); hit=0
    for n,d in cands(b,h):
        for a in algs:
            hx=hashlib.new(a,d).hexdigest()
            for t,s in (('',hx),('hh',hashlib.sha256(hx.encode()).hexdigest()),('hhmd5',hashlib.md5(hx.encode()).hexdigest()*2)):
                if dig in s or s in dig and len(s)>=32 and t=='' :
                    print(' HIT',n,a,t); hit+=1
            if dig.upper() in hx.upper(): pass
    print(' hits',hit)
