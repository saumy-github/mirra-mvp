# 21 - Fabric appearance internals (lane N)

*Status: static analysis only, CLO 2026.1.336 exe, base 0x140000000, all addresses are RVAs. Tags: [V] = read directly from disassembly, [I] = inference. Raw dumps: `raw/n_*.txt`; helper `scripts/disasm_fn4.py` (cache `raw/disasm4/`). Names of unexported helpers are mine.*

## 0. Common helpers (all [V] unless noted)

| RVA | Role |
|---|---|
| 0x49ffd90 / 0x49fb510 | doc/colorway container getter / "current colorway index" of it. Setters without a colorway arg use the *current* colorway. |
| 0x49faf00 | colorway count |
| 0x60ac160 `GetFabric(this,&sp,fabricIdx)` | document fabric list (0x1c22c90; vector of 16-byte shared_ptr at +0x10..+0x18) -> shared_ptr<Fabric>. **Index >= size -> null sp** (unsigned compare via `ja`). |
| 0x60ae0f0 `GetFabric(this,&sp,colorwayIdx,fabricIdx)` | colorway container (0x49fadc0) -> per-colorway fabric vector (16-byte entries); colorway null or fabric idx >= size -> null. |
| 0x60adc40 / 0x60addd0 `GetMaterial(this,&sp,fabric,colorway,face)` | colorway bounds-checked (`cmp colorway, count; jge`) -> picks fabric-in-colorway -> 0x6104b90. |
| 0x6104b90 `faceEntry(arr,&sp,&face)` | `entry = arr + face*16`; if `entry[+8]` (material shared_ptr) non-null return it, **else fall back to entry 0 (Front)**. No upper bound on face. |
| 0x1be0ec0 | global app singleton (TLS-guarded static). `[+0x30]` = main-window/UI object, `[+0x40]` = UI/colour-library object. |
| 0x49a79e0(fabric) | UI refresh: `app[+0x30]->vfn[0x120](fabric)`; then again with member at fabric+0x910. Direct virtual call, no queueing. |
| 0x5ccd3a0 | UI/3D refresh: objects from 0x61548a0 (`app+0x10`), 0x61548c0, 0x61548b0 (`app+8`): `vfn[0x100]()` and `vfn[0xB8](0)`. Direct virtual calls. |
| 0x4e10dd0 / 0x4e10fb0 | Logger (analytics event, see 17); no side effect on state. |

## 1. SetFabricPBRMaterialBaseColor

Slots: 113 `(colorway, fabric, face, string)` 0x604e000; 114 `(fabric, face, string)` 0x604dcb0; 115 `(colorway, fabric, face, r,g,b,a)` 0x604e350; 116 `(fabric, face, r,g,b,a)` 0x604e5e0. [V] (log FUNCSIG at 0x897ed70 for 116; arg order confirmed by register flow, header order from FabricAPIInterface.h l.933-986).

Common worker: **0x60f9480 `ApplyBaseColor(this, fabricSp, colorway, face, r,g,b,a, std::string* colorName)`** returns bool.

```
bool ApplyBaseColor(fabricSp, colorway, face, r, g, b, a, name):
    if fabricSp is null:                         return false           # 0x60f94bf
    mat = GetMaterial(fabricSp, colorway, face)   # 0x60addd0 -> 0x6104b90 (face falls back to Front if that face has no own material)
    if mat == null:                               return false           # 0x60f94ec
    prop = mat+0x220 .baseColorHolder             # 0x3ad2cc0 (selects one of two shared_ptrs by mode flag 0x3adef90)
    if prop.ptr == null:                          return false           # 0x3ac6ec0 (cmp [rcx],0)
    baseColorProp.set(Color(r, g, b, 1.0f))       # 0x39d1d40 ctor, 0x3a857e0 setter; alpha slot hard-coded 1.0
    baseColorProp.setOpacity(a)                   # 0x3a852e0 -> 0x3ae93c0 (a clamped; 1.0f at .rdata 82703f8 is the bound) [I]
    if name != "": baseColorProp.setName(name)    # 0x3a85b70   (only the string overloads)
    baseColorProp.<flag>(false)                   # 0x3a90900(...,0)
    UI refresh: 0x49a79e0(fabric); 0x5ccd3a0(); app[+0x30]->vfn[0x20]()   # 0x1be0ec0 guards
    return true
```

