"""z_verify_digest.py - verify CLO container digest = hex(SHA256(file[0:zip_off-68] + salt)) ; also check 0x24 vs real size, ZIP at zo, f14 etc."""
import sys,hashlib,struct,zipfile,io,os
SALT=b"scrampling&$%!@#mvfileheader"
for p in sys.argv[1:]:
    try: b=open(p,'rb').read()
    except Exception as e: print(p,'ERR',e); continue
    if len(b)<0x100 or b[:16] not in (b' AVT        CLO ',b' ZPRJ       CLO ',b' ZPAC       CLO ') and not b[:16].endswith(b'CLO '):
        print(os.path.basename(p),'not CLO container',b[:16]); continue
    ver,f14,po,pl,zo,zl=struct.unpack_from('<6I',b,0x10)
    ln=struct.unpack_from('<I',b,zo-68)[0]; dig=b[zo-64:zo]
    calc=hashlib.sha256(b[:zo-68]+SALT).hexdigest().encode()
    pk=b[zo:zo+4]==b'PK\x03\x04'
    st=(len(b)-zo)
    print('%-45s %s ver=%d f14=%d zl_hdr=%d zl_real=%d %s digest_ok=%s ln=%d pk=%s'%(os.path.basename(p)[:45],b[1:5].decode().strip(),ver,f14,zl,st,'ZLEN_OK' if zl==st else 'ZLEN_STALE(%+d)'%(st-zl),calc==dig,ln,pk))
