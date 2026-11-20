import struct,math,sys
R=r"C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing\Male"
def load(f):
    b=open(R+"\\"+f,"rb").read(); a,c=struct.unpack_from("<ii",b,0); v=struct.unpack_from("<%df"%(a*c),b,8); return a,c,v
nf,ns,F=load("FeatureData.bd"); nc,ns2,Y=load("ReducedVertexData.bd")
print("feat",nf,ns,"coef",nc,ns2)
# layout guess: F[feature*ns+sample]? test: feature0 first values ~ heights 181.6,173.6,... consecutive -> row-major [feature][sample]
print("F[0:4]",F[:4],"F[ns:ns+4]",F[ns:ns+4])
print("Y[0:4]",Y[:4],"Y[ns:ns+4]",Y[ns:ns+4])
X=[[1.0]+[F[j*ns+s] for j in range(nf)] for s in range(ns)]
p=nf+1
# standardise columns for conditioning
mu=[sum(r[j] for r in X)/ns for j in range(p)]; sd=[ (sum((r[j]-mu[j])**2 for r in X)/ns)**.5 or 1 for j in range(p)]
Z=[[1.0]+[(r[j]-mu[j])/sd[j] for j in range(1,p)] for r in X]
A=[[sum(Z[s][i]*Z[s][j] for s in range(ns))+(1e-6 if i==j and i>0 else 0) for j in range(p)] for i in range(p)]
# cholesky-free gauss
def solve_multi(A,B):
    n=len(A); M=[A[i][:]+B[i][:] for i in range(n)]
    for i in range(n):
        piv=max(range(i,n),key=lambda r:abs(M[r][i])); M[i],M[piv]=M[piv],M[i]
        d=M[i][i]; M[i]=[x/d for x in M[i]]
        for r in range(n):
            if r!=i and M[r][i]!=0:
                f=M[r][i]; M[r]=[x-f*y for x,y in zip(M[r],M[i])]
    return [row[n:] for row in M]
K=nc
B=[[sum(Z[s][i]*Y[k*ns+s] for s in range(ns)) for k in range(K)] for i in range(p)]
W=solve_multi(A,B)
res=[]
for k in range(K):
    ys=[Y[k*ns+s] for s in range(ns)]; m=sum(ys)/ns; tot=sum((y-m)**2 for y in ys)
    sse=0
    for s in range(ns):
        pr=sum(W[i][k]*Z[s][i] for i in range(p)); sse+=(pr-ys[s])**2
    res.append((k,1-sse/tot,math.sqrt(tot/ns)))
print("R2 per comp (first 20):",[round(r[1],3) for r in res[:20]])
print("R2 comps 20..99 mean:",sum(r[1] for r in res[20:])/80, "min",min(r[1] for r in res))
print("coef std (first 5):",[round(r[2],1) for r in res[:5]],"last:",round(res[-1][2],2))
# variance-weighted R2
tv=sum(r[2]**2 for r in res); print("variance-weighted R2:",sum(r[1]*r[2]**2 for r in res)/tv)
