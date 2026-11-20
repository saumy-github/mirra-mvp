# 41 - Per-panel texture/colour: API-level options (lane AQ)

*Status: static analysis only (CLO 2026.1.336 exe, base 0x140000000, all addresses RVAs; CLO not run). Tags: [V] = read from disassembly / headers / existing data, [I] = inference.*
*Date: 2026-10-29. Code: `scripts/disasm_fn18.py` (copy of disasm_fn15, cache `raw/disasm18/`), dumps `raw/aq_0x*.txt`. Slot model: `scripts/slots_lookup.py`. Thunk check: `raw/verify_thunks.json`.*

## 0. Result in one paragraph

The shared-fabric clobbering (findings/23 section 6) is real and has an API-level fix: **give every panel its own fabric** (candidate A). The SDK has no "duplicate fabric" call, but `ExportFabric`/`ExportZFab` + `AddFabric` (or `CreateZfabFromTextures` + `AddFabric`) creates N independent fabrics, `SetPatternPieceFabricIndex`/`AssignFabricToPattern` binds each panel to its own, and the **already-existing plugin commands `set-fabric-color` / `set-fabric-texture` already resolve the fabric through `GetFabricIndexForPattern(pattern)`** (RestPlugin_windows.cpp l.2060-2100), so once the panels point to different fabrics, per-panel colour/texture works with no change to those two commands. What is missing in the plugin: wrappers for `AddFabric`, `ExportFabric` (or `CreateZfabFromTextures`), `GetFabricCount`, `GetPatternPieceFabricIndex`/`AssignFabricToPattern`. GLB export already produces one mesh per pattern (meshes "1","2","3","7", one primitive each) and one material per CLO material, so 4 fabrics should give 4 glTF materials [V for meshes, I for 4 materials]. Colorways (B) are unsuitable; graphic decals (C) are a second-best complement for logos only.

## 1. What every candidate needs to know (verified facts)

All candidate functions are **implemented** (not thunks): `raw/verify_thunks.json` lists thunks only for Utility slots 388-400, Pattern 196-220 and Rest 4-10; Fabric has none. All slots used here are below those ranges. [V]

| API | class slot | exe RVA | sig |
|---|---|---|---|
| AddFabric(path) | Fabric 15 | 0x5f8f580 | `unsigned int` |
| ReplaceFabric(idx, path) | Fabric 16 | 0x6038110 | bool (header default returns "") |
| ExportFabric(path, idx) / (path, colorway, idx) / (path) | Fabric 10/11/12 | 0x5fb6b40 (slot 10) | string = path, "" on error |
| CreateZfabFromTextures(zfab, base, normal, disp, opacity, rough, metal) | Fabric 121 | 0x5fabc50 | bool |
| GetFabricCount(bool cur) / (int colorway) | Fabric 1/2 | 0x5fe3c40 / 0x5fe3f90 | uint |
| SetPatternPieceFabricIndex(pat, fab) | Pattern 62 | 0x6064db0 | void |
| GetPatternPieceFabricIndex(pat) | Pattern 61 | 0x6009310 | int |
| AssignFabricToPattern(fab, pat, option) / (colorway, fab, pat, option) | Fabric 27 / 26 | 0x5f9bd50 / 0x5f9bf90 | bool |
| GetFabricIndexForPattern(pat) / (pat, colorway) | Fabric 51 / 50 | 0x5fe4a50 / 0x5fe4d90 | int (see findings/21 sec 4) |
| AddTextureToPatterns | Fabric 284 | 0x5f96610 | JSON string |
| TransformAOPOnFabric | Fabric 283 | 0x607fdd0 | JSON string |
| AddGraphicStyleFromImageFile(path, idx) | Utility 208 | 0x5f8faa0 | bool |
| AddGraphicStyleToPattern (9-arg) / V2 | Utility 305 / 386 | 0x5f90470 / 0x5f90ba0 | bool / JSON-ish string |
| AddGraphicStyleToPattern (vector form) | Pattern 182 | 0x5f8fd00 | bool |
| GetPatternUVSpace / MovePatternToUVSpace / MovePatternsToUVSpace | Pattern 189/190/191 | 0x600ba60 / 0x60323b0 / 0x60324f0 | JSON string |

