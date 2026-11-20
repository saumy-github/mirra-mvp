# Avatar-related file formats (lane C)

*Status: done (static analysis of files on disk; CLO not run)*
*Date: 2026-10-29*
*Scripts: `scripts/avt_probe.py` (info / diff / strings), `scripts/glb_probe.py` (info / summary / diff). Raw: `raw/glb_summary.tsv` (all 61 GLB-ish files in `clo_avatar_generation/output`).*

All offsets are decimal unless prefixed `0x`; all integers little-endian.

## 1. Summary table

| Ext | Container | Magic / first bytes | Compression | Who writes it |
|---|---|---|---|---|
| `.avt` (avatar) | custom CLO header + **ZIP** appended | `20 41 56 54 20x8 43 4C 4F 20` = `" AVT        CLO "` | ZIP deflate (method 8) | CLO (`ExportZPrj` member, `ExportAVT`), also our `avt_patch.py` re-zips |
| `.zprj` (project) | same CLO header + ZIP | `" ZPRJ       CLO "` | ZIP deflate | `ExportZPrj` |
| `.avs` (avatar size) | bare typed property stream, **no** zip, no magic | `03 0A 0E 0D 0F 0F 16 13 ...` | none | CLO (GUI "Save Avatar Size"); our `avs_patch.py` patches a template |
| `.dan` (inside .avt) | typed property stream, same family as .avs/.osw | `3D 0A 0E 11 09 ...` | none (deflated by the ZIP) | CLO |
| `.glb` as written by plugin (Aug 2026, CLO 2026.0.374) | **text glTF JSON** (not a GLB!) + external `.bin` | `{\r\n  "accessors"` | none | `ExportGLB` (misnamed) |
| `.glb` as written by plugin (Oct 2026, CLO 2026.1.224) | true binary GLB v2 | `glTF 02 00 00 00` | none (images embedded as bufferViews) | `ExportGLB` |

## 2. `.avt` / `.zprj` outer container

The ZIP does not start at 0: a variable-length CLO header precedes it. Our code finds it via `raw.find(b"PK\x03\x04")`; the header itself also stores the offset.

Header layout (verified on `input/base-1.avt`, `u_001-012/result_avatar.avt`, `Preset/Avatar/Converting/Male/Genesis8_Male.avt`, `.zprj` files):

| Offset | Size | Value in `base-1.avt` | Meaning |
|---|---|---|---|
| 0x00 | 16 | `" AVT        CLO "` (or `" ZPRJ       CLO "`) | magic: 4-char type padded with spaces to 12, then `"CLO "` |
| 0x10 | u32 | 12 (Genesis8 preset: 11; Untitled.Zprj: 3) | format version (rises with CLO release) |
| 0x14 | u32 | 237 (zprj: 218) | unresolved; equals offset of the 19-byte template-name field minus a few bytes (0xED); not decoded |
| 0x18 | u32 | 261 (zprj: 242) | **offset of embedded PNG thumbnail** (PNG signature found at exactly this offset in all files) |
| 0x1C | u32 | 71825 | **PNG length** (PNG IEND ends at 261+71825 = 72086; verified) |
| 0x20 | u32 | 244210 | **offset of ZIP** (equals `find(PK\x03\x04)`; verified for every file tested) |
| 0x24 | u32 | 33683366 | **ZIP length** = file size - ZIP offset (33927576 - 244210; verified; also on zprj: 36218919-76405 = 36142514) |
| 0x28 | u64 | 1774958706515 | Unix time in **milliseconds** (2026-03-31 12:05:06.515 UTC for base-1.avt; re-saves update it, e.g. u_001-012 export: 2026-04-07 12:40:09.863). Written twice (0x28 and 0x34). |
| 0x30 | u32 | 413 | unresolved (417 in a later build, 346 in preset zprj): looks like build number |
| 0x34 | u64 | same ms timestamp again | second timestamp (created/modified; always equal here) |
| 0x3C | u32 | 2010 (preset: 2008) | unresolved, repeated with the 413 field; probably file-format year/revision |
| 0x40 | u32 + bytes | `14 00 00 00` + `ce79e2364d4404e9798a` | length-prefixed string: an id (20 chars). Same id `ce79e2364d4404e9798a` for every file derived from `base-1.avt`; Genesis8 preset has `callumlee` (author). |
| 0x5C | u32 + bytes | 25 + `CLO Standalone OnlineAuth` | length-prefixed product string |
| 0x7D... | | `e9 07 00 00` (2025), `02 00 00 00`, then a table of ~11 u32 sizes | not decoded (looks like per-resource size/offset table) |
| 0xE6 | u32 + bytes | 19 + `5.1_MaleTemplate_07` | avatar template/preset name |
| 0x101 | u32 | 244142 | unresolved; 244210 - 244142 = 68 (the 0x44 that follows) |
| 0x105 | | `89 50 4E 47` | PNG thumbnail (512x512 RGBA, IHDR at 0x10D) |
| after PNG..zip start | ~172 KB | | more header material, not decoded (the 0x20 offset skips it) |

