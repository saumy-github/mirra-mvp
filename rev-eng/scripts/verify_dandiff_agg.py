"""Lane M: aggregate dandiff by leaf-name. usage: A B  (paths to .avt). Read-only."""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(__file__))
import avs_grammar as g
a,b = g.load_dan(sys.argv[1]), g.load_dan(sys.argv[2])
rows = g.dan_diff(a,b)
agg = collections.defaultdict(lambda:[0,0,0.0])
for p,k,n,mx in rows:
    name = re.sub(r'\[\d+\]','[]',p).split('/')[-1]
    key = name if k=='bytes_diff' else k+':'+name
    agg[key][0]+=1; agg[key][1]+=n; agg[key][2]=max(agg[key][2],mx)
print('lenA',len(a),'lenB',len(b),'leaves',len(rows),'total bytes',sum(r[2] for r in rows))
for k,(c,n,mx) in sorted(agg.items(), key=lambda x:-x[1][1])[:25]: print('%-40s leaves %4d bytes %9d maxfloatdelta %.6g'%(k,c,n,mx))
