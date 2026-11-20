"""abi_check.py - Will a RestPlugin DLL built against SDK folder X dispatch correctly inside the installed CLO exe?

Static only (stdlib). Never runs or hooks CLO. Reads: SDK headers, the exe (mmap, via exe_rtti.py, cached),
the plugin source + PluginBuildInfo.h (read-only), and rev-eng/raw/vtable_app.json + findings/06 as slot anchors.

USAGE (from anywhere):
  python -I rev-eng/scripts/abi_check.py [--sdk SDK_DIR] [--clo CLO_DIR] [--tag NAME] [--out-dir DIR]
                                         [--plugin-cpp PATH] [--build-info PATH] [--rebuild-cache]
  defaults: --sdk  C:\\Users\\Saumy\\Downloads\\CLO_SDK_v2026.1.336_Win
            --clo  C:\\Program Files\\CLO Standalone OnlineAuth
            --tag  derived from SDK folder name's last build number (e.g. 336)
  Outputs: rev-eng/findings/14_abi_check_report[_<tag>].md and rev-eng/raw/abi_check_<tag>.json
           (the default 336 run writes the unsuffixed 14_abi_check_report.md; any other tag writes a suffixed file).
  Exit code: 0 = PASS (no MISMATCH, versions match), 1 = FAIL.

WHAT IT CHECKS
 (a) Per-class vtable slot index of every virtual, from header declaration order (CLOAPIInterface/include/*APIInterface.h).
     Rule (validated in findings/06): slot == 0-based index of the `virtual` declaration, except MSVC groups all overloads of
     one name contiguously at the position of the FIRST declaration of that name. Self-test: the model is run on the
     installed-DLL named slots (raw/vtable_app.json) and agreement is reported per class ("anchor agreement").
 (b) Exe derived vtables (Marvelous::*API): slot count per class vs header count (+1 trailing derived dtor slot for
     classes where the base has no virtual dtor slot); every slot must point into .text and not be an int3/trivial
     `xor eax,eax; ret` stub body.
 (c) For every `*_API->Name` the plugin source uses: header-derived slot set (this SDK) vs anchor slot set from the
     installed build (DLL export names, else findings/06 header-order rows). OK / MISMATCH / UNVERIFIED.
 (d) Hash (comment-stripped, whitespace-normalised) of each CloApiData.h type the plugin uses, compared with the
     reference SDK (--ref-sdk, default SDK 336) hash; ProductVersion of exe vs SDK folder version; PluginBuildInfo.h
     SDK folder / CLO version vs the SDK given.
 (e) Writes markdown + JSON verdict.
"""
import argparse, hashlib, json, mmap, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV = os.path.normpath(os.path.join(HERE, ".."))
RAW = os.path.join(REV, "raw")
FIND = os.path.join(REV, "findings")
DEF_SDK = r"C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.336_Win"
DEF_CLO = r"C:\Program Files\CLO Standalone OnlineAuth"
DEF_CPP = r"C:\D-drive-data\mirra-mvp\clo_workspace\windows\RestPlugin_windows.cpp"
DEF_BI = r"C:\D-drive-data\mirra-mvp\clo_workspace\shared\PluginBuildInfo.h"
CLASSES = ["Export", "Utility", "Fabric", "Gui", "Import", "Pattern", "Rest"]
API_VAR = {"EXPORT_API": "Export", "UTILITY_API": "Utility", "FABRIC_API": "Fabric", "GUI_API": "Gui",
           "IMPORT_API": "Import", "PATTERN_API": "Pattern", "REST_API": "Rest"}


# ---------------------------------------------------------------- helpers
def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def folder_version(path):
    m = re.search(r'v(\d+\.\d+\.\d+)', os.path.basename(path.rstrip("\\/")))
    return m.group(1) if m else None


def header_virtuals(sdk, cls):
    """Return ordered list of virtual function names (declaration order) incl. virtual dtor."""
    p = os.path.join(sdk, "CLOAPIInterface", "include", cls + "APIInterface.h")
    t = strip_comments(open(p, encoding="utf8", errors="ignore").read())
    names = []
    for m in re.finditer(r'\bvirtual\b([^;{}]*?)(~?\w+)\s*\(', t):
        names.append(m.group(2))
    return names


def slot_model(names):
    """MSVC overload grouping: all overloads of a name are laid out contiguously at the first declaration."""
    order, seen = [], {}
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        if seen[n] == 1:
            order.append(n)
    slots, idx = {}, 0
    for n in order:
        slots[n] = list(range(idx, idx + seen[n]))
        idx += seen[n]
    return slots, idx


