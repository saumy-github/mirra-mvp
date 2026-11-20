# Finding: is the logo applied twice in CLO?

*Status: verified from code, not yet verified in a live CLO session*
*Written: 2026-10-18*

---

## 1. The claim being checked

> "Your pipeline applies every logo or text design twice: once baked into the flat texture by `texture_projection.py`, and once again as a native 3D decal by `step_08_apply_fabric.py`. The 'pattern' branch has a guard comment, but the same guard was never added for 'logo' and 'text'. This is a cheap, mechanical fix."

I checked this against the code. **The conclusion does not hold as written**, and the real situation is different, and more important, than a missing guard. Nothing was changed in the code.

---

## 2. What the code actually does (verified)

### 2.1 Step 6 (texture projection): the first application is real

`product_ingestion/step_06_0_texture_projection.py`, for a `logo` or `text` design:

- every panel is filled with one solid colour (the median fabric colour),
- the graphic is composited onto the **front panel only**, 30% of the panel width, 35% down from the top.

This part of the claim is correct.

### 2.2 Step 8 (apply fabric): the second application never runs today

`clo_vto/native_vto/step_08_apply_fabric.py`:

- The graphic step (step "d", lines 176-203) only runs when `design_type in ("logo", "text")`.
- `design_type` comes from `_load_design_type()` (lines 63-72), which reads `data.get("design_type", "")` from the **top level** of `image_info/extraction_metadata.json`.
- In that file, the value is nested: it lives at `data["design"]["design_type"]`. The top-level key does not exist.

I checked three real runs:

| Run | `data.get("design_type","")` | Real value at `data["design"]["design_type"]` |
|---|---|---|
| `c_001/s_001/001` | `''` | `logo` |
| `c_002/s_001/001` | `''` | `text` |
| `c_003/s_001/001` | `''` | `logo` |

So `design_type` is always empty, the `logo`/`text` branch is never taken, and the "pattern" guard message is never printed either. Every run falls through to "No graphic diffuse found or non-logo design, skipping graphic overlay". **The double application cannot happen today, because of this key mismatch.**

### 2.3 If that key were fixed, `set_fabric_graphic` is not a decal

`clo_workspace/windows/RestPlugin_windows.cpp`:

- `POST /set-fabric-graphic` parses `u`, `v` and `scale` (lines 1474-1476) but the handler that runs the command (lines 2106-2125) **never uses them**.
- That handler calls `FabricDispatcher::dispatchTexture(fabric_idx, path)`, which ends in `SetBaseTextureMapImageGivenFilePath`. Its own comment says: "Dispatched identically to set-fabric-texture (base texture replacement)."

So a "graphic overlay" is really **another base-texture replacement**. It does not place a logo at (u, v) with a scale. The Python docstring ("Place a graphic overlay (logo, print) ... u, v are normalised UV coordinates") describes behaviour the plugin does not have.

### 2.4 All four pieces share one fabric, so per-piece textures overwrite each other

- `set_fabric(idx, fabric_index=0)` is sent for all four pieces. The plugin handles it with `SetPatternPieceFabricIndex(pattern, 0)`. So **every piece uses fabric 0**.
- Colour, texture and graphic all go to `GetFabricIndexForPattern(pattern)`, which is the same fabric (0) for every piece.
- Therefore the four `set_fabric_texture` calls (front, back, sleeve_left, sleeve_right) all write to the same fabric; the **last one wins**. The graphic call would overwrite that again.

This is consistent with what the code's own comment (lines 145-151) says about the atlas "rendering wrong": it is treated as a repeating swatch, and transparent regions show skin through the garment. That comment is the reason the `CLO_PLAIN_FABRIC=1` switch exists.

---

## 3. What this means

| Question | Answer |
|---|---|
| Is the logo applied twice today? | **No.** The second application never runs (wrong metadata key). |
| Would it be applied twice if the key were fixed? | **Worse than twice.** The second call replaces the first, and the result is `graphic_diffuse.png` (a small cropped logo image) set as the **base texture of the shared fabric**, with `u`, `v`, `scale` ignored. |
| Is adding the same guard as the "pattern" branch enough? | **No.** The guard would hide a symptom. The real constraints are that CLO's texture call is a swatch, not a UV map, and that all pieces share one fabric. |
| What does the viewer probably see now? | **Not confirmed live.** From the code: base colour on fabric 0, then the last panel texture (`sleeve_right_texture.png`) as a repeating swatch. The logo would not appear where intended. |

**Do not "fix" the key alone.** Reading `data["design"]["design_type"]` would switch on the overwrite behaviour above.

---

## 4. Options to fix it properly

