import pickle,math,itertools
data=pickle.load(open(r"C:\D-drive-data\mirra-mvp\rev-eng\raw\w_positions.pkl","rb"))
names=["base","u_001-092","g_e5c37ff7a450d060-001","u_003-004","u_dcabc592e2bb18e7-009"]
dup=("u_003-004","u_003-005")
P={k:data[k][0][2] for k in data}; I={k:data[k][1][2] for k in data}
F={k:data[k][2] for k in data}
# duplicate repro
a,b=P[dup[0]],P[dup[1]]
print("dup max abs diff pos (mm?)",max(abs(x-y) for x,y in zip(a,b)),"feat diff",max(abs(x-y) for x,y in zip(F[dup[0]],F[dup[1]])))
n=len(a)
def solve(A,b):  # normal eq small
    m=len(A[0]); 
    M=[[sum(A[r][i]*A[r][j] for r in range(len(A))) for j in range(m)]+[sum(A[r][i]*b[r] for r in range(len(A)))] for i in range(m)]
    for i in range(m):
        p=max(range(i,m),key=lambda r:abs(M[r][i])); M[i],M[p]=M[p],M[i]
        for r in range(m):
            if r!=i:
                f=M[r][i]/M[i][i]; M[r]=[x-f*y for x,y in zip(M[r],M[i])]
    return [M[i][m]/M[i][i] for i in range(m)]
H=lambda k:F[k][0]
def feat(k,cols): return [1.0]+[F[k][c] for c in cols]
def fit_eval(cols,label,src=P,sample=range(0,n,97)):
    # LOO over 5 distinct points, using subsample of coordinates
    errs=[];fits=[]
    for hold in names:
        tr=[k for k in names if k!=hold]
        A=[feat(k,cols) for k in tr]
        e=0;mx=0;cnt=0
        for i in sample:
            y=[src[k][i] for k in tr]
            c=solve(A,y)
            pred=sum(ci*xi for ci,xi in zip(c,feat(hold,cols)))
            d=abs(pred-src[hold][i]); e+=d*d;cnt+=1; mx=max(mx,d)
        errs.append((hold,math.sqrt(e/cnt),mx))
    print(label,["%s rms=%.2f max=%.1f"%(h[:8],r,m) for h,r,m in errs])
fit_eval([0],"height only")
fit_eval([0,2],"height+bust")
fit_eval([0,2,6],"h+bust+waist")
# in-sample all-points fit residual with h,bust,waist,lowhip (4 params+1 =5 params, 5 pts => exact) skip
# in-sample height only
A=[feat(k,[0]) for k in names]
e=0;mx=0;cnt=0
for i in range(0,n,97):
    y=[P[k][i] for k in names]; c=solve(A,y)
    for k,yy in zip(names,y):
        d=sum(ci*xi for ci,xi in zip(c,feat(k,[0])))-yy; e+=d*d; cnt+=1; mx=max(mx,abs(d))
print("in-sample height-only rms %.2f max %.1f"%(math.sqrt(e/cnt),mx))
# displacement magnitudes
for k in names[1:]:
    dd=[abs(x-y) for x,y in zip(P[k],P["base"])]; print(k[:10],"mean|d|=%.1f max=%.1f"%(sum(dd)/len(dd),max(dd)),"feat:",[round(F[k][c],1) for c in (0,2,6,8)])
# collinearity of 67-dim features
import statistics
print("rank-ish: corr of each feature's delta with height delta")
dh=[F[k][0]-F["base"][0] for k in names[1:]]
cors=[]
for j in range(67):
    dj=[F[k][j]-F["base"][j] for k in names[1:]]
    # fit dj = s*dh residual
    s=sum(a*b for a,b in zip(dj,dh))/sum(a*a for a in dh); r=max(abs(a-s*b) for a,b in zip(dj,dh)); cors.append((j,round(s,3),round(r,2)))
print(cors)
