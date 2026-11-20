import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import disasm_fn2 as d
f=d.f; hdr=d.hdr; pe=struct.unpack_from('<I',hdr,0x3c)[0]
opt=pe+24; magic=struct.unpack_from('<H',hdr,opt)[0]
impdir=struct.unpack_from('<II',hdr,opt+112+8)[0]
def rd(r,n):
    f.seek(d.rva2off(r)); return f.read(n)
want=set(int(x,16) for x in sys.argv[1:])
p=impdir
while True:
    oft,ts,fc,nm,ft=struct.unpack('<IIIII',rd(p,20))
    if nm==0: break
    dll=rd(nm,64).split(b'\0')[0].decode()
    i=0
    while True:
        e=struct.unpack('<Q',rd((oft or ft)+8*i,8))[0]
        if e==0: break
        iat=ft+8*i
        if iat in want:
            if e>>63: name='ord %d'%(e&0xffff)
            else: name=rd((e&0x7fffffff)+2,100).split(b'\0')[0].decode()
            print(hex(iat),dll,name)
        i+=1
    p+=20