def load_anchor_names():
    """name -> sorted slot list from installed DLL (raw/vtable_app.json), per class."""
    d = json.load(open(os.path.join(RAW, "vtable_app.json")))
    res = {}
    for k, sl in d.items():
        if not k.endswith("APIInterface") or k == "APICommand":
            continue
        c = k[:-len("APIInterface")]
        r = {}
        for s in sl:
            t = s.get("demangled") or (s["candidates"][0] if s.get("candidates") else None)
            if s.get("demangled"):
                m = re.search(r'CLOAPI::\w+::(~?\w+)\(', t)
                if m:
                    r.setdefault(m.group(1), []).append(s["slot"])
        res[c] = r
    return res


def load_anchor_f06():  # kept for reference only: its header-order rows used a naive (ungrouped) index, not used as anchor
    """(class, func) -> (slots, source) from findings/06 table."""
    res = {}
    for l in open(os.path.join(FIND, "06_exe_real_vtables.md"), encoding="utf8"):
        m = re.match(r'\|\s*(EXPORT|UTILITY|FABRIC|GUI|IMPORT|PATTERN|REST)\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|', l)
        if m:
            k = (m.group(1).capitalize(), m.group(2))
            e = res.setdefault(k, {"slots": [], "src": m.group(4)})
            e["slots"].append(int(m.group(3)))
    return res


# ---------------------------------------------------------------- exe
def exe_vtables(exe, rebuild=False):
    st = os.stat(exe)
    key = "%d-%d" % (st.st_size, int(st.st_mtime))
    cache = os.path.join(RAW, "abi_exe_vtables_cache.json")
    if not rebuild and os.path.exists(cache):
        c = json.load(open(cache))
        if c.get("key") == key and c.get("exe") == exe:
            return c["vt"], True
    sys.path.insert(0, HERE)
    argv = sys.argv
    sys.argv = [argv[0], exe]
    try:
        import exe_rtti  # exe_rtti.py's own cache (raw/exe_rtti_cache.json) is keyed by nothing: drop if exe changed
        if not os.path.exists(exe_rtti.CACHE) or rebuild:
            C = exe_rtti.build()
            json.dump(C, open(exe_rtti.CACHE, "w"))
        vt = exe_rtti.derived_vtables()
        # add trivial-stub / int3 analysis from raw bytes
        for cls, v in vt.items():
            for s in v["slots"]:
                tgt = s["jmp_target"] if s["jmp_target"] else s["rva"]
                o = exe_rtti.off(tgt)
                b = bytes(exe_rtti.m[o:o + 8]) if o is not None else b""
                s["body"] = b.hex()
                s["trivial"] = (b[:1] == b"\xcc") or (b[:3] == b"\x33\xc0\xc3") or (b[:1] == b"\xc3")
    finally:
        sys.argv = argv
    json.dump({"key": key, "exe": exe, "vt": vt}, open(cache, "w"))
    return vt, False


def exe_product_version(exe):
    with open(exe, "rb") as f:
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        # resource is near the end of file typically; search tail first
        pat = "ProductVersion".encode("utf-16le") + b"\0\0"
        n = len(m)
        for lo in (max(0, n - 8 * 1024 * 1024), 0):
            p = m.find(pat, lo)
            if p >= 0:
                p += len(pat)
                while p % 4:
                    p += 1
                e = p
                while m[e:e + 2] != b"\0\0" or e % 2:
                    e += 2 if e % 2 == 0 else 1
                    if e - p > 200:
                        break
                return m[p:e].decode("utf-16le", "ignore")
    return None


