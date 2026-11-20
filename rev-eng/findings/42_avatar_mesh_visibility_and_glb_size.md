# 42 - Avatar mesh visibility and GLB size reduction (lane AP)

*Status: static analysis, 2026-10-29. No CLO run. Tags: [V] verified in header/disassembly/data, [I] inferred.*
*Scripts: `scripts/disasm_fn19.py` (copy of disasm_fn.py, cache `raw/disasm19/`). Raw: `raw/ap_5cb2520.txt`, `raw/ap_606e250.txt`, `raw/ap_602eca0.txt`, `raw/ap_50f2850.txt`, `raw/ap_5ccd3a0.txt`, `raw/ap_dan_bool_leaves.txt`, `raw/ap_dan_mesh_transformers.txt`, `raw/ap_visibility_offsets.txt`.*

## 1. API: there is NO per-part avatar visibility call [V header grep]
Searched UtilityAPIInterface.h, ExportAPIInterface.h, ImportAPIInterface.h, CloApiData.h, PatternAPIInterface.h for hair/shoe/eye/teeth/visib/hide/show/accessory/LOD/MeshName/MeshCount. There is no `SetAvatarShowHair`, `SetAvatarMeshVisibility`, `GetAvatarMeshNames/Count` or accessory toggle. Avatar-related virtuals that exist (all non-thunk, i.e. implemented, per `raw/verify_thunks.json`; slots via `slots_lookup.py`):

| Slot | Name / signature | Exe RVA | Use here |
|---|---|---|---|
| 75 | `void SetShowHideAvatar(bool)` (all avatars) | 0x606e440 | whole avatar only |
| 76 | `void SetShowHideAvatar(bool, int avatarIdx)` | 0x606e250 | whole avatar only |
| 77 | `bool IsShowAvatar(int avatarIdx)` | 0x602eca0 | returns avatar `vtbl[+0x70]` (see 2) |
| 109 | `bool SetAvatarMeshTexture(wstring shape, int matMesh 0 face/1 body/2 arm/3 leg, wstring img)` | 0x603f770 | textures only |
| 293 | `SetAvatarOpacityMapByIndex(path, matShapeIdx 0..3)` | 0x6040bc0 | opacity map, not geometry |
| 306 | `bool SetAvatarActivation(name, bool)` | 0x603dff0 | whole avatar |
| 347/348 | `SetAvatarSmooth(avatarIdx, level 1-3)` / `GetAvatarSubdivisionLevel` | 0x60420c0 / 0x5fd69a0 | would INCREASE vertices; base .dan has `/bOnSubDivision`=0 [V] so already off; never raise |
| 349/350 | `Set/GetAvatarProperties(idx, map<string,string>)` keys DivideMesh, SkinOffsetMM, friction, SoftBodySimulation | 0x6041900 / 0x5fd59f0 | no visibility keys documented [V header] |

`SetShowHideAvatar`/`IsShowAvatar` are logging wrappers ("Marvelous::UtilityAPI::SetShowHideAvatar(bool)" strings at 0x89a5ca0, IsShowAvatar 0x89a5d20); IsShowAvatar's core (0x50f2850) range-checks the index and returns `avatarObj->vtbl[+0x70]()` [V]. SetShowHideAvatar(bool) core is 0x5ccd3a0 (calls `[x+0x100]` / `[x+0xB8]` on the avatar sub-objects) [I]. Mesh order/index bases for the 9 glTF meshes: not exposed by any API. glTF mesh order [V, `u_001-065/result_avatar.glb`]: 0 shoes_r_Shape(2 prims), 1 shoes_l_Shape(2), 2 Hair(3), 3 body(4), 4 eye_L, 5 eye_R, 6 eyelash_L, 7 eyelash_R, 8 tooth_ (1 each). Skin i == mesh i, 92 joints each.

