"""msg_catalog_gen.py (lane J) - per-API-function diagnostic strings referenced by the wrapper bodies. Needs raw/log_catalog.json
(scripts/log_catalog.py) and the SDK headers (for slot->name). Writes raw/msg_by_function.json + prints a markdown table body."""
import json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "..", "raw")
sys.path.insert(0, HERE)
import abi_check as A
SDK = A.DEF_SDK
names = {}
for c in A.CLASSES:
    ns_ = A.header_virtuals(SDK, c); slots, n = A.slot_model(ns_)
    inv = {}
    for nm, sl in slots.items():
        for s in sl: inv[s] = nm
    names[c] = inv
cat = json.load(open(os.path.join(RAW, "log_catalog.json")))
NOISE = re.compile(r"^(cannot |invalid map|\[json|Marvelous::|std::|CLOAPI::|class |bool __cdecl|void __cdecl|struct )")
def good(s):
    if NOISE.match(s) or s.startswith("[Python]") and re.fullmatch(r"\[Python\] [~\w]+ ?", s): return False
    if "__cdecl" in s: return False
    return (" " in s.strip() and len(s) >= 10) or s in ("NO_EDITOR",)
res = collections.OrderedDict()
for fn in cat:
    c = fn["cls"].split("@")[0].replace("API", "")
    slot = fn["slot"]
    nm = names.get(c, {}).get(slot, "?slot%d" % slot)
    msgs = [s for a, s in fn["strings"] if good(s)]
    if msgs: res.setdefault("%s.%s" % (c, nm), {"rva": fn["rva"], "slot": slot, "msgs": []})["msgs"] += [m for m in msgs if m not in res.get("%s.%s" % (c, nm), {"msgs": []})["msgs"]]
json.dump(res, open(os.path.join(RAW, "msg_by_function.json"), "w"), indent=1)
for k, v in res.items():
    print("### %s  (slot %d, RVA %s)" % (k, v["slot"], v["rva"]))
    for m in v["msgs"]: print("   -", repr(m[:160]))
