import struct,sys
R=r"C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing"
for g in ["Male","Female","Boy","Girl","PreSchool"]:
    for f in ["PCA_weight.bd","FeatureData.bd","ReducedVertexData.bd","BaseMesh.be","range_list.rlist","symmetry_data.sym","nearestIndices.txt","IndexSet.txt"]:
        b=open(R+"\\"+g+"\\"+f,"rb").read(64)
        print(g,f,b[:48].hex(), struct.unpack_from("<4i",b,0), struct.unpack_from("<4f",b,0))
    # obj counts
    v=0;vt=0;fc=0
    for line in open(R+"\\"+g+"\\BaseMesh.obj","rb"):
        if line.startswith(b"v "): v+=1
        elif line.startswith(b"f "): fc+=1
    print(g,"obj v",v,"f",fc)
