# Exe implementations: Utility / Import / Export target functions

*Status: static disassembly (dumpbin), CLO_Standalone_OnlineAuth_x64.exe 2026.1.336, first-level only*
*Date: 2026-10-29*
*Tooling: `scripts/disasm_fn.py <RVA>` (annotated summary, `--full` for listing), `scripts/disasm_view.py <RVA>` (compact view). Raw dumps cached in `raw/disasm/<rva>_<size>.txt`.*

Conventions: addresses are RVAs (VA = 0x140000000 + RVA) unless written 14xxxxxxx. "Confidence" is about the pseudo-code; anything marked *(inference)* is not directly visible in the listing. All functions are MSVC x64 (`rcx=this`; a by-value `std::string`/`ImportExportOption` is passed as a pointer to a caller-made copy and **destroyed by the callee**; a function returning `std::string`/`std::vector` gets a hidden return pointer in `rdx`).

## 0. Common building blocks (shared by every function below)

| RVA | What it is | Evidence |
|---|---|---|
| 0x4e10dd0 | `Logger::Instance()` (function-local static, TLS-guarded init, stored at .data 0xa319f40) | 29-instruction Meyers singleton |
| 0x4e10fb0 | `Logger::Log(level, std::string msg, src-info)`; does nothing if `byte [logger+0x28]==0` | `cmp byte ptr [rcx+28h],0; je ret` |
| 0x5ef27e0 | builds the source-location/context arg for the log call | called right before the log |
| 0x1be0ec0 | `App::Instance()` singleton at .data 0xa2a47d0. `[app+0x30]` is a "main document/window present" pointer, `[app+0x38]` is an object with a **vtable** that does the real work (open/import/save). `[app+0x60]` is another object. | used by NewProject, Import*, ExportZPrj, ExportGLTF (via 0x60a5090) |
| 0x1bf5d20 | `AvatarManager::Instance()` singleton at .data 0xa2a5380 (ctor 0x50889b0) | used by DeleteAvatar, Import(Avatar/Measurement), Get/SetAvatarProperties, GetAvatarCount/NameList/GenderList |
| 0x50ccb70 / 0x50db800 | `AvatarManager::GetAvatarList()` -> `vector<shared_ptr<Avatar>>` (16-byte elements, refcount at `[ctrl+8]/[ctrl+0xC]`) | DeleteAvatar loop, Get* loops |
| 0x66668a0 | `std::string (UTF-8) -> wide/Qt string` conversion; 0x6668370 is the reverse (wide -> UTF-8 `std::string`) | used on every path argument / returned path |
| 0x40ef3a0 | wide string -> filesystem-path object | after 0x66668a0 |
| 0x40ed340 | `path -> extension string` (no leading dot; "" if empty) | feeds the extension compare |
| 0x6666560 | **tail-jump through IAT 0x822f1b8** with `(str+8, str+8, flag)`; behaves as `compare(a, b, caseSens)` returning 0 on equal. Called with flag=0 everywhere. *(inference)*: this is a Qt `QString::compare(..., Qt::CaseSensitivity)` where 0 = `Qt::CaseInsensitive`, i.e. extension checks are probably case-insensitive. | `add rdx,8; add rcx,8; jmp [..]` |
| 0x6664f70 | construct string from literal ("avt", "csv", ...) | |
| 0x6665040 | string destructor; 0x70d91b8 = operator new, 0x70d91f4 -> 0x1470d9060 = operator delete, 0x70d9780 = `__security_check_cookie` | |
| 0x6268a40 | **`IsHeadless()`**: builds a `QCommandLineParser`-style object, registers an option named `"headless"` with help text `"Run python file at <file>."`, processes the app arguments and returns `isSet("headless")`. | strings at 0x8414f08 / 0x8414f18, IAT calls 0x822e1b0.. |

