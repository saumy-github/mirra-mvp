import sys, struct, json
sys.path.insert(0,'C:/D-drive-data/mirra-mvp/rev-eng/scripts')
import glb_probe as G
g=G.load(sys.argv[1]); j=g['json']; b=g['bin']; acc=j['accessors']; bv=j['bufferViews']
print(g['kind'], 'nodes',len(j['nodes']),'meshes',len(j['meshes']),'skins',len(j.get('skins',[])),'mats',len(j.get('materials',[])),'ext',j.get('extensionsUsed'))
def rd(ai):
    a=acc[ai]; v=bv[a['bufferView']]; off=v.get('byteOffset',0)+a.get('byteOffset',0)
    n={'VEC3':3,'VEC2':2,'VEC4':4,'SCALAR':1}[a['type']]
    fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    sz=struct.calcsize(fmt)*n; stride=v.get('byteStride') or sz
    return [struct.unpack_from('<'+fmt*n,b,off+i*stride) for i in range(a['count'])]
T=[0,0,0,0]
for mi,m in enumerate(j['meshes']):
    for p in m['primitives']:
        at=p['attributes']; pos=rd(at['POSITION']); idx=rd(p['indices']) if 'indices' in p else []
        up=len(set(pos)); nrm=rd(at['NORMAL']) if 'NORMAL' in at else []
        un=len(set(zip(pos,nrm))) if nrm else 0
        uv=rd(at['TEXCOORD_0']) if 'TEXCOORD_0' in at else []
        upu=len(set(zip(pos,uv))) if uv else 0
        used=len(set(i[0] for i in idx))
        print(mi,m.get('name'),'attrs',list(at),'verts',len(pos),'tris',len(idx)//3,'uniqPos',up,'uniq(pos,n)',un,'uniq(pos,uv)',upu,'usedIdx',used,'mat',p.get('material'))
        T[0]+=len(pos);T[1]+=len(idx)//3;T[2]+=up
print('TOTAL verts',T[0],'tris',T[1],'uniqPos(sum)',T[2])
