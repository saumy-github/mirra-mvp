# Measurement import / avatar size apply / AVT writer internals (lane H)

*Status: static disassembly only (dumpbin), CLO_Standalone_OnlineAuth_x64.exe 2026.1.336; nothing was run*
*Date: 2026-10-29*
*Scripts added: `scripts/measure_map_extract.py` (first-pass extractor, see caveat in 2.3), `scripts/xref_rip.py` (finds `lea reg,[rip+x]` xrefs to .rdata RVAs). Raw dumps cached in `raw/disasm/`.*

Conventions as in findings/11: addresses are RVAs (VA = 0x140000000 + RVA). Tags: **[V]** verified directly in the listing, **[I]** inference (not directly visible). `AvatarManager` = singleton from 0x1bf5d20.

## 0. Summary of conclusions

1. `ImportAvatarMeasurement(csv, avt, opt)` = `ImportAvatar`-worker (0x50e3fc0) on the .avt, then `ImportMeasurement`-worker (0x50e4d80) on the csv. [V] (0x50e41a0 is only a 124-instruction glue function.)
2. The CSV is a **3-column comma CSV: `Name,Type,Value`**. Line 1 is read and discarded, line 2 must look like `Something(unit)`, rows from line 3 on are `Name,Type,Value`. The row key is `Name + "_" + Type` and is looked up in a per-avatar hash map (41 keys, section 2.3) that yields the feature index (0..66). [V for the code path, I for the exact line-1/line-2 layout, see 1.4]
3. Values are converted from the unit declared in line 2 to **cm** and stored into a float[67] (0x43). No half/full-girth conversion happens; values are stored as given. [V]
4. After parsing, CLO needs a non-zero Total Height (idx 0) and non-zero Bust (idx 2, male) or Under Bust (idx 5, female), otherwise the import fails with a log message. [V]
5. The measurements are applied by feeding a global "avatar size manager" (singleton 0xa320338, ctor 0x508dcb0, 0x86B80 bytes) and then calling `0x50a0f70(avatar, 0)`, which re-sizes the avatar (the same code path the GUI "Size" panel uses). So the mesh **is** re-deformed on this route, in contrast to the plugin's `avt_patch` route that just rewrites floats in the .dan. [V for the call chain, I for "re-deforms the mesh" because the deformation kernels (0x513f190, 0x51945e0, 0x5146a40) were not read]
6. Gender/template matters: the avatar's template name is mapped to a gender/profile int by 0x50d3680 and that selects which of two mandatory measurements is required and which index is made the "driver" (Bust for male, Under Bust for female). The size manager also has a per-profile table (stride 0x8F20). [V]
7. `ExportAVT` worker 0x60a42f0 only validates, forces a ".avt" extension and hands the first avatar to a serializer at 0x511f4f0; the header/ZIP layout of findings/10 is produced further down (0x3a03bf0 and the 0x39f.. writer), **not decoded**. [V for the worker, unknown below]

---

## 1. ImportMeasurement worker `AvatarManager::0x50e4d80(std::string& wpath)`  (RVA 0x50e4d80..0x50e5bed, 872 instr.)

Called from `ImportAPI::ImportMeasurement` (0x6025560, headless-only, extension `csv`) and from the glue 0x50e41a0. `rdx` = pointer to the path string (a wide/QString-converted-to-std::string path; the function empties it, `[rsi+0x10]=0; [rsi]=0; [rsi+0x18]=0xF`, on exit [V]).