Notes
- `avt_patch.py` keeps the prefix verbatim and rewrites only the ZIP. Consequence: patched files keep the base file's timestamp (0x28) and the prefix length stays 244210 (confirmed: `clo_payload.patched.avt` prefix is byte-identical to `base-1.avt`), while ZIP-length field 0x24 is now stale by ~600 bytes. CLO loads such files fine, so it does not validate 0x24 (or the plugin import path tolerates it). Unverified whether any consumer checks it.
- Header values in `result_avatar_from_project.avt` from the pipeline's later runs: thumbnail length 74976 / 87593 (different thumbnails), prefix 254842 / 302201.

### 2.1 `.avt` ZIP members (base-1.avt: 28 members)

| Member | Role | Notes |
|---|---|---|
| `first.dan` (name varies: `result_avatar.dan`, `genesis_8_male_daz.dan`) | avatar data stream (mesh, skeleton, skin weights, size/feature floats) | 33,066,665 B uncompressed / 11.46 MB deflated for the base male |
| `*.jpg`, `*.png` (26 of them) | avatar textures (MV2_Jinho_01_* body/face/leg/arm/eye/tooth, hair, sneaker, `transparency_*.png`) | byte-identical across all derived avatars (diffs: "same") |
| `clofiles.json` | map filename -> absolute path of texture in CLO's temp cache (`C:/Users/Saumy/AppData/Local/CLO Virtual Fashion/CLO Standalone OnlineAuth/<n>/<n>/...`) | 4187 B in base-1; differs per export only in cache-dir numbers |

Genesis8 preset avatars (`Preset/Avatar/Converting/{Male,Female}/Genesis{8,9}_*.avt`, 1.2 MB each) are the same container, version 11, with one `.dan` (3.5 MB) and no textures; they have **no** `listFeatureValues` marker (they are converting skeletons, not size-driven avatars).

### 2.2 `.zprj` ZIP members (from `u_001-092/result_project.zprj`)

`img_3dwindow_bg_Modelist.png`, `<name>.osw` (scene objects; binary typed stream, references `listAvatarFilePath` -> `result_project_0.avt`), `<name>.xml` (Environment 6.0, plain XML), `.cmt`, `.cmp`, `.cpt`, **`<name>_0.avt` (the full avatar, byte-identical to `result_avatar_from_project.avt`; verified `m == f` on u_001-092, 34,313,119 B)**, `.smp`, `.vmp`, `.vlp`, `.vrp`, `displaysettings.json`, `snapshotoptionsettings.json`, `fitmapsettings.json`, `clofiles.json`. So the pipeline's `result_avatar_from_project.avt` is just the `_0.avt` member unzipped; the AVT inside a project is a complete `.avt` including the CLO header.

## 3. The feature-float block (where measurements live)

- Both `.avt` (inside the `.dan`) and `.avs` contain the ASCII key `listFeatureValues` followed by 57 float32 values (cm, little-endian), index 0 = Total Height.
- In `.dan`: floats start at `marker_offset + len("listFeatureValues") + 273`. For `base-1.avt` that is **absolute .dan offset 33,021,814** (the block is near the end of the 33 MB stream; same offset in every base-derived `first.dan`/`result_avatar.dan` since upstream data length is constant). Verified: patch of 6 floats changes exactly those bytes (18 differing bytes, 3 per float since the exponent byte often matches).
- In `.avs` (2486 B): marker at 1448, floats at **file offset 1718** (= 1448 + 17 + 253; located heuristically by `avs_patch.py` by scanning for height in 100..250 followed by a plausible second value), 57 floats end at 1946. Before it: `u32 0x3e` + typed array; marker `listMeasureLinkList` at 1966 follows.
- Values in `base-1.avt` (default male template): idx0 Total Height 187.96, idx1 70.0, idx2 Chest 96.52, idx6 Waist 82.55, idx8 Low Hip 95.25, idx26 Inseam 86.36, idx36 Across Shoulder (Curvilinear) 44.13. Identical to the `.avs` template (`CLO_Male_Default.avs`) for all 57 (differences only in the 4th decimal for idx 39, 41, 56-57 due to float rounding of my display).
- `clo_payload.avt_patch.json` maps field names to indexes (Total Height 0, Chest 2, Waist 6, Low Hip 8, Inseam 26, Across Shoulder 36).
- Floats are plain IEEE-754; no checksum covers them inside the .dan (the ZIP CRC is recomputed by `zipfile`).

