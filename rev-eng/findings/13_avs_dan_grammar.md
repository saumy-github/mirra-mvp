# Lane F: typed property stream grammar (.avs / .dan / .osw) and .avt header fields

*Status: done (static analysis only; CLO not run; no files written outside rev-eng/)*
*Date: 2026-10-29*
*Code: `scripts/avs_grammar.py` (parser + exact writer + `roundtrip`, `tree`, `dandiff` commands). Raw: `raw/avs_tree.json`.*
*Labels: **VERIFIED** = reproduced by code on real files; **INFERENCE** = plausible reading, not proven.*

All integers little-endian. Offsets are decimal unless prefixed `0x`.

## 1. Grammar (VERIFIED)

The same grammar covers `.avs`, the `.dan` inside `.avt`, and `.osw` (see roundtrip results in section 1.3). There is no magic number and no checksum. The earlier idea (file 10, section 4) that the first bytes were a "type-code table" was half right: they are a *column-oriented block header*.

### 1.1 Block (a "struct")

```
block := u8  n                      ; field count (0..255; no larger counts seen)
         u8  namelen[n]             ; length of each key name
         u8  type[n]                ; type code of each field
         u32 size[n]                ; byte size of each field's VALUE
         ( name[i] value[i] )*n     ; names and values interleaved, in field order
```

The whole file is one top-level block. `.avs`: `03 0a 0e 0d | 0f 0f 16 | 13000000 13000000 58090000 | "qsAvatarID" <19 bytes> "qsAvatarIDUTF8" <19 bytes> "MVresizingMap" <0x958 bytes: a nested block>`. The `.dan` top-level block has n = 0x3d = 61 fields (header = 1+61+61+244 = 367 bytes) and ends exactly at EOF (33,066,665 for the base male). Because every value carries its byte size, any parser can skip unknown types; the only things needing semantic knowledge are the type codes below.

### 1.2 Type codes (value encoding given by the size column)

| Code | Meaning | Value bytes | Status |
|---|---|---|---|
| 0x01 | bool | 1 byte (0/1) | VERIFIED |
| 0x04 | int32 (also enums `en*`, indices `i*`) | 4 | VERIFIED |
| 0x05 | uint32 (`ui*`) | 4 | VERIFIED (only seen in .dan/.osw, not .avs) |
| 0x06 | float32 (`f*`) | 4 | VERIFIED |
| 0x0a | vec2 (`v2*`) 2 x float32 | 8 | VERIFIED by size/name |
| 0x0b | vec3 (`v3*`, `massCenter`, `p0/p1`) 3 x float32 | 12 | VERIFIED by size/name |
| 0x0c | vec4 (`v4*` colours) 4 x float32 | 16 | VERIFIED by size/name |
| 0x0e | mat4 (`m4*`) 16 x float32, 64 bytes | 64 | VERIFIED by size/name (row/col order not determined) |
| 0x0f | string / byte blob (`qs*` QString-as-UTF8, `ba*` byte array, `utf*`) | size bytes, no terminator, no length prefix of its own | VERIFIED |
| 0x14 | list | `u32 count` then, if count > 0: `u8 elemtype`, `u32 elemsize[count]`, then the elements back to back. An empty list is exactly 4 bytes (`00 00 00 00`, no type byte). Elements are parsed by `elemtype` (so a list of 0x16 is a list of structs, a list of 0x14 is a list of lists, a list of 0x04 has one 4-byte size entry per int) | VERIFIED |
| 0x15 | array (`arr*`) of packed scalars | `u32 count`, `u8 elemtype` (04 int, 05 uint, 06 float seen), `count x sizeof(elem)` packed, no per-element size table. Size is `5 + count*4` (9, 13, 17, 21, 25, 373 seen) | VERIFIED (sizes), element types INFERENCE from 4 samples |
| 0x16 | struct | a nested `block` | VERIFIED |