Every API wrapper starts with the same prologue: build the `__FUNCSIG__` string of the function (e.g. `bool __cdecl Marvelous::ImportAPI::ImportAvatar(class std::basic_string<...>,class Marvelous::ImportExportOption)`), call `Logger::Log(level, msg)`, then run. Log level: 0 for ExportGLB/ExportGLTF, 1 for ImportAvatar/ImportFile, 2 for NewProject/Simulate/DisplayMessageBox/Get-SetAvatarProperties/DeleteAvatar. *(inference)*: 0 = debug/trace, higher = info; the log is only written if the logger is enabled. There is **no** main-thread or GUI-thread assertion anywhere in these wrappers (no `GetCurrentThreadId`/`QThread::currentThread` compare was seen at this level). Exceptions: none of the wrappers contains a visible try/catch (SEH/C++ handlers are registered in `.pdata`, not in the body); stack-protector cookie only.

---

## UtilityAPI

### NewProject (slot 55) - RVA 0x60342c0, `void NewProject()`
*Confidence: high for the call sequence, medium for the meaning of each callee.*
```
log(2, "void __cdecl Marvelous::UtilityAPI::NewProject(void)")
app = App::Instance()
if (app->[0x30] != 0) {                  // 0x14603442D..37
    app->[0x38]->vtbl[3]();              // call [rax+18h]  (inference: "new/clear document")
    app->[0x60]->vtbl[1]();              // call [rax+8]
    s = Singleton_0x1c5fb60();           // string "NULL" (0x4C4C554E) passed to 0x5d827f0(s, "NULL")
}
return;                                  // void, nothing reported to the caller
```
- Early return: only the `[app+0x30]` null check (silently does nothing, still returns).
- Global state: App singleton (a2a47d0), singleton from 0x1c5fb60 receives the literal string `"NULL"` *(inference: resets the "current file name" to NULL)*.
- No unsaved-changes prompt is visible at this level; whether `vtbl[3]` prompts is unknown (second-level).

### Simulate (slot 85) - RVA 0x607f070, `bool Simulate(unsigned int steps)`
*Confidence: high.*
```
log(2, "bool __cdecl Marvelous::UtilityAPI::Simulate(unsigned int)")
sim = Singleton_0x1c23080()
0x5cbfb40(sim, 1, 0, 0, 0)               // start/enable simulation (edx=1, r8b=1, r9=0, [rsp+20]=0)  (inference)
for (i = 0; i < steps; ++i)              // 0x14607F235 loop, counter in rbx = edi
    0x5cc1fc0(&static_a2a6c40)           // one solver step on a function-local static (TLS-guarded init 0x5cb5d70)
0x5cbfb40(sim, 0, 0, 0, 0)               // stop simulation (edx=0)
0x5ccd3a0(Singleton_0x1be1040())         // post-sim refresh/finalize
return true;                             // mov al,1  (0x14607F294) - ALWAYS true
```
- No null/GUI checks at all: `Simulate(0)` just starts then stops the sim. It always returns `true`, so a `true` return carries no information about convergence.
- Global state: simulation singleton (0x1c23080), static solver object at .data 0xa2a6c40 (init guard 0xa2a7320).

### DeleteAvatar (slot 264) - RVA 0x5fad0e0, `bool DeleteAvatar(std::vector<int> indices)`
*Confidence: high.* The vector is passed by value (pointer in rdx, `r14`), destroyed at the end.
```
log(2, ...DeleteAvatar(class std::vector<int,...>))
avatars = AvatarManager::Instance()->GetAvatarList()        // 0x50ccb70
if (avatars.empty() || indices.empty()) return false;        // 0x145FAD2B8 / 2C8 -> 79c -> xor al,al
selected = []
for idx in indices: if (0 <= idx < avatars.size()) selected.push_back(avatars[idx])   // loop 0x145FAD300..387, shared_ptr copy (lock inc [ctrl+8])
if (selected.empty()) return false;                          // 0x145FAD391 cmp rcx,rdx ; je ... -> false (out-of-range indices only)
AvatarManager::Instance()->0x50c00b0(&selected)              // actual removal
return true;                                                 // mov al,1 at 0x145FAD5E5
```
- Out-of-range indices are silently skipped; if *none* is valid the result is `false`. The return of 0x50c00b0 is ignored, so `true` only means "at least one valid index was passed".
- Global state: AvatarManager singleton.

