import sys,struct,json,os,re,math
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import avs_grammar as g
O=r"C:\D-drive-data\mirra-mvp\clo_avatar_generation"
runs={"base":O+r"\input\base-1.avt"}
for r in ["u_001-092","g_e5c37ff7a450d060-001","u_003-004","u_003-005","u_dcabc592e2bb18e7-009"]:
    runs[r]=O+r"\output\%s\result_avatar_from_project.avt"%r
data={}
for k,a in runs.items():
    d=g.load_dan(a); out=[];g.index_block(d,0,len(d),"",out,minsize=1000)
    pos=[];init=[]
    for p,off,sz,ty,dep in out:
        if p.endswith("/mapMesh/baPosition"): pos.append(struct.unpack_from("<%df"%(sz//4),d,off))
        if p.endswith("/baInitPosition"): init.append(struct.unpack_from("<%df"%(sz//4),d,off))
    t=g.to_json(g.parse(d))["mapResizingAvatar"]
    data[k]=(pos,init,t["listFeatureValues"])
    print(k,[len(x) for x in pos],[len(x) for x in init])
import pickle; pickle.dump(data,open(r"C:\D-drive-data\mirra-mvp\rev-eng\raw\w_positions.pkl","wb"))
