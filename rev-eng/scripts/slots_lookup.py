"""slots_lookup.py <Class> name [name..]  -> grouped-overload slots + exe RVAs (lane I helper)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abi_check as A
cls = sys.argv[1]
sdk = A.DEF_SDK
names = A.header_virtuals(sdk, cls)
slots, n = A.slot_model(names)
vt = json.load(open(os.path.join(A.RAW, "abi_exe_vtables_cache.json")))["vt"]
key = [k for k in vt if k.startswith(cls + "API")][0]
S = vt[key]["slots"]
for nm in sys.argv[2:]:
    for s in slots.get(nm, []):
        e = S[s]; print(cls, nm, s, hex(e["rva"]), "jmp->" + hex(e["jmp_target"]) if e.get("jmp_target") else "")