### SetAvatarProperties (slot 349) / GetAvatarProperties (slot 350) - RVA 0x6041900 / 0x5fd59f0
*Confidence: medium-high (key names and error text verified; per-key setter semantics are second-level).*
`void SetAvatarProperties(unsigned avatarIndex, const std::map<string,string>& props)` and `std::map<string,string> GetAvatarProperties(unsigned avatarIndex)`.
```
log(2, ...)
mgr = AvatarManager::Instance()
avatar = lookup(index)                     // 0x50d1640; if missing:
    print "[Python] Please Load Avatar"    // string 0x89a6a30 "Please Load Avatar" with prefix "[Python]" (0x8862210); NOT an exception, nothing is set / empty map returned
    return
// Get: returns a map with exactly these keys:
//   "StaticFriction", "KineticFriction", "SkinOffsetMM", "DivideMesh", "SoftBodySimulation"
//   (strings at 0x89ae9c0, 0x89ae9d0, 0x89ae9e0, 0x89aec40, 0x89aec50)
// Set: walks the map (RB-tree walk, node+0x19 = isnil) and handles only these keys:
//   "StaticFriction"  (len 14, memcmp-style compare 0x70de9f0) -> std::stof(value) -> setter 0x5132bf0
//   "KineticFriction" (len 15) -> std::stof(value) -> setter 0x512d920
//   "SkinOffsetMM"    (len 12, cmp r14,0Ch) -> std::stof(value) -> setter 0x51319c0 (+ 0x1c59150 check)
//   other keys are ignored silently (including DivideMesh / SoftBodySimulation: NOT settable here)
```
- **Error behaviour that matters:** values go through `std::stof`. The throw stubs `"invalid stof argument"` (0x885ece0) and `"stof argument out of range"` (0x885ecf8) are inlined at 0x14604207x. A non-numeric value therefore raises a C++ exception out of the plugin call (no handler visible in the wrapper) - *(inference)* this can terminate/crash CLO instead of returning an error. Always send well-formed decimal strings.
- Values are unitless strings; SkinOffsetMM is millimetres by name.
- NOTE: the disassembly window of 0x6041900 also swallowed the adjacent function `UtilityAPI::SetAvatarSmooth(unsigned,unsigned)` (starts ~0x14604214x; string "Subdivision is not available when Soft Body Simulation is checked."). That text belongs to SetAvatarSmooth, not SetAvatarProperties.
- Get side branch: `if (!App?->0x61548b0())` skip - a second guard (`0x1be0ec0` -> `0x61548b0` must be non-null) before reading avatar data *(inference: "scene/document available")*.

### DisplayMessageBox (slot 2) - RVA 0x5fb0260, `void DisplayMessageBox(std::string text)`
*Confidence: medium-high.* (The following function in the same window is `DisplayMessageBoxW`, RVA ~0x5fb04c0; not analysed.)
```
log(2, "void __cdecl Marvelous::UtilityAPI::DisplayMessageBox(std::string)")
w = utf8_to_wide(text)                     // 0x66668a0
0x4b6be20(w)
// 0x4b6be20:
//   ui = Singleton_0x1be0fc0()   (.data a2a49e0)
//   if (ui->[0x10] && ui->[0x10]->vtbl[4]())      // e.g. "is a progress/wait dialog showing"
//        ui->[0x10]->vtbl[2](0)                    // close/hide it
//   tail-jmp 0x4b78600(w, -1, 0)                   // show the (modal) message box
```
- The only guard is a null check on the UI delegate `ui->[0x10]` (if null the box call still happens). No headless check here -> *(inference)* in `--headless` mode the call may still try to open a modal Qt dialog and **block forever**. Avoid from automation.