### 3.1 Observed effect of writing the floats vs what CLO then does

| Source | Total Height (0) | Chest (2) | Waist (6) | Notes |
|---|---|---|---|---|
| base-1.avt | 187.96 | 96.52 | 82.55 | template |
| patched (u_001-012; request 178.5/100/85/98/90/45) | 178.5 | 100.0 | 85.0 | only the 6 requested floats differ from base: `diff` shows 6 changed features; all other .dan bytes and all other zip members "same" |
| after CLO load + `result_avatar.avt` export | 178.5 | 100.0 | 85.0 | **other 51 floats change** (e.g. idx1 stays 70.0 but idx3 37.552->36.923): CLO recomputes derived floats on load, and `.dan` length shrinks by 64 B |
| AVS route (u_001-092, 178.5): from_project.avt | 178.5 | 100.0 | 85.0 | derived floats also recomputed |
| AVS route (g_e5c..., 137.0, chest 81.5) | 137.0 | 81.5 | 62.0 | likewise |

## 4. `.avs` / `.dan` / `.osw` stream grammar (partial)

Observed structure of `CLO_Male_Default.avs` (2486 B): a prefix of one byte per field (`03 0A 0E 0D 0F 0F 16 13`, 8 bytes; `.osw` starts `17 12 09 0C 13 15 ...`, `.dan` starts `3D 0A 0E 11 ...`), then records `[u32 len][ASCII key]` style data such as `qsAvatarID` -> `5.1_MaleTemplate_07`, `qsAvatarIDUTF8`, `MVresizingMap`, `bWidthLinked`, `DetailFeature`, `bUseProportionBase`, `bHeightLinked`, `WidthBaseFeature`, `listMeasureMode` (u32 count 0x3e=62 + 62 one-byte/u32 mode entries), `ProportionBaseFeature`, `listMeasureDiffValues` (0x3e entries), `bUseCFNeckToWaist`, `bUseCBNeckToWaist`, `bUseTotalRise`, `enLastUpdateMode`, `listFeatureValues`, `listMeasureLinkList`. Key prefixes follow a Hungarian convention (`qs` QString, `b` bool, `i`/`ui` int, `v2/v3/m4` vec/matrix, `list`, `map`, `en` enum). The leading per-field byte list looks like a type-code table (values 0x01..0x1D) for the following fields; I did not fully decode it (unverified).
The `.dan` for the base male contains 942 distinct identifier-like tokens (joint names `Right_thigh`, `Spine1`, `jaw`, `Left_eye`, ...; `mapGlueData`, `m4LtoW`, `bVisible`, `qsClosetId`...), i.e. the same serialisation used for garment/project data in CLO.

## 5. GLB / glTF exports

Two distinct on-disk shapes (check with `scripts/glb_probe.py info`):

| Shape | Files | Structure |
|---|---|---|
| A. text glTF named `.glb` + `result_avatar.bin` | Aug 2026 runs (e.g. `u_001-062`, `g_241f...`), generator `CLO Standalone OnlineAuth 2026.0.374`, JSON 81,257-81,325 B (CRLF, 2-space pretty-printed), BIN 13,409,456 B, images referenced by `uri` (jpg/png files next to it) | not loadable as GLB by other tools (first bytes `{\r\n`); the repo's `step_12_export_glb.py` repacks it into `result_avatar_packed.glb` (30.5 MB, true GLB) |
| B. true binary GLB | Oct 2026 runs (e.g. `g_e5c3...`, `u_001-092`), generator `CLO Standalone OnlineAuth 2026.1.224`; 39,648,436-39,648,556 B | header `glTF`, version 2, total length; chunk 0 `JSON` at 20 (44,272 B in g_e5c...), chunk 1 `BIN\0` at 44,300 (39,604,256 B). 96 bufferViews (70 geometry + 26 images embedded) vs 70 in shape A |

glTF content (identical in both shapes):

