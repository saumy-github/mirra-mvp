import struct, array, json, sys, math
R=r"C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing"
def load(p):
    b=open(f"{R}\{p}\FeatureData.bd","rb").read()
    m,n=struct.unpack("<ii",b[:8]); a=array.array('f'); a.frombytes(b[8:8+4*m*n]); return m,n,len(b),a
def pct(s,q):
    k=(len(s)-1)*q; i=int(k); f=k-i
    return s[i]*(1-f)+s[min(i+1,len(s)-1)]*f
if __name__=="__main__":
    for p in ["Male","Female","Boy","Girl","PreSchool"]:
        m,n,sz,a=load(p); print(p,m,n,sz,8+4*m*n)
        # layout test: row-major [m][n] vs [n][m]: height row
        r0=a[0:n]; c0=a[0:m]
        print(" first n as row0 range",min(r0),max(r0)," first m",min(c0),max(c0))