---

## ImportAPI

All Import wrappers return `bool`. Pattern: build wide path -> check extension (where applicable) -> delegate. Two families:
(a) "document" imports go through `App::Instance()->[0x38]->vtbl[N](wpath, options)` and are guarded by `[app+0x30] != 0`.
(b) "avatar" imports go straight to `AvatarManager` with **no** `[app+0x30]` guard.

### ImportFile(path, const ImportExportOption&) (slot 1) - RVA 0x6022e80
*Confidence: high.*
```
log(1, "bool ImportFile(const std::string&, const Marvelous::ImportExportOption&)")
if (App::Instance()->[0x30] == 0) return false;           // xor al,al at 0x1460230AE
wp = to_path(utf8_to_wide(path))
return App::Instance()->[0x38]->vtbl[31 /*+0xF8*/](wp, &options);   // r8 = options pointer
```
No extension check at this level - the vtbl[31] callee dispatches by extension *(inference)*.

### ImportFile(path) (slot 2) - RVA 0x6022a80
*Confidence: medium (branch structure verified, meaning of 0x3bb3640/0x666b680 is inference).*
```
log(1, "bool ImportFile(const std::string&)")
if (App::Instance()->[0x30] == 0) return true;            // NOTE: returns TRUE (mov al,1 at 0x146022E4D) without doing anything
wp = to_path(utf8_to_wide(path))
if (IsHeadless()) {                                       // 0x6268a40
    App->[0x38]->vtbl[32 /*+0x100*/](wp)                  // direct open/import, no dialogs
} else {
    ext = extension(path)
    if (0x3bb3640(ext-derived-path)) { ... build list, call function pointer rsi(...) ... }   // (inference) GUI-mode handling for known project/zip types
    else App->[0x38]->vtbl[32](wp)
}
ext = extension(path)
if (ext compare "zprj" == 0)                              // "zprj" at 0x82608a0
    App->[0x38]->vtbl[44 /*+0x160*/](wp)                  // extra step after a .zprj load (inference: register in recent-files / set project name)
return true;
```
- Unlike slot 1 this overload "succeeds" (true) even when no document pointer exists, and its return value does not reflect load success. Prefer checking state afterwards.

### ImportOBJ (slot 11) - RVA 0x6025820
*Confidence: high.* `[app+0x30]==0 -> false`; else `return App->[0x38]->vtbl[34 /*+0x110*/](wpath, &options)`. No extension check.

### ImportDXF (slot 21) - RVA 0x6021f40
*Confidence: high.*
```
if (App->[0x30]==0) return false;
ext = extension(path)
ok = (ext cmp "dxf" == 0) || (ext cmp "aama" == 0)       // 0x825e29c, 0x8290e9c  (AAMA grading-pattern DXF)
if (!ok) return false;
return App->[0x38]->vtbl[37 /*+0x128*/](wpath, &ImportDxfOption);
```
Extensions validated: `.dxf`, `.aama`.