| Item | Value |
|---|---|
| asset | `{"generator": "CLO Standalone OnlineAuth 2026.x", "version": "2.0"}`; no `extras`, no node/scene `extras` anywhere |
| extensionsUsed | `["KHR_materials_specular"]`; none required |
| scenes / nodes | 1 scene, 113 nodes (skeleton joints + 9 mesh nodes) |
| meshes (9) | `shoes_r_Shape`(2 prims), `shoes_l_Shape`(2), `Hair`(3), `body`(4), `eye_L`, `eye_R`, `eyelash_L`, `eyelash_R`, `tooth_` (1 each) |
| attributes per primitive | `POSITION, NORMAL, TEXCOORD_0, JOINTS_0, WEIGHTS_0` (all skinned) |
| skins | 9, each 92 joints, `skeleton` = node 3 |
| vertices / triangles | 606,659 / 179,080 for a single avatar (all 70 accessors) |
| materials / textures / images | 16 / 26 / 26 (PBR metallic-roughness; KHR_materials_specular; baseColor + metallicRoughness textures; normal maps present as textures) |
| animations / cameras | none |
| units | metres (plugin sets `scale = 0.001` on export since CLO uses mm) |
| POSITION bounds (default male, avt route) | Y 0.0 .. 1.9213 (shape A, Aug), -0.0135 .. 1.9078 (shape B + avt route) |

Quirk (important): if the CLO scene already holds N avatars when exporting, the single GLB contains N copies of the geometry (BIN = N x 13,409,456; verified for N = 1, 2, 3, 4: sizes 13,409,456 / 26,818,912 / 40,228,368 / 53,637,824; vertices 606,659 / 1,213,318 / 1,819,977 / 2,426,636). Seen on `u_012-002/003`, `u_013-002`, `u_001-071`, `u_011-003/4`, `u_dcabc...-008` (65.9 MB shape B, 1,213,318 verts).

## 6. Do GLBs differ between users? (verifies the project memory, with a refinement)

Hash facts (`raw/glb_summary.tsv`, sha256 of BIN chunk, first 10 hex):

**avt_patch route (patched floats applied to base-1.avt then imported): geometry does NOT depend on measurements. Memory confirmed.**
- Aug-8/9 pair `g_241f...` vs `g_4e1a...` (both height 175, chest 100, so not independent users): `result_avatar.bin` sha256 identical (`3dd45a78...`), `clo_payload.patched.avt` identical (`914ef070...`, 33,926,967 B), the two packed GLBs differ in **50 bytes** (`cmp -l`; JSON material-id suffix numbers, no geometry), `result_avatar_from_project.avt` differ (different timestamps/thumbnail).
- 15+ runs across users u_001, u_011, u_012, u_013, u_014, u_015 with heights 168 / 178.5 / 181 etc. produce only **two** distinct BIN hashes: `3dd45a78cb` (CLO 2026.0.374, Aug 8) and `6a8aabbfee` (Aug 20+); every shape-A single-avatar file after Aug 20 shares `6a8aabbfee`.
- Shape-B GLBs from the avt route: `u_001-081`, `u_001-091` (178.5), `u_011-006` (168), `u_012-006`, `u_013-006`, `u_013-007` (181), `u_014-006`, `u_015-006` all share BIN hash **`ef5ab2c9aa`**, identical Y max 1.9078 m regardless of requested height.
- But the `.avt` exported back from CLO does carry the patched floats (feature[0] = 178.5 in `u_001-092/result_avatar_from_project.avt`). I.e. the number is stored but the mesh is not re-deformed.

**avs route (`.avs` applied via `ImportFile`): geometry DOES change.**

| Run | apply mode | requested height (cm) | BIN sha (10) | Y max (m) | Y max / height |
|---|---|---|---|---|---|
| default male template | n/a | 187.96 (template) | ef5ab2c9aa | 1.9078 | 1.0150 |
| u_001-092 | avs | 178.5 | 8b71b22fb1 | 1.8137 | 1.0160 |
| u_003-004 | avs | 175.0 | a673daebf5 | 1.7786 | 1.0164 |
| u_003-005 | avs | 175.0 | 51beae98c3 | 1.7786 | 1.0164 |
| u_dcabc...-009 | avs | 179.5 | 52eaa62e92 | 1.8237 | 1.0160 |
| g_e5c37ff7a450d060 | avs | 137.0 | 0c65ffb6d6 | 1.4002 | 1.0221 |

