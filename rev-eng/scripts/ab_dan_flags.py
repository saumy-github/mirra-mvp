"""ab_dan_flags.py - print softbody/divide related leaf values of the .dan inside .avt files (lane AB). Usage: python -I ab_dan_flags.py FILE.avt...
Read-only; reuses avs_grammar.load_dan/leaf_map."""
import sys, os, struct, importlib.util
spec=importlib.util.spec_from_file_location('g',os.path.join(os.path.dirname(os.path.abspath(__file__)),'avs_grammar.py'))
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
KEYS=('bSoftBodySimulation','fSoftBodyStiffness','bNeedToUpdateSoftBody','iSoftBodyMeshQuality','iDivisionLevel','bOnSubDivision','qsAvatarID','fSkinOffset','fStaticFriction','fKineticFriction','iResizingDataVersion')
for p in sys.argv[1:]:
    d=g.load_dan(p); lm=g.leaf_map(d)
    print('==',p, len(d))
    for path,(off,sz,ty) in lm.items():
        if any(path.split('/')[-1].startswith(k) for k in KEYS) and 'Controller' not in path.split('/')[-1]:
            raw=d[off:off+sz]
            if ty==1: v=raw[0]
            elif ty==4: v=struct.unpack('<i',raw)[0]
            elif ty==6: v=struct.unpack('<f',raw)[0]
            elif ty==0x0f: v=raw[:60]
            else: v='raw%d'%sz
            print('  %-60s t=%02x = %s'%(path,ty,v))