### 1.1 Control flow (annotated)
```
avatar = AvatarManager::0x50d1640(&sp)          // first/current avatar, shared_ptr in [rsp+30h]    [V]
if (!avatar->isCloAvatar())                       // 0x50f2010: movzx eax, byte [rcx+0x990]            [V]
    log "Only CLO Avatar is allowed." ; return false                                                  [V] 0x50e4dfa
vals = vector<float>(0x43 /*67*/)                 // 0x39acc70(&vec, 0x43, &zero)                       [V]
ifstream f(path)                                  // 0x2994640 (basic_ifstream ctor, mode=1 in)         [V]
if (!f.is_open()) { log "File Open Failed."; return false }   // 0x50e4f1c
getline(f, line)                                  // 0x3153070   line 1 DISCARDED                       [V]
getline(f, key,  '(')   // 0x28                    // text before '('  (ignored, overwritten)           [V]
getline(f, unitStr, ')')// 0x29                    // text between '(' and ')'  -> unit                [V]
getline(f, line)                                  // rest of line 2 discarded                           [V]
unit = parseUnit(unitStr)                         // table below                                        [V]
while (f.good()):                                 // loop head 0x50e51a2
    getline(f, line); istringstream ss(line)      // 0x822bfb0 = stringstream ctor                      [V]
    getline(ss, a, ','); getline(ss, b, ','); getline(ss, c, ',')     // three 0x2c delimited tokens   [V]
    v = stod(c)                                   // throws std::invalid_argument / out_of_range        [V] strings @0x50e5be6/d9
    idx = avatar->0x50d9250(a, b)                 // looks up key a + "_" + b, returns 0x43 if missing  [V]
    if (idx < 0x43) vals[idx] = convert(v, unit -> cm)   // 0x625bda0(&v, unit, 3)                       [V]
    // unknown keys (idx==0x43) are silently ignored                                                    [V]
```
Note the *whole file* is parsed before any check, so a bad number in a later row (`stod` exception, not caught in this function) aborts the call after the file was opened. [V: no handler in the body; *I*: exception escapes to the caller]

### 1.2 Units (`unitStr` -> unit code)  [V]
The compares are `memcmp` (0x70de9f0, case **sensitive**) after a length check. Code `rbx = strlen`, `r13` = result:

| unitStr | length test | unit code | factor to mm (0x625bda0 table) |
|---|---|---|---|
| `m` (rdata 0x825e704) | len 1 | 0 | 1000.0 (0x82bda88) |
| `feet` (0x890f7dc) | len 4 | 1 | 304.8 (0x83752a0) |
| `inch` (0x828c0b0) | len 4 | 2 | 25.4 (0x8291f60) |
| `cm` (0x825e6f4) | len 2 | 3 | 10.0 (0x8269b44) |
| `mm` (0x825e6e0) | len 2 | 4 | 1.0 (0x82703f8, the `else` factor) |
| (anything else) | | **0 = meters** | |

(`0x825e6e0`.. also contain the long names "Meters", "Centimeters", "Millimeters" next to the short ones, but only the short strings are compared by this function.)
`0x625bda0(float* v, int from, int to)` returns `v * factor[from] / factor[to]`; the importer always passes `to = 3` (cm), so **internal storage unit is cm** [V]. Code 7 exists in the converter with factor 914.4 (yard) but the CSV parser cannot produce it.
**Gotcha:** a unit string that is not exactly `m`, `feet`, `inch`, `cm`, `mm` (including `CM`, `cm `, `Centimeters`, or a missing `(...)`) falls through to code 0 = **meters**, so a 170 would be treated as 170 m (-> 17000 cm), later clamped (section 3). [V: `mov r13d,[rsp+40h]` with that slot = 0 on the fall-through]