Key-name prefixes follow the Hungarian convention and agree with the type codes: `b`=0x01, `i`/`en`=0x04, `ui`=0x05, `f`=0x06, `v2/v3/v4/m4`=0x0a/0x0b/0x0c/0x0e, `qs*/ba*/utf*`=0x0f, `list*`=0x14, `arr*`=0x15, `map*`=0x16.

Quirk: a "list" is size-tabled (random access, heterogeneous element sizes), an "array" is not. Lists of ints/floats (e.g. `listFeatureValues`) therefore cost 8 bytes per value (4 for the size entry + 4 data).

### 1.3 Round-trip results (VERIFIED, `python -I avs_grammar.py roundtrip FILE...`)

- **184 of 184** `.avs` files found anywhere under the repo (default avatars from `.agent/saumy/research_files/CLO/CLO Assets`, `clo_avatar_generation/input/CLO_Male_Default.avs`, pipeline `clo_payload.avs` outputs, Phase-0 experiment `.avs`, ASTM size files) parse and re-encode to **identical bytes**. No `.avs` exists under `C:\Program Files\CLO Standalone OnlineAuth` (0 found).
- The `.dan` from `clo_avatar_generation/input/base-1.avt` (33,066,665 bytes, 289,891 type-0x15 and 146,396 type-0x05 values, 1,242 structs) re-encodes **byte-identically** (parse+encode takes ~2 s). See the end of this file for the wider `.dan`/`.osw` sweep.

Variant seen in `.avs`: three sizes of header value fields (2486/2488/2490/2498 B differ only in the avatar-id string length 0x13/0x14/0x15/0x19; the 2881-2885 B variants carry 5 extra fields (cup-size block, below)).

## 2. `.avs` key/value tree (male default) - `raw/avs_tree.json`

Top level (3 fields): `qsAvatarID` = `"5.1_MaleTemplate_07"` (the 3 fields are the avatar template id, its UTF-8 twin, and the map).
`MVresizingMap` (struct, 16 fields in the 2486 B default; 22 in the cup-size/"custom" variant):

| Key | Type | Default value | Meaning (INFERENCE unless noted) |
|---|---|---|---|
| bWidthLinked / bHeightLinked | bool | true / true | link width / height sliders |
| DetailFeature | int32 | 0 | |
| bUseProportionBase | bool | false | |
| listMeasureMode | list<int32> x62 | mostly 0; idx0=3, idx2=1, idx4=2, idx6..9=2, idx15=2, idx26=4, idx36=4, idx47=4, idx58..61=5 | per-measure edit mode; the six primary pipeline fields (0,2,6,8,26,36) are not all non-zero, so the enum meaning is unresolved |
| WidthBaseFeature, ProportionBaseFeature, BaseFeature | int32 | 0, -1, 0 | feature index selectors (-1 = none) |
| listMeasureDiffValues | list<float> x62 | all 0.0 | per-measure delta from base |
| bUseCFNeckToWaist / bUseCBNeckToWaist / bUseTotalRise | bool | true | |
| fBaseFeatureBustCircum | float | 9.824459 | cm? (bust base reference) |
| enLastUpdateMode | int32 | 4 | |
| **listFeatureValues** | list<float> x62 (x67 in `.dan` and cup variant) | see table | **the measurement vector, cm** |
| listMeasureLinkList | list<list> x62 | all empty lists | measure links |
| (cup variant only) listCupSizeValueList, bUseCupSize, SelectedCupSizeIndex, listCupSizeName, utfSizeFileName, utfSizeFileNameUTF8 | | `[75,100,125,150,170,200]`, false, 0, `["AA","A","B","C","D","E (DD)"]`, "", "" | bra cup selection |

