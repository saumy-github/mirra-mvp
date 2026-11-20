"""Lane AE: stats of FeatureData.bd (derived summaries only). python -I scripts/ae_analyze.py > raw/ae_out.txt"""
import sys, math, json
sys.path.insert(0, r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
from ae_ranges import load, pct
SQRT_ROWS = range(1, 18)   # rows 1..17 are stored as sqrt(cm) (row 1 = sqrt(kg))
NAMES = {}
fm = json.load(open(r"C:\D-drive-data\mirra-mvp\rev-eng\raw\avs_tree.json"))["_feature_index_map"]
for k, v in fm.items(): NAMES[int(k)] = v["name"]
def rows(p):
    m, n, _, a = load(p)
    out = []
    for r in range(m):
        x = list(a[r*n:(r+1)*n])
        if r in SQRT_ROWS: x = [t*t for t in x]
        out.append(x)
    return out
def solve(A, b):
    n = len(A); M = [A[i][:] + [b[i]] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(n):
            if r != i:
                f = M[r][i]/M[i][i]; M[r] = [M[r][c]-f*M[i][c] for c in range(n+1)]
    return [M[i][n]/M[i][i] for i in range(n)]
def ols(X, y):
    n = len(y); k = len(X)+1
    cols = [[1.0]*n] + X
    A = [[sum(cols[i][t]*cols[j][t] for t in range(n)) for j in range(k)] for i in range(k)]
    b = [sum(cols[i][t]*y[t] for t in range(n)) for i in range(k)]
    w = solve(A, b)
    res = [y[t]-sum(w[i]*cols[i][t] for i in range(k)) for t in range(n)]
    sd = math.sqrt(sum(r*r for r in res)/(n-k)); my = sum(y)/n
    r2 = 1-sum(r*r for r in res)/sum((v-my)**2 for v in y)
    return w, sd, r2, res
def mean(x): return sum(x)/len(x)
def sd(x): m = mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
def corr(x, y):
    mx, my = mean(x), mean(y)
    return sum((a-mx)*(b-my) for a, b in zip(x, y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
if __name__ == "__main__":
    profiles = ["Male", "Female", "Boy", "Girl", "PreSchool"]
    for p in profiles:
        R = rows(p); n = len(R[0])
        print(f"## {p} n={n}")
        for r in range(58):
            s = sorted(R[r])
            print(f"{r}|{NAMES[r]}|{s[0]:.2f}|{pct(s,.01):.2f}|{pct(s,.05):.2f}|{pct(s,.5):.2f}|{pct(s,.95):.2f}|{pct(s,.99):.2f}|{s[-1]:.2f}|{mean(s):.2f}|{sd(s):.2f}")
    R = rows("Male"); n = len(R[0])
    sel = [(0, "Height"), (2, "Bust"), (6, "Waist"), (8, "LowHip"), (26, "Inseam"), (36, "AcrShoulder")]
    print("## corr male")
    for i, a in sel: print(a, " ".join(f"{corr(R[i],R[j]):.2f}" for j, b in sel))
    print("## corr male incl weight")
    for i, a in [(1,"Weight")]+sel: print(a, " ".join(f"{corr(R[i],R[j]):.2f}" for j, b in [(1,"W")]+sel))
    H, B, W, L, I, S, WT = R[0], R[2], R[6], R[8], R[26], R[36], R[1]
    for tgt, name in [(W,"Waist"),(L,"LowHip"),(I,"Inseam"),(S,"AcrShoulder"),(R[7],"HighHip")]:
        for xs, lab in [([H,B],"H+B"),([H,B,WT],"H+B+Wt"),([B],"B"),([H],"H")]:
            w, s_, r2, _ = ols(xs, tgt)
            print(f"reg {name} ~ {lab}: coef={[round(c,3) for c in w]} resid_sd={s_:.2f} R2={r2:.3f} (target sd {sd(tgt):.2f})")
    # difference distributions
    def dist(x, lab):
        s = sorted(x); print(f"diff {lab}: min {s[0]:.3f} p1 {pct(s,.01):.3f} p5 {pct(s,.05):.3f} med {pct(s,.5):.3f} p95 {pct(s,.95):.3f} p99 {pct(s,.99):.3f} max {s[-1]:.3f}")
    dist([a-b for a,b in zip(W,B)], "waist-bust"); dist([a-b for a,b in zip(L,B)], "lowhip-bust")
    dist([a-b for a,b in zip(L,W)], "lowhip-waist"); dist([a/b for a,b in zip(W,B)], "waist/bust ratio")
    dist([a/b for a,b in zip(L,B)], "hip/bust ratio"); dist([a/b for a,b in zip(I,H)], "inseam/height"); dist([a/b for a,b in zip(S,H)], "acrossShoulder/height")
    dist([a/b for a,b in zip(B,H)], "bust/height")
    dist([a/(b/100)**2 for a,b in zip(WT,H)], "BMI(weight row/height)")
    # Mahalanobis 6-var
    X = [H,B,W,L,I,S]; k=6
    mu=[mean(v) for v in X]
    C=[[sum((X[i][t]-mu[i])*(X[j][t]-mu[j]) for t in range(n))/(n-1) for j in range(k)] for i in range(k)]
    def md(v):
        d=[v[i]-mu[i] for i in range(k)]; z=solve(C,d); return math.sqrt(sum(a*b for a,b in zip(d,z)))
    ds=sorted(md([X[i][t] for i in range(k)]) for t in range(n))
    print("mahal6 p50 %.2f p95 %.2f p99 %.2f max %.2f"%(pct(ds,.5),pct(ds,.95),pct(ds,.99),ds[-1]))
    # test cases: (H,B,W,L,I,S)
    for lab,v in [("template",[187.96,96.52,82.55,95.25,86.36,44.13]),("avg",[177,102,93,101,79,44]),("waist>bust+15",[175,90,110,100,80,44]),("slim big hip",[175,85,70,115,80,44]),("short tall-bust",[150,120,100,100,70,40])]:
        print("mahal",lab,round(md(v),2))
    # joint conditional box for Mirra: given H,B -> waist, hip 2-var residual cov
    _,_,_,rw=ols([H,B],W); _,_,_,rl=ols([H,B],L)
    print("resid corr waist-hip given H,B: %.2f"%corr(rw,rl))
    s=sorted(rw);print("waist resid p1 %.1f p99 %.1f"%(pct(s,.01),pct(s,.99)))
    s=sorted(rl);print("hip resid p1 %.1f p99 %.1f"%(pct(s,.01),pct(s,.99)))