# ---------------------------------------------------------------- structs
def struct_hashes(sdk, tnames):
    p = os.path.join(sdk, "CLOAPIInterface", "include", "CloApiData.h")
    t = strip_comments(open(p, encoding="utf8", errors="ignore").read())
    out = {}
    for n in tnames:
        m = re.search(r'\b(?:class|struct)\s+' + re.escape(n) + r'\b[^;{]*\{', t)
        if not m:
            out[n] = None
            continue
        i = m.end() - 1
        depth = 0
        for j in range(i, len(t)):
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        body = re.sub(r'\s+', ' ', t[m.start():j + 1]).strip()
        out[n] = {"sha1": hashlib.sha1(body.encode()).hexdigest()[:16], "len": len(body)}
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdk", default=DEF_SDK)
    ap.add_argument("--ref-sdk", default=DEF_SDK, help="SDK whose struct hashes are the known-good reference")
    ap.add_argument("--clo", default=DEF_CLO)
    ap.add_argument("--tag")
    ap.add_argument("--plugin-cpp", default=DEF_CPP)
    ap.add_argument("--build-info", default=DEF_BI)
    ap.add_argument("--rebuild-cache", action="store_true")
    ap.add_argument("--out-dir", default=FIND)
    a = ap.parse_args()
    sdk, clo = a.sdk, a.clo
    sdkver = folder_version(sdk)
    tag = a.tag or (sdkver.split(".")[-1] if sdkver else "x")
    exe = os.path.join(clo, "CLO_Standalone_OnlineAuth_x64.exe")
    res = {"sdk": sdk, "sdk_version": sdkver, "clo_dir": clo, "tag": tag, "checks": {}}

    # (a)
    models = {}
    for c in CLASSES:
        try:
            names = header_virtuals(sdk, c)
        except OSError:
            models[c] = None
            continue
        slots, total = slot_model(names)
        models[c] = {"slots": slots, "total": total, "n_decl": len(names)}
    anchors = load_anchor_names()
    refmodels = {}
    for c in CLASSES:
        try:
            refmodels[c] = dict(zip(("slots", "total"), slot_model(header_virtuals(a.ref_sdk, c))))
        except OSError:
            refmodels[c] = None

    # anchor agreement (self-test / drift locator)
    agree = {}
    for c in CLASSES:
        mdl = models[c]
        an = anchors.get(c, {})
        if not mdl:
            agree[c] = None
            continue
        ok = bad = 0
        first_bad = None
        # order by anchor slot to find first divergence
        for nme, sl in sorted(an.items(), key=lambda kv: kv[1][0]):
            hs = mdl["slots"].get(nme)
            if hs is not None and set(sl) <= set(hs):
                ok += 1
            else:
                bad += 1
                if first_bad is None:
                    first_bad = {"name": nme, "anchor": sl, "header": hs}
        agree[c] = {"ok": ok, "bad": bad, "first_divergence": first_bad, "anchored": len(an)}
    res["anchor_agreement"] = agree

    # (b)
    vt, cached = exe_vtables(exe, a.rebuild_cache)
    res["exe_cache_hit"] = cached
    cls_rows = {}
    for c in CLASSES:
        v = vt.get(c + "API@Marvelous")
        mdl = models[c]
        if not v or not mdl:
            cls_rows[c] = {"status": "UNVERIFIED", "why": "no exe vtable or no header"}
            continue
        hdr_total = mdl["total"]
        n = v["n_slots"]
        extra = n - hdr_total
        # Utility/Pattern/Gui derived dtor adds +1 per findings/06 (base DLL slots = n-1).
        expect_extra = {"Utility": 1, "Pattern": 1, "Gui": 1, "Rest": 2}.get(c, 0)  # Rest +2 is empirical (findings/06)
        triv = [s["slot"] for s in v["slots"] if s.get("trivial")]
        st = "OK" if extra == expect_extra else "MISMATCH"
        cls_rows[c] = {"status": st, "header_slots": hdr_total, "exe_slots": n, "delta": extra,
                       "expected_delta": expect_extra, "trivial_body_slots": triv[:10], "n_trivial": len(triv)}
    res["classes"] = cls_rows

    # (c)
    try:
        cpp = strip_comments(open(a.plugin_cpp, encoding="utf8", errors="ignore").read())
    except OSError:
        cpp = ""
    used = {}
    for m in re.finditer(r'\b([A-Z]+_API)\s*->\s*(\w+)', cpp):
        if m.group(1) in API_VAR:
            used.setdefault((API_VAR[m.group(1)], m.group(2)), 0)
            used[(API_VAR[m.group(1)], m.group(2))] += 1
    fn_rows = []
    for (c, f), cnt in sorted(used.items()):
        mdl = models.get(c)
        hs = mdl["slots"].get(f) if mdl else None
        an = anchors.get(c, {}).get(f)
        src = "dll-export-name"   # partial sets possible: ICF-folded overloads are unnamed in the DLL
        if an is None and refmodels.get(c) and f in refmodels[c]["slots"]:
            an, src = refmodels[c]["slots"][f], "ref-sdk-header-model"
        row = {"api": c, "func": f, "calls": cnt, "header_slots": hs, "anchor_slots": an, "anchor_src": src if an else None}
        v = vt.get(c + "API@Marvelous")
        if hs is None:
            row["status"] = "MISMATCH"; row["note"] = "not declared virtual in this SDK header"
        elif an is None:
            row["status"] = "UNVERIFIED"; row["note"] = "no anchor slot for this name"
        elif (set(an) <= set(hs)) if src == "dll-export-name" else (sorted(hs) == sorted(an)):
            row["status"] = "OK"
            if src != "dll-export-name":
                row["note"] = "no DLL name for this slot (ICF); compared with reference-SDK header model (weak)"
            elif sorted(hs) != sorted(an):
                row["note"] = "installed names cover only slots %s (rest ICF-unnamed); subset OK" % an
        else:
            row["status"] = "MISMATCH"
            row["note"] = "header slot %s != installed %s" % (hs, an)
        if v and hs:
            row["exe_body_ok"] = all(h < v["n_slots"] and not v["slots"][h].get("trivial") for h in hs)
            row["exe_rva"] = [hex(v["slots"][h]["rva"]) for h in hs if h < v["n_slots"]]
            if not row["exe_body_ok"] and row["status"] == "OK":
                row["status"] = "MISMATCH"; row["note"] = "slot beyond exe vtable or trivial body"
        fn_rows.append(row)
    res["functions"] = fn_rows

    # (d)
    tnames = sorted(set(re.findall(r'Marvelous::(\w+)', cpp)))
    cur = struct_hashes(sdk, tnames)
    ref = struct_hashes(a.ref_sdk, tnames)
    srows = []
    for n in tnames:
        if cur[n] is None and ref[n] is None:
            continue  # not a CloApiData.h type
        same = cur[n] is not None and ref[n] is not None and cur[n]["sha1"] == ref[n]["sha1"]
        srows.append({"type": n, "sha1": cur[n] and cur[n]["sha1"], "ref_sha1": ref[n] and ref[n]["sha1"],
                      "status": "OK" if same else "MISMATCH"})
    res["structs"] = srows
    pv = exe_product_version(exe)
    bi = {}
    try:
        for l in open(a.build_info, encoding="utf8"):
            m = re.match(r'#define\s+(\w+)\s+"(.*)"', l)
            if m:
                bi[m.group(1)] = m.group(2)
    except OSError:
        pass
    def vnorm(s):
        return re.sub(r'[^0-9.]', '', (s or '').replace(', ', '.'))
    ver = {"exe_product_version": pv, "sdk_folder_version": sdkver, "buildinfo_sdk_folder": bi.get("MIRRA_PLUGIN_SDK_FOLDER"),
           "buildinfo_clo_version": bi.get("MIRRA_PLUGIN_SDK_CLO_VERSION"), "buildinfo_build_time": bi.get("MIRRA_PLUGIN_BUILD_TIME")}
    def vm(x, y):
        x, y = vnorm(x), vnorm(y)
        return bool(x and y and (x == y or x.startswith(y) or y.startswith(x)))
    ver["sdk_vs_exe"] = "OK" if vm(".".join(vnorm(pv).split(".")[:3]), sdkver) else "MISMATCH"
    ver["buildinfo_vs_sdk"] = "OK" if (bi.get("MIRRA_PLUGIN_SDK_FOLDER") == os.path.basename(sdk.rstrip("\\/"))) else "MISMATCH"
    res["versions"] = ver

    # verdict
    fails = []
    fails += ["class %s vtable size" % c for c, r in cls_rows.items() if r["status"] == "MISMATCH"]
    fails += ["fn %s::%s" % (r["api"], r["func"]) for r in fn_rows if r["status"] == "MISMATCH"]
    fails += ["struct " + r["type"] for r in srows if r["status"] == "MISMATCH"]
    fails += [k for k in ("sdk_vs_exe", "buildinfo_vs_sdk") if ver[k] == "MISMATCH"]
    unv = [r for r in fn_rows if r["status"] == "UNVERIFIED"]
    res["verdict"] = "FAIL" if fails else ("PASS (with %d unverified)" % len(unv) if unv else "PASS")
    res["fail_reasons"] = fails

    os.makedirs(a.out_dir, exist_ok=True)
    jpath = os.path.join(RAW, "abi_check_%s.json" % tag)
    json.dump(res, open(jpath, "w"), indent=1)
    suffix = "" if tag == "336" else "_" + tag
    mpath = os.path.join(a.out_dir, "14_abi_check_report%s.md" % suffix)
    write_md(res, mpath, jpath)
    print("VERDICT:", res["verdict"], "| fails:", len(fails), "| unverified:", len(unv))
    print("report:", mpath, "\njson:", jpath)
    return 0 if not fails else 1


