"""Lane M: list output dirs with route + .dan listFeatureValues[0] (cm). Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import avs_grammar as g
root = r'C:\D-drive-data\mirra-mvp\clo_avatar_generation\output'
def h(path):
    dan = g.load_dan(path); lm = g.leaf_map(dan)
    for p,(o,s,t) in lm.items():
        if p.endswith('listFeatureValues'):
            return struct.unpack_from('<f', dan, o+5+4*0+ (4*struct.unpack_from('<I',dan,o)[0]) )[0] if False else None, p, o, s
    return None
rows=[]
for dname in sorted(os.listdir(root)):
    dp = os.path.join(root, dname)
    if not os.path.isdir(dp): continue
    res = os.path.join(dp,'result_avatar_from_project.avt')
    if not os.path.exists(res): continue
    route = 'avt_patch' if os.path.exists(os.path.join(dp,'clo_payload.patched.avt')) else ('avs' if os.path.exists(os.path.join(dp,'clo_payload.avs')) else '?')
    dan = g.load_dan(res); lm = g.leaf_map(dan)
    ks = [p for p in lm if p.endswith('listFeatureValues')]
    val=None
    if ks:
        o,s,t = lm[ks[0]]
        c = struct.unpack_from('<I',dan,o)[0]; q=o+5+4*c
        val = struct.unpack_from('<f',dan,q)[0]
    rows.append((dname,route,val))
    print(dname,route,val)
