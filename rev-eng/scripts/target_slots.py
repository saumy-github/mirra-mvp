"""Vtable slot (installed app CLOAPIInterface.dll, CLO 2026.1.336) of every API function the plugin calls."""
import json, re, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
v = json.load(open(R/"raw"/"vtable_app.json"))
src = (R.parent/"clo_workspace/windows/RestPlugin_windows.cpp").read_text(encoding="utf8", errors="ignore")
targets = sorted(set(re.findall(r"\b(UTILITY|IMPORT|EXPORT|PATTERN|FABRIC)_API->([A-Za-z_]+)", src)))
cmap = {"UTILITY":"UtilityAPIInterface","IMPORT":"ImportAPIInterface","EXPORT":"ExportAPIInterface","PATTERN":"PatternAPIInterface","FABRIC":"FabricAPIInterface"}
rows = ["| API | Function | vtable slot(s) | byte offset of first |", "|---|---|---|---|"]; missing = []
for a, fn in targets:
    cls = cmap[a]
    sl = [s["slot"] for s in v[cls] if s["demangled"] and re.search(rf"::{cls}::{fn}\(", s["demangled"])]
    if not sl: missing.append(f"{a}::{fn}")
    rows.append(f"| {a} | {fn} | {','.join(map(str, sl)) or 'unresolved'} | {('0x%X' % (8*sl[0])) if sl else '-'} |")
txt = "\n".join(rows)
(R/"findings"/"04_target_vtable_slots.md").write_text("# Vtable slots of plugin-used functions (installed CLOAPIInterface.dll)\n\n*Slot numbers include the extra vtable entries MSVC emits for overloaded functions; byte offset = slot*8.*\n\n"+txt+f"\n\nUnresolved (export-name lookup lost to identical-code-folding of stubs): {missing}\n", encoding="utf8")
print(txt); print("missing", missing)