## 2. Exporter treatment of hidden objects [V code, I granularity]
`0x5cabc90` calls `0x5cb2520` for the avatar selection (finding 39). In 0x5cb2520 the per-object loop (rb-tree walk, loop head 0x145CB2620) does:
```
0x145CB2659  cmp byte [r13+2Bh],0      ; opt.bIncludeHiddenObject
0x145CB265E  jne  include
0x145CB2660  mov rax,[rsi]; mov rcx,rsi; call [rax+70h]   ; obj->vtbl[14]
0x145CB266B  je   skip(0x145CB282F)     ; result false -> object NOT selected
```
[V] With `bIncludeHiddenObject=false` (default) an object whose `vtbl+0x70` returns 0 is skipped. [V] The same virtual (`+0x70`) is what `IsShowAvatar` returns, so `+0x70` = "is visible/shown". The same pattern at 0x145CB2B0B is the second branch of the function. Therefore a hidden avatar object is not exported. [I, untested] Whether the iterated objects are whole avatars or the per-mesh transformers (hair/shoes) cannot be settled statically; `SetShowHideAvatar(false)` certainly drops the whole avatar (not wanted). Experiment is cheap: see 5.

## 3. `.dan` flags that control hair/shoes [V data, `raw/ap_dan_mesh_transformers.txt`]
Under `/mapTransformer3D` each mesh is a transformer node with `mapElement/bVisible`, `mapElement/bEditable`, `bAccessory`, `enAccessoryPart`, `bEnableExportOBJ`, `enElementType`=3 (22 for the `listMatShape[0]` shape child, which also carries `mapElement/bVisible`). Values in `input/base-1.avt`:

| Transformer | bAccessory | enAccessoryPart | bVisible (uncompressed .dan byte offset) |
|---|---|---|---|
| Hair (child of Head, depth 12) | 1 | **1** | transformer 934,878; shape 7,798,614 |
| shoes_r (child of Right_toe chain) | 1 | **2** | 157,983 (shape 511,461) |
| shoes_l | 1 | **3** | 541,020 (shape 894,498) |
| body, eye_L, eye_R, eyelash_L, eyelash_R, tooth | 0 | 0 | direct children of root, L[1..6] |

So CLO classifies hair and shoes as "accessory" parts (enAccessoryPart 1 hair, 2 right shoe, 3 left shoe; 0 none). Related: `listRiggedAccssory` (empty in the base) and the doc line "OB_TYPE_AVATAR subItemIndex = mesh index over the avatar's non-accessory meshes" [V CloApiData.h:1522] confirm hair and shoes are the accessory group, body/eyes/lashes/tooth the 6 non-accessory ones (materials mat 0 face /1 body /2 arm /3 leg live on body).
All are 1-byte bools (value 1). Per findings 31/13 the `.dan` re-encodes byte-identically and the `.avt` digest covers only the header, so patching a bool in place (same length) is safe for the container. [I] Setting `bVisible`=0 on the Hair transformer (and shape) makes the avatar load with hair hidden, so the 2 gate applies; setting `bEnableExportOBJ`=0 only affects OBJ export [I]. Whether the route that Mirra uses (patched `.avt`, `ImportAvatar`) preserves `bVisible` on load is untested (findings 19: some patched floats are not applied; visibility is read from the same tree as other flags so same risk applies).
Alternative if hiding is ignored: delete the Hair transformer subtree and `listSkinController[2]` from the `.dan` (grammar round-trips, lists are count-prefixed). Higher risk: skin-controller to mesh mapping is by index, shoes/hair other lists, and CLO may re-add accessories [I].

## 4. Sizes (from finding 25; 56 B per render vertex = pos12 + n12 + uv8 + joints u16x4 8 + weights f32x4 16)
Baseline: .bin 13,409,456 B; packed GLB 30,521,044 B (textures ~17.1 MB); 200,134 render vertices; 179,080 tris.
| Part | render verts | vertex B | index B (12/tri) | textures on disk |
|---|---|---|---|---|
| Hair | 141,426 (70.7%) | 7.92 MB | 75,252 tris = 0.90 MB | hair_main/cap/normal/roughness 1.64 MB (roughness PNG 0.90) |
| shoes (2) | 11,770 | 0.66 MB | 19,310 tris = 0.23 MB | sneaker 0.10 MB |
| body | 37,301 | 2.09 MB | 71,410 tris = 0.86 MB | arm/leg/body/face roughness PNGs 9.38 MB + colour/normal ~1.7 MB |
| eyes+lashes+tooth | 9,637 | 0.54 MB | 5,..k tris ~0.1 MB | small |
Hair total = 8.82 MB of the 13.41 MB bin (66%) and 10.46 MB of the 30.52 MB packed GLB (34%). The four body roughness PNGs (2.72+2.69+2.44+1.53 = 9.38 MB) are the single largest asset and are independent of hair.