Findings:

- **Face (arg `materialFace`)**: unsigned used directly as an array index into the fabric's per-face material table, then `0` Front, `1` Back, `2` Side [V for indexing, I for names - matches 211's explicit check `face <= 2` and the header "0: Front, 1: Back, 2: Side"]. There is **no bounds check in this function**; values > 2 index past the table (undefined). If the Back/Side face has no own material (null entry, typically when "Use same colour as front" is active) the call silently **modifies the Front material** and returns true. So setting Back in that state is harmless but redundant; setting Back when it is separate really changes the inside.
- **Value range**: floats go straight into a Color(r,g,b,1.0) with **no scale/clamp in the setter path** [V for 116/115/114/113 and 0x60f9480; I for the deeper 0x3ae9cd0 -> 0x3b089d0 chain, which showed no float constants]. Alpha is applied separately and clamped to <= 1.0 [I]. So 0..1 floats; 0..255 would be stored out of range (not clamped). Plugin's /255 convention is correct. (Lane E's remark about "constant vectors at 0x897e620.." for 116 is not supported by the disassembly: 116 has none.)
- **Colour space**: no `pow`, 2.2, 2.4, 0.04045, 12.92 or 1/2.2 constants in 0x604e5e0, 0x604e350, 0x60f9480, 0x3a857e0, 0x3ae9cd0, 0x39d1d40. **No conversion is done by the API**; value is stored as given. Whether CLO treats the stored value as sRGB (display) or linear is a property of the property object (not decoded; [I] CLO UI colour pickers store display-referred values, so passing sRGB/255 is the expected convention).
- **String overloads (113/114)** do not parse hex: the string is a **colour-library name**: 0x60b1300 calls `app[+0x40]->vfn[0x78](name, &Color)` and the overload returns false (0x604dee3 `jne` -> return false) if the name is unknown. The resulting colour's r,g,b are then passed to 0x60f9480 and the *name* is stored on the property. Before this, `app[+0x40]->vfn[0x48]()` is called (UI object; a headless CLO with `app[+0x30]==0` skips it). [V]. **Do not pass "#RRGGBB"; use the float overloads.**
- **Return values**: false when: fabric index out of range (null sp), colorway out of range (116/114 use the current colorway, so only 113/115), material for that face missing, property holder null, (string overloads) unknown colour name. True otherwise. No exceptions in the happy path. The header's `GetFabricPBRMaterialBaseColor` returns (1,0,0,0) on invalid (lane E), consistent.
- **Colorway index** (113/115): 0-based, `colorway >= count` -> false [V]. Note for 115: colorway is the *first* argument, fabric second (header order; reverse overload order in vtable).
- **Re-render**: data change **plus synchronous UI refresh** in the same call (0x49a79e0, 0x5ccd3a0, app[+0x30] vfn 0x20). It is not a pure data setter. Whether the 3D window repaints immediately or schedules an update is [I] (virtual call +0x100 on window objects is probably `update()`/`repaint()`); no sleep is needed before an export that follows synchronously on the same thread.
- **Threading**: direct virtual calls into UI objects, no `QMetaObject::invokeMethod`, `QThread::currentThread` or marshalling in any of these functions [V - checked bodies listed above]. => treat as **GUI-thread only** [I]. The existing plugin design (PostMessage to the main window then call) is right; calling from the httplib worker thread is unsafe.

## 2. SetBaseTextureMapImageGivenFilePath

Slots (lane E): 211 `(path, colorway, fabric, styleChip, face)` returns std::string, 0x6044000; 212 `(path, colorway, fabric)` 0x60451f0; 213 `(path, fabric)` 0x6044f10; 214 `(path)` 0x6044c80.