### ImportAvatar (slot 37) - RVA 0x6021080
`bool ImportAvatar(std::string avtPath, Marvelous::ImportExportOption opt)` - both parameters by value.
*Confidence: high for the flow, high for the destructor evidence, medium for the crash-cause inference.*
```
log(1, "bool ImportAvatar(std::string, Marvelous::ImportExportOption)")
if (extension(wpath) cmp "avt" != 0) { destroy(path); destroy(opt); return false; }   // 0x1460212C0..301, string "avt" at 0x82607b0
imp = ImportParams();                       // 0x50888e0 (local struct)
imp.<byte at rbp-44h> = opt[+0xB5]          // movzx [rsi+0B5h]
imp.<byte at rbp-33h> = opt[+0x49]          // movzx [rsi+49h]
imp.pos/scale floats = opt[+0xB8], opt[+0xBC], opt[+0xC0]   // movss x3
r = AvatarManager::Instance()->0x50e3fc0(wide_path, imp);   // the real import (second-level)
destroy(path);              // 0x1baa170
destroy(opt);               // 0x1d7a070 = ~ImportExportOption
return r;
```
- Only `.avt` is accepted (and only a case/locale-insensitive compare *(inference)*): `.avs` or `.obj` => `false` before anything is touched.
- **No** `[app+0x30]` guard, no headless check: it dives straight into `AvatarManager`. If the manager/scene is not ready the failure shows up as a crash rather than `false`.
- ImportExportOption field offsets seen being read: `+0x49` (byte), `+0xB5` (byte), `+0xB8/+0xBC/+0xC0` (floats). `[0xB8..0xC0]` are probably the avatar position/size vector, `0xB5` and `0x49` boolean toggles (e.g. `bSizeAndPoseFromAvatar`) *(inference; names not verified)*.

**Why a plugin built against the wrong SDK can crash CLO inside ImportAvatar** (all supported by the disassembly, final causal chain is inference):
1. `ImportExportOption` is passed **by value**: the plugin builds the object (SDK-sized) and hands the exe a pointer. In 336 the object is at least 0x128 bytes long (last vector ends at +0x128) and has 4 new `std::vector`s at `+0xC8` (patternList), `+0xE0` (buttonList), `+0xF8` (graphicList), `+0x110` (zipperList). `0x60a5090` (ExportGLTF) confirms these offsets (it tests `[opt+0xC8]==[opt+0xD0]`, `+0xE0/+0xE8`, `+0xF8/+0x100`, `+0x110/+0x118`), and `~ImportExportOption` (0x1d7a070) frees `[+0x110]`, `[+0xF8]`, ... with `operator delete` and zeroes the triple.
2. The **callee** destroys the by-value parameter (0x146021380..AD: `call 0x1d7a070` on `rsi`=r8 at the end of the function, also on the early failure path). With an SDK-224 plugin the object is shorter, so the exe reads/destroys vectors from memory past the end of the plugin's object (stack/heap garbage) -> `delete` of a wild pointer -> heap corruption / access violation. It can also read `+0xB5..+0xC0` from the wrong place.
3. Independently, vtable slots moved for the grown classes (Utility 401->408, Export 119->124, Pattern 217->233 per findings/04); ImportAPI's own slot count was not reported as changed, so this is a secondary risk for Import* but applies to every Utility/Export call in a mismatched build.
4. A mismatched `std::string` ABI is not a concern (same MSVC STL layout), but note the exe frees the plugin's string buffer, so plugin and exe must share the CRT heap (both use the UCRT, fine).
=> Always build the plugin against SDK 336 for CLO 336 (consistent with `project_clo_app_sdk_version_match`).

### ImportAvatarMeasurement (slot 36) - RVA 0x6021400
`bool (std::string csvPath, std::string avtPath, ImportExportOption opt)` all by value. *Confidence: medium-high.*
```
log(1, ...)
require extension(csvPath)=="csv" AND extension(avtPath)=="avt"     // "csv" 0x8331ad8, "avt" 0x82607b0; any mismatch -> false
imp = ImportParams(); copy fields from opt as ImportAvatar
return AvatarManager::Instance()->0x50e41a0(wide(avtPath)... , wide(csvPath)..., imp);   // r8=rbx,r9=rdi
// all three by-value args are destroyed on every path (0x1baa170 x2, 0x1d7a070)
```
Same by-value `ImportExportOption` crash exposure as ImportAvatar.

