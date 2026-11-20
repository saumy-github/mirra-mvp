import sys
sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import glb_probe as G
for p in sys.argv[1:]:
    g=G.load(p); j=g["json"]; acc=j["accessors"]
    per=0; ids=[]
    for m in j["meshes"]:
        for pr in m["primitives"]:
            a=pr["attributes"]["POSITION"]; per+=acc[a]["count"]; ids.append(a)
    d=sorted(set(ids))
    print(g["kind"],p.split("\\")[-2],"prims",len(ids),"distinct POSITION accessors",len(d),d,"counts",[acc[i]["count"] for i in d],"sum distinct",sum(acc[i]["count"] for i in d),"per-primitive sum",per)
