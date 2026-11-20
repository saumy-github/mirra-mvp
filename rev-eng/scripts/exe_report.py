"""Build findings/06_exe_real_vtables.md from raw/exe_vtables.json + findings/04 table (+4 header-resolved slots)."""
import json, re, subprocess, os
ROOT = r"C:\D-drive-data\mirra-mvp\rev-eng"
DUMPBIN = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\dumpbin.exe"
EXE = r"C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"
R = json.load(open(ROOT + r"\raw\exe_vtables.json"))
cls = {"EXPORT": "ExportAPI@Marvelous", "FABRIC": "FabricAPI@Marvelous", "IMPORT": "ImportAPI@Marvelous",
       "PATTERN": "PatternAPI@Marvelous", "UTILITY": "UtilityAPI@Marvelous"}
rows = []
for l in open(ROOT + r"\findings\04_target_vtable_slots.md"):
    p = [x.strip() for x in l.split('|')]
    if len(p) > 5 and p[1] in cls and re.match(r'^[\d,]+$', p[3]):
        rows.append((p[1], p[2], [int(x) for x in p[3].split(',')], "04"))
rows += [("UTILITY", "GetAvatarProperties", [350], "header order"), ("UTILITY", "SetAvatarProperties", [349], "header order"),
         ("FABRIC", "SetFabricPBRMaterialBaseColor", [113, 114, 115, 116], "header order"),
         ("FABRIC", "SetBaseTextureMapImageGivenFilePath", [205, 217, 218, 247], "header order")]
def dis(rva, n=4):
    va = 0x140000000 + rva
    o = subprocess.run([DUMPBIN, "/nologo", "/disasm:nobytes", f"/range:0x{va:x},0x{va+0x20:x}", EXE], capture_output=True, text=True).stdout
    ins = [re.sub(r'^\s*[0-9A-F]+:\s*', '', x).strip() for x in o.splitlines() if re.match(r'\s*0000000', x)]
    return "; ".join(re.sub(r'\s+', ' ', i) for i in ins[:n])
out = ["# Real (derived) vtables in the CLO exe", "",
       "*Status: static analysis, CLO_Standalone_OnlineAuth_x64.exe 2026.1.336*", "*Date: 2026-10-29*", "",
       "RTTI found `Marvelous::{Utility,Pattern,Fabric,Import,Export,Gui,Rest}API` deriving from `CLOAPI::*APIInterface`. "
       "Slot numbers from `findings/04` apply 1:1 (slot == declaration index in the SDK header, verified on every named base slot). "
       "RVA = image offset (VA = 0x140000000 + RVA). `jmp` = slot is an E9 thunk to the shown RVA. "
       "Derived vtables of Utility/Pattern/Gui carry one extra trailing slot (the derived scalar-deleting dtor).", "",
       "| Derived class | vtable RVA | slots |", "|---|---|---|"]
for k, v in R.items(): out.append(f"| {k} | 0x{v['vtable_rva']:x} | {v['n_slots']} |")
out += ["", "| API | Function | Slot | Exe RVA | Source | First instructions |", "|---|---|---|---|---|---|"]
cache = {}
for api, fn, slots, src in rows:
    for s in slots:
        e = R[cls[api]]["slots"][s]; rva = e["rva"]
        d = cache.setdefault(rva, dis(rva))
        j = f" (jmp -> 0x{e['jmp_target']:x})" if e["jmp_target"] else ""
        out.append(f"| {api} | {fn} | {s} | 0x{rva:x}{j} | {src} | `{e['bytes'][:24]}` {d} |")
out += ["", "Notes: slots resolved by header order = declaration index, confirmed by neighbours (Utility 346/352 named, Get/SetAvatarProperties are decl 349/350; "
        "Fabric overload groups are contiguous in declaration order, as for GetFabricIndexForPattern 50,51)."]
open(ROOT + r"\findings\06_exe_real_vtables.md", "w", encoding="utf8").write("\n".join(out) + "\n")
print(len(out), "lines")