The file-10 statement "57 floats" is wrong: the real vector is **62** floats in the default `.avs` and **67** in the `.dan` (indices 62..66 = 0,0,0,50,50 in the base male). The old probe's 57 was a plausible-looking prefix. The `.dan` feature block is `/mapResizingAvatar/listFeatureValues`: list header at .dan offset **33,021,541** (`u32 count=67`, `u8 type=06`, 67 x `u32 size=4`, then data), so the float data starts at 33,021,541 + 5 + 268 = **33,021,814** (matches the old heuristic, VERIFIED). In the `.avs` default the list header is at 1465 so data starts at 1465+5+248 = **1718**, VERIFIED.

### 2.1 listFeatureValues index map (units: centimetres, VERIFIED for unit; names are INFERENCE)

Method: each of the 62 floats was compared with `default-avatar-csv.csv` (CLO's measurement export of the same default male, values in mm). 47 of 62 match a CSV row within 0.06 cm; ordering of indices follows CLO's measurement list. Full table in `raw/avs_tree.json` under `_feature_index_map`.

| idx | cm | Name | | idx | cm | Name |
|---|---|---|---|---|---|---|
| 0 | 187.96 | Total Height (CSV shows 188.93 = measured mesh, see 3.3) | | 31 | 9.335 | Ankle Height |
| 1 | 70.0 | ? (weight kg?) | | 32 | 30.82 | ? |
| 2 | 96.52 | Bust/Chest Circ | | 33 | 20.09 | ? |
| 3 | 37.55 | Mid Neck Circ | | 34 | 38.12 | Across Front |
| 4 | 40.96 | Neck Base Circ | | 35 | 37.40 | Across Back |
| 5 | 89.39 | Under Bust Circ | | 36 | 44.13 | Across Shoulder (Curvilinear) |
| 6 | 82.55 | Waist Circ | | 37 | 21.81 | Across Shoulder (CB Neck) |
| 7 | 88.26 | High Hip Circ | | 38 | 10.00 | CF Neck to Across Front |
| 8 | 95.25 | Low Hip Circ | | 39 | 16.30 | CB Neck to Across Back |
| 9 | 55.88 | Thigh Circ | | 40 | 43.55 | CF Neck to Waist |
| 10 | 50.60 | Mid Thigh Circ | | 41 | 49.41 | CB Neck to Waist |
| 11 | 37.60 | Knee Circ | | 42 | 8.40 | Waist to High Hip |
| 12 | 36.67 | Calf Circ | | 43 | 17.65 | Waist to Low Hip |
| 13 | 24.33 | Ankle Circ | | 44 | 20.90 | Apex to Apex |
| 14 | 48.15 | Armhole Circ | | 45 | 26.70 | HPS to Apex |
| 15 | 32.39 | Bicep Circ (CSV 32.31, approximate) | | 46 | 71.22 | Halter |
| 16 | 27.14 | Elbow Circ | | 47 | 64.85 | Arm Length |
| 17 | 18.26 | Wrist Circ | | 48 | 86.66 | ? |
| 18 | 161.91 | HPS Height | | 49 | 73.65 | Total Rise |
| 19 | 155.96 | Shoulder Height | | 50 | 33.34 | Front Rise |
| 20 | 5.95 | Shoulder Drop | | 51 | 40.31 | Back Rise |
| 21 | 139.00 | Bust Height | | 52-54 | 29.01, 23.00, 13.69 | ? |
| 22 | 134.48 | Under Bust Height | | 55 | 84.28 | Front Vertical Trunk |
| 23 | 115.40 | Waist Height | | 56 | 92.58 | Back Vertical Trunk |
| 24 | 107.03 | High Hip Height | | 57 | 176.87 | Vertical Trunk |
| 25 | 97.83 | Low Hip Height | | 58 | 19.65 | Hand Length |
| 26 | 86.36 | Inseam Height | | 59 | 56.00 | Head Circ |
| 27 | 82.92 | Thigh Height | | 60-61 | 30.0, 30.0 | ? |
| 28 | 72.69 | Mid Thigh Height | | 62-64 | 0, 0, 0 | ? (.dan/cup-variant only) |
| 29 | 53.27 | Knee Height | | 65-66 | 50, 50 | ? (.dan/cup-variant only) |
| 30 | 37.09 | Calf Height | | | | |

The 7 CSV-listed rows are matched uniquely except idx 3/11 (37.552 vs 37.597; assigned to Mid Neck / Knee by nearest value). The user-facing "body parameters" the pipeline patches (0, 2, 6, 8, 26, 36) agree with `avt_patch.json`. Only **targets** are stored: the CSV's Total Height of 188.93 is the measured result on the mesh while the stored value is 187.96, i.e. the mesh is not exactly the target.

Other `MVresizingMap`-level parameters: `listMeasureMode` (0-5 enum), `listMeasureDiffValues`, `fBaseFeatureBustCircum`, flags above. No weight/skin-tone/face keys exist in the `.avs`; those would be elsewhere in the `.dan` (`mapModelParameter`, materials) - not explored.

## 3. `.dan` structure and section offsets (base-1.avt, uncompressed .dan = 33,066,665 B)

### 3.1 Top-level fields (VERIFIED; offsets are of the value)

| Field | Value offset | Size |
|---|---|---|
| mapDefaultAvatarRoot (skeleton hierarchy, 92 joints expected) | 581 | 141,299 |
| mapTransformer3D (scene graph holding all mesh shapes) | 141,896 | 11,116,459 |
| mapInitPoseData | 11,258,370 | 141,370 |
| **listSkinController** (9 controllers) | 11,399,758 | 21,603,787 |
| mapModelParameter | 33,003,582 | 121 |
| listPan | 33,003,752 | 15,596 |
| **mapResizingAvatar** (contains listFeatureValues) | 33,019,981 | 2,787 |
| listArr | 33,022,775 | 30,723 |
| listTf3DToHIKNodeId | 33,053,586 | 2,965 |
| mapStyleConfig | 33,056,788 | 603 |
| listTf3DToTposeLtoW | 33,057,730 | 8,935 |

(Offsets come straight from `index_block`; the full leaf index is reproducible with `leaf_map()`.) Root-level strings: `qsAvatarID`=`5.1_MaleTemplate_07`, `qsAvatarName`=`MV2.1_Jinho`, `qsSizingSrcFileName`=`CLO_Male_Default` (so the `.avt` records which `.avs` size file it came from), `qsProductVersion`=`2.5.9999.99999`.

### 3.2 Meshes: where the vertices, indices, UVs and weights live (VERIFIED)

Nine mesh shapes live under `mapTransformer3D`, each as `.../listMatShape[0]/mapShape` with:

| Leaf | Type / stride | Content |
|---|---|---|
| `listSource[0]/baArray` | float32 x3 (12 B/vertex) | render-vertex **positions**, **millimetres** |
| `listSource[1]/baArray` | float32 x3 | **normals** |
| `listSource[2]/baArray` | float32 x2 (8 B/vertex) | **UVs** |
| `baRenderToNormalIndex`, `baRenderToPhysicalPos` | uint32 x N | render-vertex -> normal / physical (skin) vertex index; identity (0,1,2,...) at start |
| `listIndexedMesh[k]/baPositionIndex` | uint32 x (3 x tris) | triangle index list per material primitive |
| `listIndexedMesh[k]/arrayIndexLength` etc. | | per-primitive counts |

Per shape (render vertices, tris per primitive); position-array absolute offsets; order = file order:

| # | Verts | Primitive tris | listSource[0] offset | Identification (INFERENCE from GLB prim counts + Y ranges) |
|---|---|---|---|---|
| 0 | 5,885 | 9,148 + 507 | 158,571 | shoe R (2 prims) |
| 1 | 5,885 | 9,148 + 507 | 541,608 | shoe L |
| 2 | 141,426 | 2,775 + 69,702 + 2,775 | 935,466 | hair (3 prims; positions are in local space, Y -83..84) |
| 3 | 37,301 | 15,520 + 17,170 + 16,940 + 21,780 | 7,923,705 | **body** (4 prims; Y 13..1903 mm = standing height) |
| 4, 5 | 298 each | 592 | 10,603,294 ; 10,637,782 | eyelash L/R |
| 6, 7 | 1,790 each | 1,432 | 10,672,278 ; 10,777,800 | eye L/R |
| 8 | 5,461 | 9,060 | 10,883,314 | tooth |

Totals: **200,134 render vertices, 179,080 triangles**. The triangle total **equals the GLB's 179,080 triangles exactly** (VERIFIED), and the primitive splits equal the GLB meshes (shoes 2, hair 3, body 4, others 1). The GLB's 606,659 vertices are **not** the .dan render-vertex count (200,134); the glTF exporter expands vertices (likely unwelding per face attribute) - the exact rule is UNKNOWN. Positions: stride 12 B, no header/count inside `baArray`; count = size/12.

Skinning (`/listSkinController[0..8]`, 21.6 MB at 11,399,758). Each controller is a struct with: `baInitPosition` (float x3 rest positions of the physical vertices, mm), `mapMesh/baPosition` (current deformed positions), `mapMesh/baIndex` (triangles), `baLocalPosition`, `baABGList`, `baTriangleIndexList`, `baItoL` (64 B inverse-to-local matrix, or 5,888 B = 92 mat4 for the non-body ones), `arrJointIndexList` (373 B on controllers 3-8: bone list), and **`listJointWeight`**: a list with one struct per physical vertex `{uiInfluenceCount: uint32, arrWeight: array<float>, arrJointIndex: array<uint>}` (so weights are stored per vertex with a variable number of influences, e.g. `1, [1.0], [0]`). Physical-vertex counts per controller 0..8 = 4,881 / 4,881 / 90,634 / 35,739 / 298 / 298 / 1,790 / 1,790 / 4,597 = **144,908** = number of `uiInfluenceCount` values (VERIFIED). Joint count: the per-vertex joint indices index a 92-joint skeleton, the 92 itself was not re-counted here (taken from the GLB, 92 per skin; UNVERIFIED in .dan).
Offsets of the large blocks (absolute): `listSkinController[2]/baTriangleIndexList` 13,029,743 (362,536 B); `[2]/baInitPosition` 13,392,431 (1,087,608 B = 90,634 x 12); `[2]/listJointWeight` 14,480,054 (7,522,627 B); `[2]/baABGList` 22,003,123; `[2]/mapMesh/baPosition` 23,090,881; `[3]/baInitPosition` 26,477,098 (428,868 B = 35,739 x 12); `[3]/listJointWeight` 26,905,981 (3,321,014 B).

Note: controller [2] (90,634 verts) has Y range 1700..1921 mm, i.e. it is the head/face region; controller [3] is the body. The mapping skin-controller index <-> render shape is not explicit in this pass (shape 3, 37,301 render vertices, vs controller [3] 35,739 physical vertices; render count > physical count as expected from UV seams) - INFERENCE.

## 4. Do .dan vertex positions depend on listFeatureValues? (VERIFIED, measured)

`python -I avs_grammar.py dandiff A B [minbytes]` compares every leaf by path (immune to the .dan length changing). Inputs (all under `clo_avatar_generation`): base = `input/base-1.avt` (187.96 cm), `output/u_001-091/result_avatar_from_project.avt` (route **avt_patch**, requested 178.5), `output/u_001-092/result_avatar_from_project.avt` (route **avs**, 178.5), `output/g_e5c37ff7a450d060-001/result_avatar_from_project.avt` (route **avs**, 137.0).

| Compared with base | listFeatureValues bytes differing | position/normal arrays | UV, indices, weights, joint idx, tri lists |
|---|---|---|---|
| un-imported patched `.avt` (`g_241f...-001/clo_payload.patched.avt`) | 18 (6 floats) | **0** | 0 (whole .dan differs in exactly those 18 bytes) |
| avt_patch route, after CLO import+save (u_001-091) | 156 | **0 bytes** in every listSource, baInitPosition, baPosition | 0 |
| avs route, 178.5 (u_001-092) | (set by .avs) | listSource[0] 1,758,941 of 2,401,752 bytes differ; listSource[1] (normals) 1,778,720; baPosition 1,277,615 of 1,738,896; baInitPosition 385,719; max single-float change up to 100 mm (whole body shifts down ~100 mm), body-region shift 94 mm in Y max | **0** for UV, `baPositionIndex`, `baIndex`, weights, joint indices, `baRenderTo*`, `baTriangleIndexList` |
| avs route, 137.0 (g_e5c37...) | | listSource[0] 1,783,058; baPosition 1,296,826; max change ~523 mm | 0 |

Conclusion (VERIFIED for the observed routes): the **mesh topology, UVs and skin weights are identical for every avatar**; only vertex positions (and normals, rest positions, joint matrices `m4LtoW`, `baItoL`) change, and only when the `.avs` route is used. On the avt_patch route CLO re-saves the exact same positions (0 bytes differ) even though `listFeatureValues` in the saved `.dan` shows the requested numbers - the patched floats are stored but **not applied** (the resize engine does not run when loading an `.avt`). Body Y extent (shape 3, mm): base 13..1903, avs-178.5 13..1809, avs-137 13..1396 (feet stay at ~13 mm), so height scales the body from the floor up. Eyes/teeth/lashes move with the head (+/-100 mm at 178.5; +/-520 mm at 137 vs 187.96).

Nondeterminism (explains the "two identical-input runs differ" question in file 10 section 6): `u_003-004` vs `u_003-005` (identical 175 cm inputs, avs route) differ in 1,756,032 .dan bytes, all in position/normal/`baItoL`/`m4Matrix` float arrays with a **maximum single-float change of 0.0019 mm** (and 4-byte .dan length difference). That is float-level solver noise, not a content difference; it is enough to change GLB BIN hashes.

Other differences between a fresh base and any CLO-resaved `.dan` (benign, VERIFIED): ids in `uiID`/`uiShapeID`/`uiParentID` (2 bytes each, renumbering), new empty fields (`listCurve`, `listRiggedAccssory`, `listMorphTarget`, `fSkinInwardOffset`, `iSoftBodyMeshQuality`), `qsUuid` 38 -> 36 chars, `qsUniqueId` moved from root of `mapTransformer3D` to the top, `qsProductVersion` 14 -> 16 chars (the CLO build), `qsSizingSrcFileName` changes with the `.avs` used (16 -> 11 bytes = the temporary `.avs` name length; `clo_payload`).

## 5. `.avt` header fields 0x14, 0x30, 0x3C and the ZIP-length question

Swept all 379 `.avt`/`.zprj` files in the repo with the CLO magic (read-only).

| Field | Result | Status |
|---|---|---|
| 0x10 | format version: 12 (367 files), 11 (10 presets) | VERIFIED |
| **0x14** | equals **(PNG offset at 0x18) - 24** in 378 of 379 files (237 = 261-24, zprj 218 = 242-24); the one exception is a corrupt/foreign file. Points 24 bytes before the first PNG (offset 0xED, inside the avatar-id string at 0xEA) - the target is not a field boundary, so it is a derived constant of the header layout. Purpose unknown; safe to treat as "PNG offset - 24" | VERIFIED relation, meaning UNKNOWN |
| 0x28 (u64) | millisecond Unix timestamp (e.g. 1774958706515). **The earlier note "0x30 = 413" was wrong:** 413 (0x19d) is the *high dword of the u64 timestamp at 0x28*. | VERIFIED correction |
| **0x30** | u32 = **2010** in 367 files, **2008** in the 10 version-11 presets (one outlier 2250 in a non-standard file). It is not a build number or timestamp half. Same value repeats at 0x3C. Plausibly a stream/format revision constant for the avatar block ("CLO file-format year/rev") | VERIFIED value set, meaning INFERENCE |
| 0x34 (u64) | second timestamp, equal to 0x28 in 357 of 379 files (differs in 22: re-saved files) | VERIFIED |
| **0x3C** | u32, equal to the 0x30 value in 377 of 379 files (so 0x30 and 0x3C each trail a timestamp: `[u64 ts][u32 rev][u64 ts][u32 rev]`) | VERIFIED |
| 0x40 | `u32 len` + id string (20 chars), then 16 zero bytes at 0x58-0x67, then `u32 25` + `"CLO Standalone OnlineAuth"` at 0x64 | VERIFIED |
| 0x81.. | `e9 07 00 00` (2025 = product year), `u32 2`, then pairs `(offset, length)` that match **three additional embedded PNGs**: (72086, 68064), (140150, 39747), (179897, 63290), terminator 243187. First pair (368, 54927) does not match PNG #1 (261, 71825) - unresolved. | PNG #2-#4 VERIFIED by IEND/signature search (PNG signatures at 261, 72086, 140150, 179897) |
| 0xFD/0x101 | `u32 244142 = zip_off - 68` and `u32 68`. The 68 bytes right before the ZIP are a **64-hex-character digest** (`7e7d8de5...c413`) prefixed by a 4-byte length: i.e. a trailer string at 244142. Likely a content hash of the ZIP; I did not match it to MD5/SHA of any region (not tested; 64 hex = SHA-256 width). | VERIFIED layout, hash INFERENCE |

So the region between the first PNG and the ZIP that file 10 called "~172 KB not decoded" is **three more PNG thumbnails (3D-view/angle renders) plus the 64-hex digest**.

**ZIP-length field (0x24):** 266 of the 379 files have `0x24 == filesize - zip_offset`; 113 do not, and all 113 are the pipeline's `avt_patch` outputs (`clo_payload.patched.avt`, `*.patched.avt`), where the value is stale by 600-610 bytes (because `avt_patch.py` re-zips with a different deflate stream). Those same patched files were imported by CLO in production (every one has a matching `result_avatar_from_project.avt`, e.g. u_001-091) and gave a normal avatar, so **CLO does not validate the ZIP-length field** (VERIFIED by the pipeline having worked, not by a new experiment). The ZIP offset (0x20) is valid in 378 of 379 files and must be right (CLO needs it to find `PK`); the PNG offsets are likewise consistent. Whether CLO uses 0x24 at all (e.g. only for a streaming-progress bar) is unknown.

## 6. What remains unknown

- Exact meaning of the type-0x05/0x15 element codes beyond the four observed (04/05/06) and of `listMeasureMode` values 0-5.
- Joint count/names inside the `.dan` (92 inferred from GLB); location of the skeleton `m4LtoW` per joint is `mapDefaultAvatarRoot/listChildrenTransformer3D...` (not tabulated).
- Why the GLB has 606,659 vertices while the .dan has 200,134 render vertices (exporter unwelding; not derived).
- Exact skin-controller <-> render-shape mapping.
- Names of feature idx 1, 32, 33, 48, 52-54, 60-66.
- What the 64-hex trailer digest covers; first pair of the 0x89 offset table; field 0x14 purpose; the `.avs` extra bytes after the last field (none - the stream ends at the last field).
- Whether CLO applies `listFeatureValues` on `.avt` load (observed: no, mesh unchanged) - could be governed by a flag inside `mapResizingAvatar` (`bHeightLinked`, `enLastUpdateMode`); not tested.

## 7. Wider round-trip sweep (VERIFIED)

Every unique (by CRC) `.dan` (147) and `.osw` (19) member of all `.avt`/`.zprj` files under the repo parses with this grammar and re-encodes byte-identically: **147/147 `.dan`, 19/19 `.osw`, 184/184 `.avs`, 0 failures.** So the grammar above is complete for the stream container (unknown element semantics remain, but nothing is unparsable).
