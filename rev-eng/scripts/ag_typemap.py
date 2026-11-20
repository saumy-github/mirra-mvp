import re,sys
sys.argv=['x']
import importlib.util
spec=importlib.util.spec_from_file_location('d','disasm_fn13.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
rows,calls,strs,g=d.analyse(0x5d76840,0x1000)
idx={int(a,16):i for i,(a,m,o,n) in enumerate(rows)}
def val_at(addr):
    # follow from addr: mov ebx,N then jmp/ fallthrough
    i=idx[addr]
    for j in range(i,i+4):
        a,m,o,n=rows[j]
        if m=='mov' and o.startswith('ebx,'):
            return o.split(',')[1]
    return '?'
cur=None
for i,(a,m,o,n) in enumerate(rows):
    if 'lea' == m and o.startswith('rdx,') and "'" in n:
        cur=re.search(r"'(.*)'",n).group(1)
    if m=='jne' and cur:
        t=int(o.strip(),16); print(cur, '->', val_at(t)); cur=None
    elif m=='je' and cur:
        # fallthrough next instr is mov ebx
        print(cur,'->',val_at(int(rows[i+1][0],16))); cur=None
