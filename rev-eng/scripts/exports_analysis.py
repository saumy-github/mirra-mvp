"""Parse dumpbin /exports dumps, undecorate via undname, diff SDK 224 vs 336 vs installed app DLL."""
import re, subprocess, sys, pathlib
R = pathlib.Path(__file__).resolve().parent.parent / "raw"
UN = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\undname.exe"
def names(f):
    out = []
    for l in (R/f).read_text(encoding="utf8", errors="ignore").splitlines():
        m = re.match(r"\s+(\d+)\s+[0-9A-F]+\s+([0-9A-F]{8})\s+(\S+)", l)
        if m: out.append((m.group(3), m.group(2)))
    return out
def undec(n):
    try:
        o = subprocess.run([UN, n], capture_output=True, text=True).stdout
        m = re.search(r'is :- "(.*)"', o)
        return m.group(1) if m else n
    except Exception: return n
sets = {k: dict(names(f)) for k, f in [("sdk224","dll_exports_224.txt"),("sdk336","dll_exports_336.txt"),("app","app_dll_exports.txt")]}
for k, v in sets.items(): print(k, len(v))
a, b, c = (set(sets[k]) for k in ("sdk224","sdk336","app"))
print("added 224->336:", len(b-a), "removed:", len(a-b), "sdk336 vs app only-in-sdk:", len(b-c), "only-in-app:", len(c-b))
out = ["# Export diffs (undecorated)\n"]
for title, s in [("Added in 336 (vs 224)", b-a), ("Removed in 336 (vs 224)", a-b), ("In SDK 336 but not in installed app DLL", b-c), ("In installed app DLL but not in SDK 336", c-b)]:
    out.append(f"\n## {title} ({len(s)})\n")
    for n in sorted(s): out.append("- " + undec(n))
# full undecorated 336 list
full = sorted(undec(n) for n in sets["sdk336"])
(R/"exports_336_undecorated.txt").write_text("\n".join(full), encoding="utf8")
(R.parent/"findings"/"03b_export_diff.md").write_text("\n".join(out), encoding="utf8")