(Y max includes hair/shoe geometry above/below the measured stature, hence the ~1.5-2% offset.) Hash of the two identical-input runs u_003-004/005 differ although Y max and X span match: some BIN bytes are not deterministic across runs (not investigated further; vertex positions vs weights unverified).
Conclusion: the memory note ("exported GLBs identical across users, only .avt floats differ") is correct for the `avt_patch` route and incorrect for the `avs` route on CLO 2026.1.224, where the mesh scales (height, widths) with the 57 feature floats. The JSON part of the GLB differs between runs only in material-name numeric suffixes (e.g. `Material_RightShoe_2451` vs `_13994`: CLO's internal object ids, monotonic with session age) and POSITION accessor min/max.

## 7. API -> format cross-reference (plugin `RestPlugin_windows.cpp`, `findings/02_header_signatures.md`)

| API call | Reads | Writes | Plugin call site / REST route | Notes |
|---|---|---|---|---|
| `ImportAPI::ImportAvatar(avtPath, opt)` | `.avt` | scene (avatar) | line 1761, `POST /import-avatar-avt` (default `method:"import_avatar"`) | `ImportExportOption`: scale, ImportObjectType, bAdd, bAutoTranslate, bSizeAndPoseFromAvatar, bIncludeAvatarShape, bIncludeSkeleton... |
| `ImportAPI::ImportFile(path)` / `(path, opt)` | zprj, zpac, **avt**, obj, fbx, zcmr, gltf; `.avs` (our use, `method:"import_file"`) | scene | lines 1757/1759; avs path in `step_08_apply_measurements._apply_via_avs` | header says "shows a dialog per file type" (the project's .avs TODO is to remove the pop-up) |
| `ImportAPI::ImportAvatarMeasurement(csv, avt, opt)` | measurement `.csv` + `.avt` | scene (resized avatar) | line 1782, `POST /import-avatar-measurements` when param2 (avt) given | CSV schema in `clo_avatar_generation/schema/measurement_csv_schema.md` |
| `ImportAPI::ImportMeasurement(csv)` | `.csv` | scene | line ~1785 (else branch) | |
| `UtilityAPI::SetAvatarProperties(idx, map<string,string>)` / `GetAvatarProperties(idx)` | in-memory CLO avatar state (string map; e.g. `KineticFriction`, `SkinOffsetMM`, `Total Height`) | in-memory CLO avatar | lines 1809-1816; experimental `avatar-set-properties` | no file format; values do not touch the `.dan` until a save/export; GetAvatarProperties on empty scene crashed CLO (2026-08-22 per code comment) |
| `ExportAPI::ExportAVT(path)` | in-memory avatar | `.avt` (same container as in section 2) | lines 615-626, `POST /export-avatar-avt`; wrapped in SEH; `has_avatar_avt_export` false until probed | known to raise SEH exceptions |
| `ExportAPI::ExportZPrj(path, thumb)` | scene | `.zprj` (contains `<name>_0.avt` member) | line 2129 `save-project` | the pipeline's `result_avatar_from_project.avt` is extracted from this |
| `ExportAPI::ExportGLB(path, opt)` | scene | Aug builds: text glTF + `.bin` + textures; 2026.1.224: real GLB | line 1943 (`/export` with format glb) | options: `scale=0.001f`, `bExportAvatar=true`, `bExportGarment = patterns loaded` |
| `ExportAPI::ExportGLTF(path, opt, bGLBinary=false)` | scene | `.gltf` + `.bin` | line 1944 | |

In the current pipeline: avt route = (patch `.avt` floats -> `ImportAvatar`), avs route = (`ImportAvatar(base .avt)` then `ImportFile(.avs)`), both end with `ExportZPrj` (-> `_0.avt`) and `ExportGLB` (-> shape B in Oct builds).

## 8. Unverified / open

- Header fields at 0x14, 0x30, 0x3C, the table after the product string and the 0x101 value; meaning of the ~172 KB between PNG end and ZIP start.
- Whether CLO validates ZIP-length (0x24) and PNG fields: patched files with stale 0x24 load, so apparently not strictly.
- Whether the typed-stream prefix really is a type-code table; no full `.dan` schema (mesh vertex layout, skin weights) was decoded.
- Cause of BIN hash differences between two avs runs with identical inputs (u_003-004 vs 005).
- How the non-height floats in the avs route are regenerated by CLO (we only know the output changes; `avs_derived_model.json` approximates it).
- Genesis9/female presets were only header-checked (Genesis8 male fully listed).