### ImportMeasurement (slot 38) - RVA 0x6025560
`bool ImportMeasurement(std::string csvPath)`. *Confidence: high (the headless gate was verified twice).*
```
log(1, ...)
if (!IsHeadless()) return false;          // 0x146025736..3D: call 0x6268a40; test al,al; je -> xor al,al
if (extension(path) cmp "csv" != 0) return false;
return AvatarManager::Instance()->0x50e4d80(wide_path);
```
**Notable: unless CLO was started with the `headless` command-line option, `ImportMeasurement` returns false without doing anything.** (This is consistent with "measurement apply" only working through the other route in GUI mode.) `ImportFile(path)` (slot 2) is also branch-dependent on `IsHeadless()`.

---

## ExportAPI

### ExportGLTF (slot 13) vs ExportGLB (slot 78) - RVA 0x5fb7f50 / 0x5fb75d0
*Confidence: high (both bodies are 200 instructions of the same shape).*
Signature: `std::vector<std::string> ExportGLTF(const std::string& path, const ImportExportOption& opt, bool bGLBinary)` and `... ExportGLB(const std::string& path, const ImportExportOption& opt)`. Hidden return pointer in rdx, `rcx=this`, `r8=path`, `r9=opt`, `bGLBinary` on the stack (`[rbp+7Fh]`, read into `r12b`).

Both do:
```
log(0, "<FUNCSIG>")                         // ExportGLB sig at 0x8973fd0, ExportGLTF sig at 0x896f0d0
wp = utf8_to_wide(path)
files = this->0x60a5090(wp, /*mode=*/0, &opt, /*bGLBinary=*/X)    // 0x60a5090(this, &out, wp, r9b=0, [rsp+20]=opt, [rsp+28]=X)
result = for f in files: utf8(f)  -> vector<string>
return result
```
**The only difference:** ExportGLB hard-codes `X = 1` (`mov byte ptr [rsp+28h],1` at 0x145FB77B2) whereas ExportGLTF forwards the caller's `bGLBinary` (`mov byte ptr [rsp+28h],r12b` at 0x145FB8139). So **`ExportGLB(p,o) == ExportGLTF(p,o,true)`** exactly; there is no separate GLB code path in the wrapper and the options object is not changed. `ExportGLTF(p,o,false)` writes text glTF (`.gltf` + `.bin` + images).

Inside the shared worker 0x60a5090 (second level, for reference):
- `app = App::Instance(); if (app->[0x30]==0) return empty vector;`  (no document -> empty result, not an error)
- If all four component lists in `opt` (`+0xC8 patternList`, `+0xE0 buttonList`, `+0xF8 graphicList`, `+0x110 zipperList`) are empty -> whole-scene path: `app->[0x38]->vtbl[19 /*+0x98*/](out, wp, mode r9b, &opt, bGLBinary)`.
- Otherwise -> selection path: builds a selection (0x5cfe9f0, 0x6099710 resolving the lists), returns an empty vector if the resolved selection is empty, else uses a format enum `bGLBinary + 2` (so 2 = glTF, 3 = GLB; `lea edx,[r15+2]` at 0x1460A5335) and `app->[0x38]->vtbl[18 /*+0x90*/]` *(inference on the format-enum meaning)*.
- Output file naming default `"output.gltf"` (0x8984e88) appears in neighbouring functions (the later windows 0x145FB8AB7), not in these two wrappers.
- No extension validation is performed on `path` in either wrapper; CLO decides the extension from `bGLBinary` *(inference: pass a path without relying on the suffix)*.

Pitfall: an empty returned vector means "no document" or "nothing selected/exported"; it never throws.

### ExportAVT (slot 102) - RVA 0x5fb2740, `std::string ExportAVT(const std::string& path)`
*Confidence: medium.*
```
log(?, sig @0x8975780)
wp = utf8_to_wide(path)
res = this->0x60a42f0(wp)          // worker: extension "avt" appended/forced via 0x40eafc0(path,"avt") (string 0x82607b0),
                                   // AvatarManager singleton, avatar list (0x50db800), current-avatar checks (0x50d1640, 0x50ef2f0, 0x50f0900) ;
                                   // on any failed check it returns an empty path (strings rdata "") 
return utf8(res)                   // returned path ("" on failure)
```
Returns the written file path or an empty string.