### 1.3 Post-parse checks and application (after the loop, 0x50e557a..)
```
gender = AvatarManager::0x50d3680( avatar->0x50ca3b0() )   // avatar template/name string at avatar+0x530 -> int        [V]
hasH   = vals[0] != 0          // [r14]      Total Height
hasBust= vals[2] != 0          // [r14+8]    Bust circumference
hasUB  = vals[5] != 0          // [r14+0x14] Under Bust circumference
if (!hasH)                         { log "Avatar size needs total height."; return false }                          [V] 0x50e561c
if (gender==1 && !hasUB)           { log "Avatar size needs the circumference of underbust for female."; return false } [V] 0x50e57c9
if (gender!=1 && !hasBust)         { log "Avatar size needs the circumference of bust for male."; return false }       [V] 0x50e57d9
// "return false" = `xor al,al` path; the logger is the 0x1d68810/[0x822be88] stream-style call, not Logger::Log.
mgr = SizeManager::Instance()  (0x50d6060, .data 0xa320338, new 0x86B80 bytes, ctor 0x508dcb0)
sizeObj = temp (0x2e96bb0 with 0x50cab40(avatar)= avatar+0x990 ; copy of vals vector via 0x1f00fc0)
for i in 0..66: mgr->0x512d2a0(i, 0)                       // reset "measure mode" of every feature to 0       [V]
for i in 0..66 where vals[i] != 0:                         //                                                    [V]
    t = mgr->0x50d8a30(i)                                   // feature "type" = [mgr + [mgr+0x18]*0x8F20 + i*0x210 + 0x599B8]
    mode = 2
    if (t > 1) mode = i + 4
    if (t == 8 || i == 58 || i == 59) mode = i + 5          // (i-0x3a <= 1)
    mgr->0x512d2a0(i, mode)                                 // set measure-mode / link entry for i
mgr->0x512d2a0(0, 3)                                        // Total Height gets mode 3                          [V]
mgr->0x512d2a0(gender==1 ? 5 : 2, 1)                        // Under Bust (female) / Bust (male) gets mode 1     [V]
mgr->0x5148d70()                                            // commit/prepare modes (calls 0x5193b80, 0x6822210..) [V call list, I meaning]
for i: if vals[i]!=0: mgr->0x512d3a0(i, vals[i])            // SetFeatureValue (clamped, section 3)               [V]
mgr->0x51449e0(1, 1)                                        // recompute pass #1 (mode 1)
for i: if vals[i]!=0: mgr->0x512d3a0(i, vals[i])            // set values AGAIN after pass #1                     [V]
mgr->0x51449e0(2, 0)                                        // recompute pass #2 (mode 2)
avatar->0x50a0f70(0)                                        // APPLY SIZE TO AVATAR (section 4)
if (App::Instance()->[0x30]) { App->[0x60]->vtbl[3](1,1); App->[0x30]->vtbl[0x78/8=15](); ...[0x48/8=9](); ...[0x20/8=4]() }   // refresh/redraw hooks [V calls, I meaning]
return true
```
Consequences: (a) there is a **two-stage solve**: values are written, a "mode 1" pass derives the dependent measurements, values are written again, then a "mode 2" pass runs; so the final stored floats are not simply the CSV numbers for the dependent features (matches findings/10 section 3.1: 51 other floats change). (b) Measurements missing in the CSV (0.0) are *not* reset; only features with a non-zero value are set, everything else is derived. (c) A value of exactly 0 can never be applied. [V]