| # | Option | What it needs | Risk |
|---|---|---|---|
| A | **Keep flat colour only** (what `CLO_PLAIN_FABRIC=1` does). Stop sending textures and the graphic | nothing | no logo or print in the try-on |
| B | **Give each piece its own fabric**, then per-panel textures can work | **SDK supports it** (section 5): `AddFabric`, `AssignFabricToPattern`, `SetTextureMapping`; our plugin exposes none of them yet | plugin work; "Unified" mapping behaviour must be checked live |
| C | **Apply the print as a real decal/graphic** at a chosen position and size | **SDK supports it** (section 5): `AddGraphicStyleFromImageFile` then `AddGraphicStyleToPatternV2`; not exposed by our plugin yet | plugin work; coordinate units must be checked live |
| D | **Bake the print into a tileable texture** in Step 2 so a swatch-style apply looks right (see FabricDiffusion in `04-improvement-options.md`) | extra model; work on tiling and scale | only works if the texture really tiles at the right physical size |
| E | **Skip CLO textures; add the print later** in a renderer or web viewer | a different render step | outside the CLO pipeline |

**Recommended order**

1. **Look first.** Run Step 3 live in CLO twice (with and without `CLO_PLAIN_FABRIC=1`) and take screenshots of what the front panel shows. This costs minutes and tells us what is really on screen.
2. ~~Read the CLO SDK headers~~ **Done on 2026-10-18** (SDK `v2026.1.224`, Windows). Results are in section 5.
3. Options B and C are both supported by the SDK. The real work is adding plugin endpoints and client calls for them, then testing live.

---

## 5. What the CLO SDK offers (headers read, nothing run)

*SDK folder: `CLO_SDK_v2026.1.224_Win`, headers in `CLOAPIInterface/include/`. This is what the **headers** declare. I have not called any of these functions, so every behaviour below is from the doc comments, not from a test.*

### 5.1 The real graphic (decal) API

| Step | Function (header) | What the doc comment says |
|---|---|---|
| 1 | `AddGraphicStyleFromImageFile(path, index)` (`UtilityAPIInterface.h`) | "Converts an image file to a graphic style and inserts it into the graphic file list at the given index." Also `ImportGraphicStyleFromImage` / `ImportAsGraphic` (`ImportAPIInterface.h`) |
| 2 | `AddGraphicStyleToPatternV2(patternIndex, graphicStyleIndex, x, y, width, height, face, zOffset, angle)` | Places the graphic on one pattern piece, **centre at (x, y)**, size width × height. x grows to the right, y grows **downward**; "in a 100 × 100 pattern the bottom-right corner is (100, 100)". `face`: 0 front, 1 back, 2 both. Returns a status string. (`AddGraphicStyleToPattern` is the older version that returns a bool.) |
| alt | `AddGraphicStyleToPattern(patternIndex, styleIndex, [left, right, top, bottom], centreFlag, face, zOffset, angle)` (`PatternAPIInterface.h`) | Same idea with coordinates relative to the pattern's bounding box |
| later | `SetGraphicStylePositionOnPattern`, `SetGraphicStyleDimensionsOnPattern`, `RepositionGraphicByAnchor`, `GetGraphicStylePlacementPoints`, `SetGraphicStyleColor`, graphic normal / opacity / roughness maps | adjust or re-place a graphic after adding it |

The unit of x, y, width and height is not stated in these comments; the example uses a "100 × 100" pattern, so it is probably the pattern's own units (mm, as our DXFs are in mm). **Check live.**

This is the call `set-fabric-graphic` pretends to be. It gives a true logo at a measured position and size on a chosen piece, which is exactly what the Python docstring promised.

### 5.2 Separate fabrics per piece

| Function | What the doc comment says |
|---|---|
| `AddFabric(path)` | Adds a fabric to the object browser from a `.zfab` (CLO file) or `.jfab` (JSON) file; **returns the new fabric's index** |
| `AssignFabricToPattern(fabricIndex, patternIndex, assignOption)` | Assigns that fabric to one pattern piece. `assignOption`: 1 = current colorway only, 2 = all colorways with unlinked materials, 3 = all colorways linked |
| `CreateZfabFromTextures(zfabPath, base, normal, displacement, opacity, roughness, metalness)` | Builds a `.zfab` from texture images (so a panel texture PNG can become its own fabric) |
| `ReplaceFabric`, `DeleteFabric`, `ChangeFabricWithJson(fabricIndex, jfabPath)` | replace, delete, or overwrite a fabric from JSON |
| `SetFabricWidth/Length(fabricIndex, mm)` | the **physical size of the texture swatch** in mm |
| **`SetTextureMapping(fabricIndex, 0 or 1)`** | "Set Texture Mapping Type (**Repeat** or **Unified**)": 0 = Repeat, 1 = Unified |
| `AddTextureToPatterns(image, colorway, fabricIndex, styleChip, aopMode, side)` and `TransformAOPOnFabric(...)` | apply an all-over-print texture (print mode or base-colour mode) and rotate, scale or move it |

