import sys,json,struct
sys.path.insert(0,"scripts")
import glb_probe as g
p=sys.argv[1]
d=g.load(p); j=d['json']
acc=j['accessors']
print("GARMENT meshes:")
for mi,m in enumerate(j['meshes'][:4]):
    for pr in m['primitives']:
        a=acc[pr['attributes']['POSITION']]
        print(mi,m.get('name'),'verts',a['count'],'min',[round(x,3) for x in a['min']],'max',[round(x,3) for x in a['max']],'idx',acc[pr['indices']]['count']//3,'mat',pr.get('material'),'mode',pr.get('mode'))
for ni,n in enumerate(j['nodes']):
    if 'mesh' in n and n['mesh']<4 or ni<3 or ni in (7,8):
        print('node',ni,{k:v for k,v in n.items() if k!='children'}, 'children' in n and len(n['children']))
print('scene',j['scenes'],j['scene'])
for i,m in enumerate(j['materials'][:2]): print(json.dumps(m))
for t in j['textures'][:3]: print(t)
for i,im in enumerate(j['images'][:3]): print(im)
print([ (k,len(v)) for k,v in j.items() if isinstance(v,list)])
print('doubleSided count',sum(1 for m in j['materials'] if m.get('doubleSided')),'alphaModes',[m.get('alphaMode') for m in j['materials']])
