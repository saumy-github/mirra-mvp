import sys,struct,json,os
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import avs_grammar as g
O=r"C:\D-drive-data\mirra-mvp\clo_avatar_generation"
runs={"base":(O+r"\input\base-1.avt",None),}
for r in ["u_001-092","g_e5c37ff7a450d060-001","u_003-004","u_003-005","u_dcabc592e2bb18e7-009"]:
    runs[r]=(O+r"\output\%s\result_avatar_from_project.avt"%r,O+r"\output\%s\clo_payload.avs"%r)
def feats(d):
    t=g.to_json(g.parse(d)); 
    m=t.get("MVresizingMap") or t.get("mapResizingAvatar")
    return m
for k,(a,s) in runs.items():
    d=g.load_dan(a); t=g.to_json(g.parse(d)); m=t["mapResizingAvatar"]
    f=m["listFeatureValues"]
    print(k,len(f),[round(x,2) for x in f[:10]], "modes",m.get("listMeasureMode",[])[:10], "LUM",m.get("enLastUpdateMode"), m.get("fBaseFeatureBustCircum"))
    if s:
        t2=g.to_json(g.parse(open(s,"rb").read())); f2=t2["MVresizingMap"]["listFeatureValues"]
        print("  avs",len(f2),"same as result:",all(abs(x-y)<1e-3 for x,y in zip(f,f2)))