## 5. Ranked plan
| # | Lever | Where | Expected saving (packed 30.52 MB) |
|---|---|---|---|
| 1 | Hide hair (and optionally shoes) so the exporter skips them: patch `.avt` `bVisible` bytes (934,878 and 7,798,614 for hair; 157,983/511,461 and 541,020/894,498 for shoes), `bIncludeHiddenObject=false` (default) | `.avt` patch + export option already default | hair: -8.82 MB bin, -10.46 MB total (to ~20.1 MB, bin 4.6 MB); shoes add -0.9 MB. [I] works only if gate is per mesh; verify by counting meshes in result GLB |
| 2 | Recompress the 4 roughness PNGs (grey JPEG q80 or 8-bit grey PNG; or drop them: glTF roughnessFactor 0.5 is acceptable) | offline post-process of the GLB images (stdlib cannot encode JPEG; needs the pipeline's existing image lib, or drop the roughness texture ref) | up to -8 to -9 MB. Largest win without touching CLO. [I] |
| 3 | If hair is kept: weld exact duplicate vertices | offline (finding 25: 141,426 -> 90,682 unique (pos,uv)); `weldType` exporter option showed no effect on avatar [I] | -50,744 x 56 B = -2.84 MB bin |
| 4 | JOINTS_0 u16 -> u8 (92 joints) and WEIGHTS_0 f32 -> u8 normalized (valid core glTF) | offline | 28 B/vertex saved? (joints 4 + weights 12) = 16 B/vertex; on all 200k: -3.2 MB; on hair-free 58,708 vertices: -0.94 MB |
| 5 | u32 -> u16 indices for every mesh with <65,536 vertices (everything except hair) | offline | 103,828 tris x 12 B halved = -0.62 MB |
| 6 | Drop eyelashes/tooth if not visible | offline | -0.25 MB |
Not exporter options: weld is an exporter field but ineffective on the avatar; u16 indices, weight precision, joint width have no ImportExportOption field [V header] so they are post-processing.
Not recommended: `SetAvatarSmooth` (only adds vertices), `SetShowHideAvatar` (drops the whole avatar).

## 6. Recipe for the Mirra pipeline
1. Step 1 payload builder (`step_06`/avt patch route): after the `.avt` is prepared, patch bytes at the offsets above in the uncompressed `.dan` (value 1 -> 0) for hair and shoes using `avs_grammar.leaf_map` (find leaves by `qsName`, not by hard-coded offsets: offsets shift after CLO re-saves the `.avt`), keep header and digest handling as is.
2. Export with `bExportAvatar=true`, `bIncludeHiddenObject=false`, scale 0.001 (unchanged).
3. Validate: `glb_probe.py summary` expects 5-6 meshes (no Hair; no shoes if patched), `meshes` sum of distinct POSITION counts about 58.7k (hair removed) or 46.9k (shoes also removed). If Hair is still present the gate is not per-mesh: fall back to the subtree deletion or to offline removal of `Hair` mesh/skin/nodes/materials/images from the GLB JSON+BIN (always works, since meshes are independent accessors).
4. Post-process the GLB offline (stdlib): drop unreferenced accessors/images, welding, u16 indices, u8 joints/weights, roughness maps.
5. Expected result: 30.5 MB -> ~20 MB with step 1-2 only; ~10-11 MB with roughness recompression and indices/weights. [I]
Order of confidence: offline hair removal (certain) > `.avt` bVisible (needs one CLO test) > exporter weld.

## Open items
- Whether the `0x5cb2520` iteration unit is the mesh transformer or the whole avatar object (needs one CLO run or tracing the container behind `0x1bf5d20`).
- Whether a patched `bVisible` survives `ImportAvatar`.