Index bases: **all 0-based**: fabric index = position in the document fabric list; pattern index = position in the pattern list (0 front, 1 back, 2 sleeve_left, 3 sleeve_right as in the run report). [V from findings/12, 23]

## 2. Candidate D first: what SetPatternPieceFabricIndex really does [V]

`0x6064db0` (slot 62): logs, then `0x60b1f10(this,&patSp,pat)` -> pattern shared_ptr; **null pattern -> silent return** (test `0x1d68bd0` at 0x146064F66/F72). Otherwise it calls `0x57d32b0(editor,&patSp,fabricIdx)`, an undoable "set fabric index" command builder, whose real worker is **`0x43bc050(pattern, fabricIdx)`**:

```
0x43bc050: n = (fabricList.end - fabricList.begin) >> 4      # fabric list = 0x1c22c90 (document-wide, 16-byte shared_ptr entries)
           if (n <= (unsigned)(int64)fabricIdx) return;     # jbe at 0x1443BC077  -> SILENT no-op
           fab = fabricList[fabricIdx]
           pattern->vfn[0x888/8](fab, true)                 # call [rsi] at 0x1443BC0D9: assign fabric to the pattern
```

- **Index == GetFabricCount is a silent no-op** (unsigned compare, `jbe`), as is any negative value (movsxd -> huge unsigned). No log, no return value (void), no exception. So the pipeline's current `set-fabric` with `fabric_index=0` works only because index 0 always exists. The undo-command is still built before the worker runs, so a failed set may leave an empty undo step [I].
- The list is the document list (not per colorway); `GetFabricCount(true)` (current colorway) should equal it in a single-colorway scene [I].
- Verification must therefore be by read-back: `GetPatternPieceFabricIndex(pat)` (0x6009310: `60b1f10` -> pattern, then `0x4348d80` reads a field at pattern+0xE20 [V]; null pattern -> 0). Caution: failure also gives 0, so only trust a read-back of a value >= 1, or compare with `GetFabricCount` first.
- Preferred alternative: **`AssignFabricToPattern(fab, pat, option)` slot 27 (0x5f9bd50)**: current colorway `49ffd90`->`49fb510`, `GetFabric(fab)` via `0x60ac160` (null on out-of-range, see findings/21 sec 0), then `0x6090d60(this, fabSp, colorway, pat, option)`; returns the bool from that call [V structure], which also does a UI refresh (`0x5ccd3a0` in its callee list). `_assignOption`: 1 = current colorway only (use this), 2 = all colorways unlinked, 3 = all linked (header). It returns bool, so failure is detectable. Whether it returns false for a bad fabric index is [I] (null sp passed down).

## 3. Candidate A: one fabric per panel (RECOMMENDED)

### 3.1 How to obtain N fabrics

There is **no fabric copy/duplicate API** in the 336 headers (searched Copy/Duplicate/Clone: none). Three ways:

1. **ExportFabric + AddFabric** (needs an existing fabric): `ExportFabric(zfabPath, 0)` writes fabric 0 (.zfab or .jfab chosen by extension per header) and returns the path ("" on error); then `AddFabric(zfabPath)` once per extra panel. [V headers; body of AddFabric below]
2. **CreateZfabFromTextures(out.zfab, baseTex, "", "", "", "", "")** writes a fabric file whose base map is the panel texture (each of the six maps is guarded by a size test; the base path check is `cmp [r14+10h],0 / jbe` at 0x145FABF38, empty strings skip, so unused maps may be ""; [V for the base guard, I for the other five]). Then `AddFabric(out.zfab)`. This embeds the texture in the file, so no `SetBaseTexture...` call is needed afterwards (but colour/physical props come from the template CLO uses internally [I]).
3. A prepared .zfab/.jfab on disk (CLO ships none we can rely on; the repo has no such file).

