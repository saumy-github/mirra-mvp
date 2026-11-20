import struct,math
R=r"C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing\Male"
f=open(R+r"\PCA_weight.bd","rb"); n,k=struct.unpack("<ii",f.read(8))
a=struct.unpack("<%df"%n,f.read(4*n)); print("run0 norm (if [comp][dim]):",math.sqrt(sum(x*x for x in a)))
b=struct.unpack("<%df"%n,f.read(4*n)); print("run1 norm",math.sqrt(sum(x*x for x in b)),"dot run0.run1",sum(x*y for x,y in zip(a,b)))
# alt: first row of 100
print("first 100 norm",math.sqrt(sum(x*x for x in a[:100])))
# ratio: scale of coefficient std ~1343 for comp 0 -> vertex displacement magnitude per unit coefficient
print("max|run0|",max(map(abs,a)), "-> comp0 std 1343*max =",1343*max(map(abs,a)))