### ExportZPrj (slots 4 `(path,bool)`, 5 `(path)`, 6 `()`) - RVA 0x5fcb040 / 0x5fcae00 / 0x5fcb290
*Confidence: high.* All three funnel into `0x60a8050(this, &outString, wpath, bFlag)`:
- slot 6 `()` builds `path = <temp dir from 0x40eebc0> + "output.zprj"` (0x896e088, joined by 0x66655a0), `bFlag=1`.
- slot 5 `(path)` passes `bFlag=1` (`mov r9b,1` at 0x145FCAFE3).
- slot 4 `(path, bool)` passes the caller's bool (r15b).
```
0x60a8050:
  if (App::Instance()->[0x30]==0) { out = ""; return out; }       // no document -> empty string
  App->[0x38]->vtbl[8 /*+0x40*/](wpath, bFlag)                     // save project
  if (bFlag) App->[0x38]->vtbl[14 /*+0x70*/](wpath, 900, 900)      // 0x384 x 0x384: (inference) thumbnail/preview written next to the project
  out = path; return out
```
Return value = the path string (identical to the input), "" if no document.

### GetAvatarCount (slot 71) - RVA 0x5fd3920, `unsigned int GetAvatarCount()`
Gets `AvatarManager::Instance()` list (0x50db800) and returns its size (`count`, compared against `r14` index in the loop - the function copies the list twice, and returns the count of entries). *Confidence: medium-high.* No other guards; 0 with an empty scene.

### GetAvatarNameList (slot 72) - RVA 0x5fd4880, `std::vector<std::string> GetAvatarNameList()`
For each avatar in the list: `avatar = 0x1d73760(sp)`, then `avatar->vtbl[22 /*+0xB0*/](&wname)` -> utf8 (0x6668370) -> `push_back`. Returns names in list order. *Confidence: medium-high.*

### GetAvatarGenderList (slot 74) - RVA 0x5fd3d20, `std::vector<int> GetAvatarGenderList()`
Same loop; per avatar the gender comes from `0x50d3ad0`/`0x1d33390` (int) pushed to the vector. *Confidence: medium; the integer encoding of gender is not visible at this level.*

---

## Cross-cutting takeaways
1. **Headless gate:** `0x6268a40` = "was CLO started with `headless`". `ImportMeasurement` is a no-op (returns false) without it; `ImportFile(path)` takes a different branch.
2. **Document guard:** `ImportFile(opt)`, `ImportOBJ`, `ImportDXF`, `ExportZPrj`, `ExportGLTF/GLB` all depend on `App::Instance()->[0x30] != 0`; when it is null they return `false` / `""` / `{}` quietly (ImportFile(path) returns **true**).
3. **No main-thread assertions** are present at wrapper level; thread-safety is by the caller (plugin `DoFunction` is run from the GUI thread).
4. **Extensions validated in-process:** `.avt` (ImportAvatar, ImportAvatarMeasurement), `.csv` (ImportMeasurement, ImportAvatarMeasurement), `.dxf` / `.aama` (ImportDXF), `.zprj` (post-step in ImportFile(path)). OBJ / generic ImportFile(opt) and the exports do not validate.
5. **By-value args are destroyed by the callee**, so any struct-layout mismatch (ImportExportOption 224 vs 336) is a crash, not an error code.
6. Return values: `Simulate` always `true`; `DeleteAvatar` true iff at least one valid index; `ImportFile(path)` true when there is no document; Export* return empty containers on failure.
7. Not analysed (second level): the callee bodies 0x50e3fc0 / 0x50e41a0 / 0x50e4d80 (actual avatar import/measurement application), App vtable methods, 0x60a42f0 (AVT writer).