**AddFabric body (0x5f8f580) [V]**: logs; builds a path object (`0x666b740`, `0x66668a0`, `0x625cc40`, `0x40ef3a0`, `0x666c7f0`) from the string; calls `0x5cdcca0(fabricList = 0x1c22c90(), &pathObj)` -> `0x5cdccf0` -> **`0x5cdc610`** which loops over the fabrics loaded from the file (vector of 16-byte entries), creates each as a document fabric and records undo names **"Add Fabric" / "Copy Fabric"** (strings at 0x8347a78 / 0x8347a50, [V]); finally returns **`fabricList.size() - 1`** (`lea eax,[rbx-1]` at 0x145F8F7D6), computed *after* the add, **with no success check**. Consequences:
- Return value = index of the newly appended fabric **only if** the add succeeded. If the file is missing/unreadable the list is unchanged and the return value is the index of the previous last fabric (or 0xFFFFFFFF if the list was empty). Always verify `GetFabricCount` grew by 1 (+ file exists) instead of trusting the return value. [V code path, I for failure behaviour of the loader]
- No dedupe by path is visible in the loop: adding the same zfab 3 times should give 3 independent fabrics (each constructed from the file) [I; unverified without running CLO]. The "Copy Fabric" label suggests CLO itself treats loading the same fabric again as a copy.
- A multi-fabric zfab would append several fabrics; the return is then the last one.

### 3.2 Required call sequence (also in section 8)

`ExportFabric` -> `AddFabric` xN -> `GetFabricCount` check -> `AssignFabricToPattern`/`SetPatternPieceFabricIndex` per panel -> read-back -> per-fabric `SetFabricPBRMaterialBaseColor` and `SetBaseTextureMapImageGivenFilePath`.

Per-fabric calls (from findings/21): `SetBaseTextureMapImageGivenFilePath(path, fabricIdx)` slot 213, face fixed Front, **an out-of-range fabric index silently textures the currently selected fabric** (so range-check first; since fabrics 1..3 are new, call `SetCurrentFabricIndex(i)` slots 119/120 before as belt and braces [I]); `SetFabricPBRMaterialBaseColor(fabric, face, r,g,b,a)` slot 116 returns bool (false on bad fabric).

### 3.3 Why the plugin already half-supports this [V]

`set-fabric-color` and `set-fabric-texture` (RestPlugin_windows.cpp ~l.2060-2100) do `fabric_idx = GetFabricIndexForPattern(cmd.param3)` and then dispatch to that fabric (colour: fabric, colorway 0 via slot 115 `(fabric, 0u, r,g,b,a)`; texture: slot 213). The success message contains the resolved fabric number ("Color ... dispatched to fabric N", "Texture dispatched to fabric N: path"). Therefore once panel i maps to fabric i, calling the existing commands with the panel's pattern index sets the panel's own fabric, and **the message text is itself a read-back of the pattern-to-fabric mapping** (no new endpoint needed for verification, although it is a string match).
Caveat: `GetFabricIndexForPattern(1-arg)` returns 0 on failure (findings/21 sec 4), identical to "fabric 0", so a failed assign shows up as all four messages saying fabric 0.
Caveat 2: `set-fabric-color` hands `0u` as colorway to the 4-arg overload per the dispatcher (l.299); correct for the single "Default Colorway".

### 3.4 Texture-size caveat (independent of A)