```
213 (path, fabricIdx):                                   # 0x6044f10 [V]
    sp = GetFabric(fabricIdx)                            # may be NULL for bad index
    pathObj = wrap(path); colorway = current colorway
    0x60fafe0(this, pathObj, 0, &sp, colorway)           # face hard-coded 0 (Front)
214 (path):  same but sp = null (-> currently selected fabric)
212 (path, colorway, fabric): same with 0x60ae0f0(colorway,fabric)   # face 0
211 (path, colorway, fabric, chip, face): full validated form (below)

0x60fafe0(this, pathObj, flag, fabricSp, colorway):       # [V]
    if pathObj not empty:                                 # 0x6667120 (empty check)
        f = open(path)  (0x6675bd0 builds a file object with strings "file not open"/"empty source path")
        if !f.is_open (0x6676030): return                 # SILENT no-op, no error
    if fabricSp == null: fabricSp = app->selectedFabric   # 0x5cf9e30 (doc+0x40/0x48) -> **fallback to the SELECTED fabric**
    mat = GetMaterial(fabricSp, colorway, face=0)         # 0x60addd0
    if mat: mat+0x220 .baseTexture.set(pathObj, flag)     # 0x3a73910 -> 0x3accd60
            0x5ccd3a0();  app[+0x30]->vfn[0x20]()         # UI refresh
```

- **Which overload sets which face**: 212/213/214 -> **Front only** (face literal 0). Only 211 takes the face (0 Front, 1 Back, 2 Side) [V].
- **Fabric index validity (213)**: an out-of-range fabric index gives a null shared_ptr, and `0x60fafe0` then **falls back to the currently selected fabric** (0x5cf9e30), so a bad index silently textures the *wrong* fabric rather than failing [V code path; I that "selected fabric" is the meaning of doc+0x40]. No message is printed in 212-214. The plugin should range-check the index itself (`GetFabricCount`) and/or select the fabric first. Colorway for 213/214 = current colorway.
- **Sync/async**: file is opened and the texture object is set on the material inside the call (0x3accd60 has a file-open/empty check, a type switch on an enum `cmp ebp,4`, and calls the decode helpers 0x3ae4fd0/0x3aef390) [V for structure]. Everything runs in the caller thread; no queued work seen. Treat as synchronous; whether pixels are decoded then or lazily at first draw is [I - likely decoded/uploaded at set time, as export reads GPU/CPU copies].
- **Extensions**: no extension filter in the API layer (no ".png/.jpg" literals in 6044f10/60fafe0/3a73910). Format support is whatever CLO's image loader (0x3accd60 -> 0x3ae4fd0) accepts; PNG/JPG are safe [I]. Unsupported file -> silent.
- **Return**: 212-214 void. 211 returns a std::string (JSON-ish `{"status":"failed","message":...}` on error, e.g. `cannot apply to Substance material` at 0x8984048; otherwise the string from 0x60ac7a0 listing other colorways that share the fabric) [V strings, I for success payload].
- **'Invalid Inputs. Fabric Index :...' conditions (211 only, 0x6044000 -> msg at 0x8983ed0/0x8984028)**: resolver 0x60ac0d0 turns (colorway, fabric, styleChip) into concrete (colorway,fabric); error if resolved fabric == -1, resolved colorway == -1, or `face > 2` (`cmp r14d,2; ja` at 0x146044231). Message is printed (logged) and the function returns without setting. Empty path -> removes the texture (0x60f1c90). Substance materials are refused.
- **Important**: base texture is the material's *own* map (material+0x220 property group). Setting a texture does not clear the base colour; the displayed result is texture x colour in CLO's shader [I]. For an exact texture look set the base colour to white (1,1,1).

## 3. SetGraphic*MapTexture (Utility 219-230) vs base texture