Why this matters: our plugin never calls any of these. It only uses `SetPatternPieceFabricIndex(piece, 0)`, which points every piece at fabric 0, and then `SetBaseTextureMapImageGivenFilePath` on that one fabric. The SDK lets us instead create one fabric per piece, assign each to its piece, and set **Unified** mapping so a panel texture is spread over the piece once instead of tiling. *Whether Unified behaves that way is the key thing to confirm live.*

### 5.3 Fabric physics also has an API path (relevant to fabric-property estimation)

The SDK's `Documents/JFABSpec.json` documents the fabric file format. Its `mapPhysical` block holds the physical properties, with these meanings (taken from the spec's own comments):

| Key | Meaning in CLO |
|---|---|
| `fSuK`, `fSvK` | Stretch-Weft, Stretch-Warp |
| `fHK` | Shear |
| `fBuK`, `fBvK`, `fBhK` | Bending-Weft, Bending-Warp, Bending-Bias |
| `fBuLR`, `fBvLR`, `fBhLR` | Buckling Ratio (weft, warp, bias) |
| `fBucklingStiffnessU/V/H` | Buckling Stiffness (weft, warp, bias) |
| `fDensity`, `fThickness`, `fFriction`, `fIDS` | Density, Thickness, Friction, Internal Damping |
| **`enFabricType`** | a fabric category label: 0 Default, 1 Silk, 2 Cotton, 3 Wool, 4 Denim, 5 Leather, 6 Cashmere, 7 Satin, 8 Spandex, 9 Rayon, 10 Linen, 11 Taffeta, 12 Polyester, 13 Terrycloth, 14 Flannel, 15 Burlap, 16 Rubber |

- `AddFabric(jfabPath)` or `ChangeFabricWithJson(fabricIndex, jfabPath)` can load such a file, so a per-cloth physics preset can be written as a `.jfab` and applied through the SDK. `Documents/fabric_sample.jfab` is a complete `mapPhysical` example.
- The `enFabricType` list is a ready-made **label set for a fabric classifier** (17 classes). The spec calls it a "Fabric Type"; I do not know whether setting it also changes the numeric values, so that needs a test.
- I still found no numeric values for cotton, denim or silk; those would have to be measured or chosen (see `04-improvement-options.md`, D8).

### 5.4 What a proper CLO apply step could look like (a plan, nothing built)

1. Per piece: create a fabric from the piece's texture (`CreateZfabFromTextures`, or `AddFabric` of a base `.jfab` then set its texture), `AssignFabricToPattern`, `SetTextureMapping(…, 1)`, and size it with `SetFabricWidth/Length` if needed.
2. For `logo` and `text` designs: make the texture a **plain colour** (no baked logo) and place `graphic_diffuse.png` with `AddGraphicStyleFromImageFile` + `AddGraphicStyleToPatternV2` at a measured position. This removes the "logo baked and applied again" ambiguity for good.
3. Physics: write a per-cloth `.jfab` with `mapPhysical` and apply it.
4. Plugin work needed: new endpoints and queue handlers for the calls above (they must run on CLO's main thread like the existing fabric calls), matching client methods, and an entry in `plugin_contract.json` for both Windows and macOS builds (the contract requires parity).
5. Fix `_load_design_type` only as part of this change.

Open questions to answer by testing: units of graphic coordinates; what "Unified" mapping does with a texture whose size differs from the piece; whether CLO keeps seam allowance or the 0.1 import scale in these coordinates.

---

## 6. Files and lines referred to

| File | Lines | What |
|---|---|---|
| `clo_vto/native_vto/step_08_apply_fabric.py` | 63-72 | `_load_design_type` reads the wrong key |
| same | 106-108 | `set_fabric(idx, fabric_index=0)` for every piece |
| same | 145-174 | `CLO_PLAIN_FABRIC` and the texture loop |
| same | 176-203 | graphic step and the "pattern" guard |
| `clo_workspace/windows/RestPlugin_windows.cpp` | 1464-1490 | `/set-fabric-graphic` parses `u`, `v`, `scale` |
| same | 2044-2049 | `set-fabric` assigns the fabric index to a pattern |
| same | 2083-2125 | texture and graphic handlers (the graphic handler is the texture handler) |
| `product_ingestion/step_06_0_texture_projection.py` | `project_all` | solid colour for logo/text, graphic pasted on the front |