A base texture is a repeating swatch whose physical size is `v2Size`/`v2PhysicalSize` (findings/23 sec 6: 153.8 x 111.5, `bTileTexture` False). It is not UV-fitted to the panel. Two API-level ways to size it to the panel once the panel owns its fabric: `TransformAOPOnFabric(aopMode=1 BaseColorMap, colorway, fabric, styleChip=-1, TransformOptions{widthMm,heightMm,...}, side)` (slot 283, 0x607fdd0; JSON result with "status"; errors: invalid colorway, fabric not found, aopMode not 0/1) or the Utility material-transform API (`SetMaterialTextureTransformations`, Utility header l.3137). Neither was decoded further here; [I] that BaseColorMap mode with widthMm/heightMm = panel bbox mm (front 580.2 x 718.6, sleeves 490.3 x 245.1, findings/23 sec 5) maps the cutout 1:1. Because the panel is its own fabric, such a transform affects only that panel, which is impossible today.

### 3.5 Does it survive ExportGLB? [V/I]

Existing garment GLB (`clo_vto/output/u_015/c_004/s_001/001/simulation.glb`, probed with `scripts/glb_probe.py`'s loader): **13 meshes; garment meshes "1","2","3","7" = one primitive each, all with material 0 (`FABRIC 1_2411138`)**; avatar meshes use one material per primitive (body: 4 primitives / 4 materials). So the exporter already splits geometry per pattern and materials per CLO material (name `<fabric name>_<uid>`). With 4 fabrics, each pattern references its own material [I, standard behaviour of the exporter, not seen in a multi-fabric file]. Textures are exported from each material's own map (image count 27 for the shared-fabric file). Name fabrics distinctly (`SetFabricName(idx, "front_panel")`, Fabric slots 79-81) so the GLB materials are identifiable in the viewer [I].
Unknown: whether `GetObjectBrowser`-based "unused fabric" pruning drops fabrics not assigned to a pattern: irrelevant here since all four are used. The leftover original fabric index 0 stays used by panel 0.

## 4. Candidate B: colorways (reject)

`GetColorwayCount` (Utility 15 0x5fdffc0; Export header l.602) and per-colorway getters exist, but **no AddColorway API exists in the three headers** (grep for AddColorway returns nothing; only Get/Set/Export by colorway index). A colorway swaps the materials of *all* patterns at once (findings/23: `mapColorWay/listColorway[c]` with one material per fabric per colorway); a single colorway cannot give different panels different looks unless they use different fabrics, which is candidate A again. GLB export with `bSaveColorWays` makes KHR_materials_variants (CloApiData.h l.179/195), a whole-garment switch. Verdict: unsuitable. [V headers, I rest]

## 5. Candidate C: graphics / prints on selected patterns

C1 **Graphic style decal on one pattern** (genuinely per-pattern, UV-following):
1. `AddGraphicStyleFromImageFile(path, index)` (Utility 208, 0x5f8faa0; header: index must be 0..count; "added or replaced"; returns bool). Calls `1c22e10` (graphic list, separate from the fabric list, findings/21 sec 3) and `5cdd0e0`/`4bcb940`. 
2. `AddGraphicStyleToPatternV2(pat, gsIdx, x, y, w, h, face, zOffset, angle)` (Utility 386, 0x5f90ba0, forwards to `0x608d450`), x/y are mm from the pattern's top-left, the graphic is centred on (x,y), face 0 front / 1 back / 2 both; returns a status string ("success"/"failure" + message). V1 (slot 305, 0x5f90470) returns bool and is large (466 instrs, resolves pattern bbox itself). Pattern API has a bbox-relative variant (slot 182).
- Pro: no new fabrics, decal sized/positioned in mm in pattern space, Front/Back selectable; hits exactly the patterns you name. Con: it is a *decal on top of the fabric*, so the panel body colour still needs the shared-fabric colour (cannot differ per panel); a full-panel texture would be a w x h = panel bbox decal. **Whether the GLB exporter bakes decals into the base colour texture is unknown** ([I] it does so only for the unified/baked UV path; findings/39 line 20 notes graphics only appear via the graphicList selection or whole-scene selection, so they may appear as separate meshes). Needs a test export before relying on it.
- The plugin's current `set-fabric-graphic` is *not* this: it calls `SetBaseTextureMapImageGivenFilePath` (same as texture), RestPlugin_windows.cpp l.2106-2124, which is the clobbering path.

C2 **AddTextureToPatterns** (Fabric 284, 0x5f96610, 2119 instrs, JSON result `{"status":"done"|"error","description":...}`): despite the name it takes **no pattern indices**: `(path, colorway, fabricIndex, styleChipIndex, aopMode, materialSide)`; it applies an all-over-print to a *fabric* (aopMode 0 Print creates a "print fabric" style chip, 1 BaseColorMap loads it as base colour). Error strings [V]: "Invalid style chip index", "Fabric not found for colorway N and fabric index M", "Invalid material side value. Use Front, Back, or Side", "Failed to load texture as base color for colorway", "Failed to create print fabric", "ColorwayIndex is -1 but 'Show all Colorways' is OFF". Useful only on top of candidate A (aopMode=1 is equivalent to SetBaseTexture but returns an error string, so it is a better-checked replacement for slot 213). On the shared fabric it clobbers like the old path.

C3 **UV-space moves** (`GetPatternUVSpace`, `MovePatternToUVSpace`, `MovePatternsToUVSpace`, Pattern 189-191): operate on the 3D-garment UV layout (tiles), return JSON per pattern, 0-based tile indices. They would let one UV atlas texture serve all four panels (move each pattern to its own region/tile of the unified UV, then apply a single atlas texture to the one shared fabric). That would match the repo's existing "atlas" idea, but needs the exporter's unified UV (`bUnifiedUVCoordinates`, findings/39 line 44) and an atlas laid out to CLO's packing; heavier than A. Not decoded further; ranked third.

## 6. Ranking

| Rank | Candidate | Effort | Risk | Notes |
|---|---|---|---|---|
| 1 | A: per-panel fabrics (ExportFabric or CreateZfabFromTextures, AddFabric x3, Assign/SetPatternPieceFabricIndex) | 3-4 new plugin endpoints (+existing color/texture reused) | Medium: AddFabric success unverifiable except by count; same-file-3x behaviour [I]; plugin rebuild + SDK match (memory: CLO app/SDK version must match) | Fixes colour and texture per panel, GLB gets distinct materials, no UI reliance |
| 2 | C1: graphic decal per pattern | 2 new endpoints | Medium-high: GLB baking unknown; body colour still shared | Good for logos on one panel (replaces broken set-fabric-graphic) |
| 3 | C3: UV atlas via MovePatternsToUVSpace | high | High (CLO packing, unified UV) | Only if one-fabric/one-atlas is wanted |
| 4 | B: colorways | - | - | No AddColorway; whole-scene switch |
| - | C2 alone (AddTextureToPatterns) | - | - | No pattern selector; helper inside A only |

## 7. Notes and risks

- Memory/consistency: the saved `.zprj` stores `listFabric` as the document list and `mapFabricShape2D/iFabricIndex` per pattern (findings/23); after A you should see `listFabric` length 4 and `iFabricIndex` 0..3 there, which is a second, offline verification (`scripts/zprj_probe.py`).
- Order matters: apply per-panel fabric assignment **before** simulation if physical properties should be identical (they will, copies of fabric 0); changing fabric after draping triggers re-simulation need [I]. With ExportFabric of fabric 0 the copies inherit its drape properties. With `CreateZfabFromTextures` they inherit whatever default template CLO uses [I], which may differ from fabric 0: if drape must stay identical, prefer method 1.
- All fabric setters call UI refresh directly (findings/21 sec 5): keep them on the GUI thread (PostMessage). `AddFabric`/`ExportFabric`/`AssignFabricToPattern` also log and call UI/undo code (callee `0x5ccd3a0` in 0x6090d60, undo naming in 0x5cdc610): GUI thread only [I]. A file-open dialog is not involved (file path API), but a missing/invalid zfab might raise a message box [I, not evidenced].
- `SetFabricPBRMaterialBaseColor` face 0 only is set by the plugin; Back falls back to Front if no own material (findings/21 sec 1).

## 8. Recommended Step 8 call sequence (4 panels)

Plugin additions required (new REST commands, GUI-thread dispatch like set-fabric-*): `fabric-count` (GetFabricCount(true)), `fabric-export` (ExportFabric(path, idx)), `fabric-add` (AddFabric(path); also reports the count before/after), `pattern-fabric` (GetPatternPieceFabricIndex(pat)), `assign-fabric` (AssignFabricToPattern(fab, pat, 1)); `set-fabric` (SetPatternPieceFabricIndex) already exists.

```
0.  n0 = fabric_count()                                          # GetFabricCount(true); expect 1 on a fresh project            [V API]
1.  p  = fabric_export(<tmp>/panel_base.zfab, 0)                 # ExportFabric(path, 0); non-empty path and file exists          [V header]
2.  for k in 1..3:                                               # panels 1,2,3 get new fabrics; panel 0 keeps fabric 0
        r = fabric_add(p)                                        # AddFabric(p); r is size-1 only if the add worked               [V 0x5f8f580]
        assert fabric_count() == n0 + k, else abort (do not trust r)
3.  for i, panel in enumerate([front, back, sleeve_left, sleeve_right]):   # pattern idx = ctx.piece_to_index[panel]
        assign_fabric(fabric=i, pattern=idx[panel], option=1)    # AssignFabricToPattern(i, pat, 1) -> bool                       [V 0x5f9bd50]
        # fallback if that returns false: set_fabric(idx[panel], fabric_index=i)  (void, silent if i >= count)                    [V 0x43bc050]
4.  read-back: pattern_fabric(idx[panel]) == i for i >= 1 (0 is ambiguous: also means failure)                                       [V 0x6009310]
        or parse the "dispatched to fabric N" message of step 5/6; N must equal i.
5.  for each panel: set_fabric_color(idx[panel], r, g, b)        # existing: GetFabricIndexForPattern -> SetFabricPBRMaterialBaseColor(fabric, 0, r,g,b,1)
6.  for each panel with a texture: set_fabric_texture(idx[panel], tex_png)   # existing: SetBaseTextureMapImageGivenFilePath(path, fabric) (slot 213, Front)
    (optionally: set colour to white first, findings/21 sec 6; and size the swatch to the panel via TransformAOPOnFabric aopMode=1)
7.  wait_for_fabric(); optionally fabric_name(i, "<panel>") for GLB material names; then simulate/export as today.
8.  Offline check after ExportZPrj: listFabric has 4 entries and each pattern's mapFabricShape2D/iFabricIndex = 0,1,2,3 (zprj_probe.py); in simulation.glb the 4 meshes "1","2","3","7" reference 4 distinct materials (glb_probe).
```

Alternative for step 1-2 (no existing fabric dependence): `create_zfab(<tmp>/<panel>.zfab, base=<panel_texture.png>)` then `fabric_add(...)` per panel; skips step 6 for that panel but loses fabric-0 drape properties (see section 7).

## 9. Unverified / needs a live test (when CLO may be run)

1. Whether AddFabric of the same .zfab three times yields three independent fabrics, and their names (`FABRIC 1`, `FABRIC 1(2)`?).
2. Whether `ExportFabric(path, 0)` of the default fabric (no texture) writes a valid zfab and whether `AddFabric` of it leaves the new fabric's "Default" physical props intact.
3. Whether AssignFabricToPattern(option=1) returns false for an out-of-range fabric.
4. Decal baking into GLB (candidate C1) and 4-material GLB output (A).
