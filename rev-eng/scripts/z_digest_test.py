import struct,hashlib,sys,re,zlib,glob,os
def load(p):
    b=open(p,'rb').read(); return b
def parse(b):
    ver,f14,po,pl,zo,zl=struct.unpack_from('<6I',b,0x10)
    return dict(ver=ver,f14=f14,po=po,pl=pl,zo=zo,zl=zl,ts=struct.unpack_from('<Q',b,0x28)[0],f30=struct.unpack_from('<I',b,0x30)[0],f3c=struct.unpack_from('<I',b,0x3c)[0])
def hexs(b,zo):
    seg=b[zo-68:zo]
    return seg
def run(p):
    b=load(p); h=parse(b); zo=h['zo']
    seg=b[zo-68:zo]
    print(os.path.basename(p),h,'len',len(b))
    print(' seg',seg[:4].hex(),seg[4:].decode('latin1','replace'))
    return b,h,seg
if __name__=='__main__':
    for p in sys.argv[1:]: run(p)