- `SetGraphicBaseColorMapTexture(path, graphicStyleIndex[, colorway])` slots 219 (0x60505d0), 220 (0x6050320); Normal 221/222 (0x6051700/0x6051970); Opacity 225/226 (0x6051bf0/0x6051e60); (Displacement/Roughness/Metalness in the neighbouring slots).
- 220 body [V]: `60af0a0(this,&sp,idx)` fetches a **graphic-style object** from a separate document list (0x1c22e10 -> `[+8]` -> 0x4bc11b0, *not* the fabric list 0x1c22c90); null -> no-op. Then `4bbecd0(sp)` -> a material index, and `0x60fb230` which re-fetches the graphic style (60af0a0), looks up its material via 0x60aee50 and applies the same texture setter `0x3a73910` on that material's +0x220 property group, followed by the same UI refresh.
- **Conclusion: separate storage** [I, high confidence]. Graphic styles are their own list (indexed by `_graphicStyleIndex`) with their own material; the fabric base texture (`60fafe0` on a fabric material) is untouched. A print placed through the Graphic API therefore overlays rather than replaces the fabric base texture, which supports 09's recommendation. The plugin's `set-fabric-graphic` that calls SetBaseTexture... does replace the base map. Using the graphic API requires an existing graphic style (list may be empty on a plain garment -> silent no-op).

## 4. GetFabricIndexForPattern (from lane E, re-verified at the helper level)

- slot 51 `(pattern)` 0x5fe4a50: result stays **0** for any failure (scene null, `pattern >= size`, fabric ref null, index lookup < 0). slot 50 `(pattern, colorway)` 0x5fe4d90: default **-1** when scene/colorway/pattern invalid, but 0 when the fabric lookup fails inside 0x60ad0d0. Pattern and colorway indices are 0-based (colorway via `0x49fadc0(container, idx)`; null -> default) [M, per findings/12].
- Plugin consequence: `if (idx < 0) idx = 0` never fires for the 1-arg overload; 0 may mean "fabric 0" or "failure". Validate with `GetPatternCount()` and `GetFabricCount()` yourself, and treat the answer as unreliable until a fabric has been assigned (assign with `SetPatternPieceFabricIndex`/`AssignFabricToPattern`, then read it back).

## 5. Thread/GUI summary

| Call | UI touch | Thread |
|---|---|---|
| SetFabricPBRMaterialBaseColor (all 4) | 0x49a79e0, 0x5ccd3a0, app UI vfn calls; string forms also call colour-library UI object | GUI thread only [I] |
| SetBaseTexture...(211-214) | 0x5ccd3a0, app UI vfn 0x20 | GUI thread only [I] |
| SetGraphic*MapTexture | same refresh, plus app+0x78 object vfn+8 | GUI thread only [I] |
| GetFabricIndexForPattern, GetFabricPBRMaterialBaseColor | read only | safe on GUI thread; not verified for other threads |

None of the bodies contain thread marshalling; a stray call from a worker thread would touch Qt objects from the wrong thread.

## 6. Recommendations for the plugin

1. **Use the float colour overloads**, never the string ones (library-name lookup, not hex). Keep 0..1 = byte/255.0, `a=1.0`. Do not apply any gamma conversion in the plugin; the API stores raw values.
2. **Check the bool**: false means bad fabric/colorway/face or a missing property; surface it instead of reporting success.
3. **Read back** with `GetFabricPBRMaterialBaseColor(fabric, face)` after the set (it returns (1,0,0,0) on an invalid index, so also compare against the set value) and report both.
4. **Set Front (0) and Back (1)**; the call falls back to Front if Back has no own material, so it is safe. Skip Side (2) unless needed. Never pass face > 2.
5. **Range-check the fabric index** (`< GetFabricCount()`) before `SetBaseTextureMapImageGivenFilePath`: out-of-range silently textures the *currently selected* fabric. Check the file exists before the call (the API fails silently). Prefer the 5-arg overload (211) when you need the face or an error string (parse for `"failed"`); use `colorway=-1` only with a valid style chip.
6. **Reset the base colour to white** when applying a texture if you want true texture colours; a previously applied tint will multiply it [I].
7. **Use the Graphic API** (`SetGraphicBaseColorMapTexture`) only after confirming a graphic style exists; it does not overwrite the fabric texture, which the current `set-fabric-graphic` does.
8. Keep these calls on the GUI thread (PostMessage dispatch), and run the export after the posted lambda has finished (the refresh is synchronous inside the call, so no extra sleep is needed once the lambda returns).
9. `GetFabricIndexForPattern` returning 0 is ambiguous; verify via `GetPatternCount()` and the fabric list, and drop the `< 0` guard or use it only for the 2-arg overload.