### 1.4 What is verified vs inferred about the file layout
- [V] Reads line 1 and throws it away; reads line 2 with delimiters `(` and `)`; the unit is the text between them; the rest of line 2 is thrown away; every following line is split on `,` into >= 3 fields; only fields 1,2 (key) and 3 (value) are used; extra columns are ignored by construction.
- [I] A plausible file is therefore:
  ```
  Name,Type,Value                       <- line 1, any text (discarded)
  Unit(cm)                              <- line 2, text before "(" is ignored, "cm" is the unit
  Total Height,Height,170
  Bust,Circumference,92
  Waist,Circumference,78
  ...
  ```
  I never saw a CLO-written example; the writer (the Size dialog "Export measurements" function) was not located (searched .rdata for `Unit(`, `(cm)` and `%s(%s)`, no match for a CSV header writer). The repo's `clo_avatar_generation/schema/measurement_template_unconfirmed.csv` (`Total Height,Weight,Waist,...` as a wide row) **does not match** this parser: it would be read as line 1 discarded, line 2 `170,65,78,...` has no `(`, so `getline(f,key,'(')` swallows everything to EOF, the unit falls to meters and nothing is parsed -> "Avatar size needs total height." [V by control flow, I by example].
- No header-name check: line 1 can be anything (even empty). A UTF-8 BOM would only affect line 1, which is discarded. Line endings: `getline` on a text-mode ifstream; a `\r` left in a token would break key matching only if the file is opened in binary mode (mode argument `1`=in, text) - *(inference: CRLF is fine)*.
- Empty / short lines: the third token would be empty -> `stod("")` throws `invalid stod argument`. A trailing blank line at the end of the file is therefore dangerous. [V that stod is called unguarded; I that a blank last line triggers it, because the loop condition is `f.good()` evaluated *after* the next getline - the final getline that hits EOF leaves `failbit` and exits before the token split, so a single trailing newline is OK, but a blank line before EOF is not]

---

## 2. Key lookup `Avatar::0x50d9250(this, name&, type&) -> int`  (RVA 0x50d9250)

```
key = name + "_" + type                                      // builds std::string; byte 0x5F at +len(name) [V]
h   = hash(key)         // 0x1d00bb0 (FNV-1a/CityHash-like, not decoded)
bucket = this->[+0x10F8][ (h & this->[+0x1110]) * 2 ]        // MSVC std::unordered_map<std::string,int> layout [I]
walk nodes, compare with memcmp (0x70de9f0)  // case SENSITIVE   [V]
return found ? node->[+0x30] : 0x43                          // 0x43 = "not found" sentinel [V]
```
So keys are **case-sensitive and must match exactly** (e.g. `Total Height` + `Height`).

### 2.1 Where the map is filled
The map (`this+0x10E0` list/unordered_map, built with `0x50877d0` from a temp initializer array of 41 `{std::string key; int idx;}` nodes (0x28 bytes each, stride visible as `[rbp+X]` offsets) is built in the **Avatar constructor**, two copies of it: `0x508a1f0` and `0x508b3f0` (two ctor variants, differing in the base-ctor call 0x3e82e40 vs 0x3e83030 and an `edx` flag). Same table in both (verified identical strings/addresses). Map is destroyed with the node dtor 0x50913f0 via `0x70d90a0` (array dtor).
The key strings themselves are in `.rdata` **0x89104c0..0x8910850**, contiguous, 41 entries, NUL separated, in the *initializer order* (which is NOT index order). [V]

### 2.2 Why the earlier `measure_map_extract.py` printout is unreliable
The script assigns the first following `mov dword ptr [rbp+X],imm` to a key; the first block (Total Height .. CB Neck to Waist) uses negative `[rbp-0x58]` offsets and `r14d` (=0) for index 0, which the regex skips, so those pairs are shifted by one. The table in 2.3 was built by reading the listing by hand for that first block (0x508a800..0x508aab0) and by the script for the rest (already cross-checked by hand for ~15 entries). The ordering in the file is: string constructed, then `mov dword [..],idx` (the int is the second member of the node).

### 2.3 Measurement table (key literal -> feature index -> units)  [V unless marked]

Index = position in the float[67] stored by CLO (and in the 57/67-entry `listFeatureValues` block of .avt/.avs, see 3.2 caveat). Units in the CSV: whatever line 2 says; internal unit cm. "Kind" is the `Type` column of the key (it tells you what kind of dimension it is; in CLO terms Height = vertical distance from floor, Circumference = **full** loop length, Length = along-surface distance).

| idx | CSV `Name` | CSV `Type` | .rdata key (RVA) | notes |
|---:|---|---|---|---|
| 0 | Total Height | Height | 0x89104c0 | **required** (mode 3); findings/10 observed 187.96 in the male template |
| 1 | (no CSV key) | | | template value 70.0 in the default male; **not importable via CSV**. [I] it is the weight-like/proportion slot (the repo sheet calls it Weight, unverified) |
| 2 | Bust | Circumference | 0x89105a0 | **required for male** (mode 1 driver) |
| 3 | (no CSV key) | | | |
| 4 | Neck Base | Circumference | 0x89104d8 | |
| 5 | Under Bust | Circumference | 0x89105b8 | **required for female** (mode 1 driver) |
| 6 | Waist | Circumference | 0x8910608 | |
| 7 | High Hip | Circumference | 0x8910668 | |
| 8 | Low Hip | Circumference | 0x8910690 | |
| 9 | Thigh | Circumference | 0x89106c8 | |
| 10 | Mid Thigh | Circumference | 0x89106f0 | |
| 11 | Knee | Circumference | 0x8910720 | |
| 12 | Calf | Circumference | 0x8910748 | |
| 13 | Ankle | Circumference | 0x8910770 | |
| 14 | (no CSV key) | | | probably Mid Neck / unused [I] |
| 15 | Bicep | Circumference | 0x8910798 | |
| 16 | Elbow | Circumference | 0x89107b0 | |
| 17 | Wrist | Circumference | 0x89107c8 | |
| 18 | HPS | Height | 0x89104f0 | |
| 19 | (no CSV key) | | | |
| 20 | Shoulder Drop | Length | 0x8910528 | |
| 21, 22 | (no CSV key) | | | |
| 23 | Waist | Height | 0x8910620 | height of waist above floor |
| 24 | High Hip | Height | 0x8910680 | |
| 25 | Low Hip | Height | 0x89106a8 | |
| 26 | Inseam | Height | 0x89106b8 | (findings/10: 86.36 in male template) |
| 27 | Thigh | Height | 0x89106e0 | |
| 28 | Mid Thigh | Height | 0x8910708 | |
| 29 | Knee | Height | 0x8910738 | |
| 30 | Calf | Height | 0x8910760 | |
| 31-33 | (no CSV key) | | | |
| 34 | Across Front | Length | 0x8910540 | |
| 35 | Across Back | Length | 0x8910570 | |
| 36 | Across Shoulder (Curvilinear) | Length | 0x8910500 | (findings/10: 44.13 in male template) |
| 37-39 | (no CSV key) | | | |
| 40 | CF Neck to Waist | Length | 0x8910558 | |
| 41 | CB Neck to Waist | Length | 0x8910588 | |
| 42 | Waist to High Hip | Length | 0x8910630 | |
| 43 | Waist to Low Hip | Length | 0x8910650 | |
| 44 | Apex to Apex | Length | 0x89105d8 | |
| 45 | HPS to Apex | Length | 0x89105f0 | |
| 46 | (no CSV key) | | | |
| 47 | Arm | Length | 0x8910788 | |
| 48 | (no CSV key) | | | |
| 49 | Total Rise | Length | 0x89107f0 | |
| 50 | Front Rise | Length | 0x8910808 | |
| 51 | Back Rise | Length | 0x8910820 | |
| 52-56 | (no CSV key) | | | |
| 57 | Vertical Trunk | Length | 0x8910838 | |
| 58 | Hand | Length | 0x89107e0 | mode special-cased (`i==58`) |
| 59 | Head | Circumference | 0x8910850 | mode special-cased (`i==59`) |
| 60-66 | (no CSV key) | | | |

Tested cross-checks against findings/10: idx 0 Total Height, 2 Chest (=Bust), 6 Waist, 8 Low Hip, 26 Inseam, 36 Across Shoulder (Curvilinear) all agree with the independently-derived `.avt` indexes. [V]
Full string of each key = `Name` + `_` + `Type` exactly as in the third column of the RVA list (e.g. `Across Shoulder (Curvilinear)_Length`).
Also in .rdata, a *different* display-name table lives at 0x833d4a8..0x833d6c8 (`Mid Neck`, `Neck Base`, `HPS`, `Across Shoulder (Curvilinear)`, `Across Shoulder (CB Neck)`, `Shoulder Drop`, `Shoulder`, `CF Neck to Across Front`, ..., `Bust`, `Under Bust`, `Apex to Apex`, `HPS to Apex`, `Halter`, `Waist`, ..., `Vertical Trunk`, `Front Vertical Trunk`, `Back Vertical Trunk`), which is the GUI/body-measure label list (xrefs at 0x2a550a4, 0x36eca6c, 0x2ed9e18 ...). It contains names that the CSV key table does **not** accept (Mid Neck, Across Shoulder (CB Neck), Shoulder, Halter, Front/Back Vertical Trunk). It was not decoded; do not use those names in the CSV. [V that they are not in the key table]

Not importable by CSV although present in the 57-float template: idx 1, 3, 14, 19, 21-22, 31-33, 37-39, 46, 48, 52-56, 60-66 (no key). In practice these are the derived values the two-stage solve computes. [I]

### 2.4 Cross-check with the 57-float order
- The code indexes up to **66** (0x43 slots) and names indexes up to **59**. findings/10 saw only 57 floats (`listFeatureValues`) in the template files, i.e. the stored block ends at index 56; keys 57 (Vertical Trunk), 58 (Hand) and 59 (Head) cannot live in a 57-float block. Either the on-disk list in 2026.1.336 files is longer than in the 2026.1.224-era `base-1.avt`/`CLO_Male_Default.avs` templates the repo has, or those indexes are in-memory only. Not resolved (needs a 336-written .avt/.avs). [unknown]
- findings/10 states "idx 0 = Total Height"; all six indices it names match the table. The other 51 indices of that block cannot be named from this code except those listed above.

---

## 3. Feature value setter `SizeManager::0x512d3a0(this, idx, value)` and the SizeManager data  [V]

```
type = this->0x50d8a30(idx)       // [this + [this+0x18]*0x8F20 + idx*0x210 + 0x599B8]
if (type == 8) { lo = 0.0;  hi = 100.0 }       // 0x8270478 = 100.0   (type 8 is probably a percentage/ratio feature [I])
else           { lo = 0.1;  hi = 300.0 }       // 0x82703d8 = 0.1, 0x846c880 = 300.0  (cm)
v = min(hi, max(lo, value))                    // maxss then minss
v = this->0x516bcf0(v, desc.[+0x278])          // per-feature adjustment (desc +0x278 int; not decoded)
this->[0x86860 + idx*4] = v                    // float array of 67 entries
```
- **Clamping:** every non-ratio feature is clamped to **0.1 .. 300.0 cm** before the transform. So `-5`, `0` (never reaches here), `1000` (meters mis-parse of 10 m) are clamped silently; there is no error. [V]
- The size manager has a profile index `[this+0x18]` (stride 0x8F20 per profile) and 0x210-byte descriptors per feature (type at +0x599B8, something at +0x278). The profile is presumably the avatar family/gender [I]. `0x50e26f0(mgr)` returns `mgr + profile*0x8F20 + 0x597D8` (current profile block).

---

## 4. Avatar resize apply `Avatar::0x50a0f70(this, bool useOtherPath)` (called with dl = 0)  [V call chain / I semantic]

```
if (!this->isCloAvatar()) return;              // 0x50f2010 [this+0x990]
mgr = SizeManager::Instance(); mgr->[+0x10] = this     // bind avatar to the manager
if (useOtherPath /*dl*/) {                     // NOT used by the importer
    0x5140500(this); 0x5193490(this); 0x512f7b0(this, 1);
} else {
    if (this->0x50f1ba0())      // name contains "_NewManne..." (rdata 0x890ffc8 `_NewManne`, i.e. the mannequin avatar variants) [V string, I meaning]
         data = mgr->0x50e26f0();  copy shared_ptr [this+0x8A0/0x8A8] ... 0x513c3d0(this+0xB88, data, ...)   // store size data on avatar
    else if (this+0xB88 initialised) 0x5140250(this+0xB88, mgr->0x50e26f0())
    else mgr->0x50e26f0()
    0x513f190(this, sizeData)    // main deformation worker (414 instr; calls 0x50a0510, 0x517c330, 0x623eb80 x3, 0x62486f0 x3, 0x624a170, 0x623cbb0, 0x623e220 ...)  **not read**
    0x51945e0(this)              // post-process (241 instr; calls 0x5138920, 0x510aec0, 0x510b2e0, 0x5147440 ...) **not read**
    0x5146a40(this, 1)           // 642 instr, touches AvatarManager, map<K,T> access, strings 0x89135d0..dc **not read**
    scene = 0x1bf5e20(); 0x5cfe9f0(scene,...) ; ... 0x57d29d0(...)   // update selection/scene graph (conditional)
}
0x5ccd3a0(Singleton 0x1be1040)                  // same "post refresh/finalize" as at the end of Simulate()   [V]
```
- Whether it deforms the mesh: the path `0x513f190` receives the size data derived from the feature floats and references mesh/skeleton related helpers, and GUI "Size" panel edits go through the same SetFeatureValue + apply sequence, and findings/10 section 6 shows the avs route changes the exported mesh while the `avt_patch` route (floats only) does not. => the ImportMeasurement route is **expected** to re-deform the mesh. [I; not proven by reading the kernels]
- Preset/size dependence: the avatar must be a "CLO avatar" ([+0x990]); the template name (avatar+0x530) selects a gender class and a SizeManager profile (`[mgr+0x18]`). The only gender-specific *validation* is the Bust-vs-Under-Bust requirement (1.3). A name that matches none of "FemaleTemplate", "New_001", "New_003", "FemaleVariant" (rdata 0x8270a60, 0x890fa10, 0x890fa18, 0x890ea08, compared by 0x6666660 case-insensitively [I: flag r8b=1]) returns the other class (male) [I; the `mov eax,1` path is at 0x450d37af]. The exact int return values of 0x50d3680 other than "1 = female" were not decoded.
- Avatar scale/size preset (the `.avs`-style presets): not referenced in the importer; the importer drives the same manager that `.avs` loading drives [I].

---

## 5. Glue `AvatarManager::0x50e41a0(wavt, wcsv, ImportParams&)`  (called by ImportAvatarMeasurement)  [V]

```
copy strings (0x508c5f0 builds a temp std::string pair; 0x6664e10 copies the csv path into [this+0x30], 0x1ba82a0 copies)
ok = 0x50e3fc0(avtPath, ImportParams)        // import the avatar (see 6)
if (!ok) goto fail
ok = 0x50e4d80(csvPath)                      // apply measurements (section 1) to the avatar that is now current
destroy temporaries (0x1baa170 x2, 0x6665040)
return ok
```
So `ImportAvatarMeasurement` = `ImportAvatar` + `ImportMeasurement` with **no headless requirement** (the `IsHeadless()` gate exists only in the one-argument `ImportMeasurement` wrapper). This matters for the plugin: `ImportAvatarMeasurement(csv, avt, opt)` works in a normal GUI session, whereas `ImportMeasurement(csv)` returns false unless CLO is started with `headless`. [V by comparing the wrappers in findings/11]. The measurement step uses "the first/current avatar" (0x50d1640), i.e. the one just imported if the scene already held others? **unknown** (0x50d1640 selection rule not decoded; findings/10 notes N copies of geometry when N avatars are loaded).

---

## 6. Avatar import worker `AvatarManager::0x50e3fc0(wpath, ImportParams&)` and 0x50e4d80/0x50e41a0 pairing

Only the entry and callees were scanned (not required by the goals): it is the single path that creates the Avatar object (constructors 0x508a1f0 / 0x508b3f0 above), reads the .avt container and registers the avatar in the manager list. Not further decoded here. [unknown]

---

## 7. ExportAVT worker `ExportAPI::0x60a42f0(this, &out, wpath)`  (RVA 0x60a42f0..0x60a44e3)  [V]

```
p = normalise(wpath)                          // 0x625cc40 (builds a std::string from the Qt path; has strings 0x8268aec / 0x827dd34 for fallback)
p = 0x40eafc0(p, "avt")                       // force/replace extension "avt" (rdata 0x82607b0)
if (p is empty-string-literal 0x82603ee)  goto done        // 0x6665330 == compare with ""  -> return "" (no path)    [V call, I that 0x82603ee is ""]
list = AvatarManager::GetAvatarList() (0x50db800)           // vector<shared_ptr<Avatar>>
if (list empty) goto done                                   // returns ""
avatar = AvatarManager::0x50d1640()                         // "current" avatar
if (!avatar)                       -> "No AVT data available." (rdata 0x8975760), return ""
if (avatar->[+0x618])              -> same message           // 0x50ef2f0  (flag A)
if (avatar->[+0x6A0] && avatar->[+0x6A8]) -> same message    // 0x50f0900 (flag B) && 0x50f1b70 (flag C)
ok = AvatarManager::0x511f4f0(p, avatar_shared_ptr, &extra)  // serializer: 0x39f6b20 (stream ctor) ; 0x3a03bf0 (write) ; 0x39f7c50 (dtor)
out = p                                                      // ExportAVT returns the written path, "" on any failure
```
- **Which avatar is exported:** the manager's "current" avatar (0x50d1640), not an index. `ExportAVT` has no avatar parameter. [V]
- The three flags make the export refuse (message only, no exception, empty string returned): [+0x618] set, or both [+0x6A0] and [+0x6A8] set. Their meaning is not decoded [unknown] (candidates: "avatar is a converting/skeleton preset", "avatar is a mannequin", "avatar derived from a measurement-less format").
- The header/ZIP fields of findings/10 section 2 (magic ` AVT        CLO `, version, PNG thumbnail, ZIP offset/len, ms timestamps, product string `CLO Standalone OnlineAuth`, template name, `.dan` + textures + `clofiles.json`) are produced inside `0x3a03bf0`/`0x511f4f0` and below. **Not decoded.** The writer is shared with project save (the ZPRJ ZIP embeds a complete `.avt` member, findings/10 2.2), so it probably is the generic "container header + zip members" writer; `AVT` vs `ZPRJ` is the 4-char magic chosen by the caller [I].
- Failure is silent: no message box (unlike `DisplayMessageBox`), and the only text is "No AVT data available." from the log-style stream (0x1d68810 style output, not shown to the user). The plugin must treat `""` as failure. [V for the return value, I for no GUI side effect]

---

## 8. Practical implications for the Mirra pipeline

1. A CSV that CLO's `ImportAvatarMeasurement` will accept (inference, matching the parser exactly):
   `line1 = anything`; `line2 = Unit(cm)` (unit exactly `m|feet|inch|cm|mm`, lowercase, no spaces); then `Total Height,Height,<v>`, `Bust,Circumference,<v>` (male) or `Under Bust,Circumference,<v>` (female) plus any of the 41 `Name,Type` pairs in section 2.3. Values are full circumferences as the key says; no halving. No trailing blank line.
2. Use `ImportAvatarMeasurement(csv, avt, opt)` (works without `--headless`); `ImportMeasurement(csv)` is a no-op in GUI mode. After either, CLO recomputes derived features (two-stage solve), so read back with `ExportAVT`/`.zprj` if you need the final 57/67 floats.
3. Values are clamped to 0.1..300 cm per feature; a wrong unit string silently becomes meters.
4. The importer cannot set idx 1, 3, 14, 19, ... (no key); those come out of the solve.
5. Gender is taken from the avatar template name; passing a male template with only `Under Bust` (or female with only `Bust`) fails with the logged message and returns false.

## 9. Unknown / not done

- Exact on-disk first two lines of a CLO-written measurement CSV (no sample, no writer found); the `Unit(cm)` layout on line 2 is derived from the parser only.
- Deformation kernels 0x513f190, 0x51945e0, 0x5146a40, 0x5148d70, 0x51449e0, the transform 0x516bcf0; so "mesh re-deformed" is inferred, and the dependence on avatar size preset beyond the profile index `[mgr+0x18]` is unknown.
- Integer return map of 0x50d3680 (gender) and what exactly selects the SizeManager profile.
- `0x50e3fc0` (avatar import) internals; 0x50d1640 selection rule when several avatars are present.
- AVT serializer 0x511f4f0 -> 0x3a03bf0: how the header fields (offsets 0x14, 0x30, 0x3C, the size table, 0x101) are produced; meaning of avatar flags at +0x618/+0x6A0/+0x6A8.
- Whether the on-disk `listFeatureValues` in 336-written files has 57 or 67 floats.
- Hash function used by the key map (0x1d00bb0) — irrelevant for behaviour, only case-sensitive exact match matters.