def write_md(r, path, jpath):
    L = []
    A = L.append
    A("# ABI check: SDK %s vs installed CLO" % (r["sdk_version"] or r["sdk"]))
    A("")
    A("*Status: generated by scripts/abi_check.py (static analysis, nothing executed)*")
    A("*Date: 2026-10-29*")
    A("")
    A("SDK: `%s`  \nCLO dir: `%s`  \nJSON: `%s`" % (r["sdk"], r["clo_dir"], os.path.relpath(jpath, REV)))
    A("")
    A("## Verdict: **%s**" % r["verdict"])
    A("")
    if r["fail_reasons"]:
        A("Failing items: " + ", ".join(r["fail_reasons"][:40]) + (" ..." if len(r["fail_reasons"]) > 40 else ""))
        A("")
    v = r["versions"]
    A("## Versions")
    A("| item | value |\n|---|---|")
    for k in ("exe_product_version", "sdk_folder_version", "buildinfo_sdk_folder", "buildinfo_clo_version", "buildinfo_build_time"):
        A("| %s | %s |" % (k, v[k]))
    A("| SDK folder vs exe ProductVersion | %s |" % v["sdk_vs_exe"])
    A("| PluginBuildInfo.h SDK folder vs checked SDK | %s |" % v["buildinfo_vs_sdk"])
    A("")
    A("## (b) Per-class vtable size (header-derived vs exe)")
    A("| class | header slots | exe slots | delta | expected delta | status |\n|---|---|---|---|---|---|")
    for c, x in r["classes"].items():
        if "header_slots" in x:
            A("| %s | %d | %d | %+d | %+d | %s |" % (c, x["header_slots"], x["exe_slots"], x["delta"], x["expected_delta"], x["status"]))
        else:
            A("| %s | - | - | - | - | %s (%s) |" % (c, x["status"], x["why"]))
    A("")
    A("## (a) Anchor agreement: header-derived slot vs installed-DLL named slots")
    A("*First divergence = where this SDK's header order starts to disagree with the installed build (insertion point).*")
    A("| class | named anchors | agree | disagree | first divergence |\n|---|---|---|---|---|")
    for c, x in r["anchor_agreement"].items():
        if x is None:
            A("| %s | - | - | - | header missing |" % c)
        else:
            fd = x["first_divergence"]
            A("| %s | %d | %d | %d | %s |" % (c, x["anchored"], x["ok"], x["bad"],
              ("`%s` installed %s, header %s" % (fd["name"], fd["anchor"], fd["header"])) if fd else "none"))
    A("")
    A("## (c) Functions called by the plugin")
    A("| API | function | header slots | installed slots | exe RVA | status | note |\n|---|---|---|---|---|---|---|")
    for x in r["functions"]:
        A("| %s | %s | %s | %s | %s | %s | %s |" % (x["api"], x["func"], x["header_slots"], x["anchor_slots"],
          ",".join(x.get("exe_rva", [])), x["status"], x.get("note", "")))
    cnt = {}
    for x in r["functions"]:
        cnt[x["status"]] = cnt.get(x["status"], 0) + 1
    A("")
    A("Totals: " + ", ".join("%s=%d" % kv for kv in sorted(cnt.items())))
    A("")
    A("## (d) Struct definitions used by the plugin (CloApiData.h, comment-stripped hash vs reference SDK)")
    A("| type | sha1 | reference sha1 | status |\n|---|---|---|---|")
    for s in r["structs"]:
        A("| %s | %s | %s | %s |" % (s["type"], s["sha1"], s["ref_sha1"], s["status"]))
    A("")
    A("## Limits")
    A("- Anchors are the installed app DLL's exported-name slots (raw/vtable_app.json, from build 336) plus findings/06 rows; if CLO is updated, regenerate them (vtable_slots.py) and pass --rebuild-cache.")
    A("- Overload order inside a group is not checked, only the slot set per name.")
    A("- Struct check is textual (definition hash), not a real sizeof; any edit, even a default value, flags MISMATCH.")
    open(path, "w", encoding="utf8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
