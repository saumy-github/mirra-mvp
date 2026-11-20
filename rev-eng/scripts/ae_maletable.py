sec=open(r'C:\D-drive-data\mirra-mvp\rev-eng\raw\ae_out.txt').read().split('## ')
male=[s for s in sec if s.startswith('Male n=')][0].splitlines()[1:]
rows=["| idx | name | min | p1 | p50 | p99 | max | mean | std |","|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
for l in male:
    p=l.split('|')
    nm=p[1].replace('? (70.0; weight kg?)','Weight (kg) [I]')
    if nm.startswith('? ('): nm+=' (unnamed)'
    rows.append(f"| {p[0]} | {nm} | {p[2]} | {p[3]} | {p[5]} | {p[7]} | {p[8]} | {p[9]} | {p[10]} |")
print("\n".join(rows))
