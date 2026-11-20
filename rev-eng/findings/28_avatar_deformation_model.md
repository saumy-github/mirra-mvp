# Lane W: how CLO turns the 67 feature values into a deformed avatar mesh

*Status: static analysis (dumpbin) of CLO_Standalone_OnlineAuth_x64.exe 2026.1.336 plus offline reads of CLO's own Preset data files and repo avatar outputs; CLO not run*
*Date: 2026-10-29*
*Tags: **[V]** read directly (disassembly / file bytes / computed), **[I]** inference. RVAs relative to image base 0x140000000.*
*Scripts: `scripts/disasm_fn8.py` (copy of disasm_fn.py, cache `raw/disasm8/`), `w_bigleaves.py`, `w_leafagg.py`, `w_allnames.py` (what arrays the .dan holds), `w_feats.py`, `w_extract.py`, `w_fit.py` (linearity test), `w_hdr.py`, `w_pca_reg.py`, `w_pca_layout.py` (Preset data files). Raw: `raw/w_fn_*.txt` (listings), `raw/w_leafagg_base1.txt`, `raw/w_allnames_base1.txt`, `raw/w_fit_out.txt`, `raw/w_pca_reg_out.txt`, `raw/w_positions.pkl`.*

## 0. Answer in five lines

1. The deformation basis is **not in the .dan**. It is a **statistical body model (PCA, 100 components) stored as plain binary files under `C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing\{Male,Female,Boy,Girl,PreSchool}\`**, loaded by the global size manager. [V file bytes + V loader strings]
2. The 67 (58 used by the model) feature values are the user-facing controls; the size manager solves for PCA coefficients that reproduce them (regression on a 1882-subject table plus an iterative optimisation), producing a vector of new base-mesh vertex positions that is then **transferred onto the avatar's own meshes** (skin meshes of the .dan) by `Avatar::0x50a0f70` -> `0x513f190`. [V call chain, I for the solver internals]
3. The .dan holds only the result (baPosition/baInitPosition/skin weights); no morph targets, no blend shapes, no regression matrices (`listMorphTarget` is present but empty). [V]
4. Over the heights actually tested (137 - 188 cm, with the other 5 inputs co-varying) the position delta is **close to linear in total height** (in-sample rms ~1.0 mm, max 4 mm, leave-one-out rms 0.9 - 2.7 mm, against displacements of up to 522 mm), and CLO is deterministic to 0.001 mm. [V computed, n = 5 distinct samples only]
5. Exact offline re-implementation is **not** feasible cheaply (needs the unseen solver); patching .dan positions offline is feasible only as an **interpolation between CLO-generated anchors** (verdict section 6).

## 1. Call structure (first and second level)

| Function | RVA | Role | Evidence |
|---|---|---|---|
| resize driver | 0x511a1b0 | gate on avatar+0x990, loops `SetFeatureValue`, `0x51449e0` x2, then `Avatar::0x50a0f70` | finding 19 [V] |
| `SetFeatureValue` | 0x512d3a0 (31 instr) | per-feature clamp + store; calls `0x50d8a30` and the small helper `0x516bcf0`; consts at .rdata 0x82703d8, 0x8270478, 0x846c880 | raw/w_fn_512d3a0.txt [V] |
| helper `0x516bcf0` | 0x516bcf0 (only ~10 instr; my disassembler listing runs on into the next functions, so "6449 instr" is an artefact) | `f(v, mode)`: if `(mode & ~3)==0 && mode != 2` it replaces `xmm1` by a constant from .rdata 0x82703e8 and tail-jumps to a float routine at 0x470DEBE2, else returns v; i.e. a **scalar per-feature adjustment, not a deformation kernel** | w_fn_516bcf0.txt first 12 lines [V], semantics [I] |
| size manager recompute | 0x51449e0 (878 instr) | the solver. Works on the **global size manager** (ctor 0x508dcb0, 0x86B80 bytes): reads `mgr+0x18` (profile index), `mgr+0x28` (model pointer), copies 67 floats at `mgr+0x86860..0x8696C` (+ two smaller float blocks at +0x86904, +0x86954), calls 0x516b8f0 (model load/lookup), 0x516c0e0, 0x518f430, 0x518ed00, 0x518f9c0/0x518fa60, 0x5190a40, 0x5191630, 0x51918c0, 0x5191e10, 0x51933a0, 0x5146420; error string `fail to generate avatar` (0x89127a8) at 0x1451 45BDA | w_fn_51449e0.txt [V structure, I roles] |
| commit helper | 0x5148d70 (124 instr) | prepare/commit: 0x5193b80, 0x6822210, 0x68223d0, 0x1d33390 x2; no FP math, no strings | [V] |
| mesh apply (Avatar) | 0x50a0f70 (188 instr) | `mgr = 0x50d6060(); mgr+0x10 = avatar; sizeData = 0x50e26f0(mgr)`; if avatar+0xB88 byte != 0 (a **transfer helper object** at avatar+0xB88, result vector at avatar+0xBA8) calls `0x513c3d0` / `0x5140250(avatar+0xB88, sizeData)` to map model-vertex positions onto the avatar's own vertices; else uses sizeData directly. Then `0x513f190(avatar, positions)`, `0x51945e0(avatar)`, `0x5146a40(avatar,1)`, then refresh (`0x5ccd3a0`, etc.) | w_fn_50a0f70.txt [V] |
| `0x513f190(avatar, vector<float3>)` | 0x513f190 (414 instr) | **mesh writer, not a solver.** `0x50de2e0(avatar)` returns the list of meshes (16-byte shared_ptr entries). For each mesh: `n = 0x623eb80(mesh)` (vertex count); either (a) `0x623e220(mesh)` true: `0x624a170(mesh, avatar+0x10C4, sizeData, 0)` deforms that mesh from the size data, or (b) copy the next `n` x 12 bytes (float3) slice of the input position vector (via a parallel for-each lambda at 0x513eff0 / 0x513f0c0 through `0x70de8e6`), `0x3f6a1d0(mesh+0x240, slice)` stores it, `0x62486f0(mesh,1)` marks dirty. Afterwards `0x50a0510` (if avatar+0xC18 != +0xC20) and `0x517c330` (if `0x50f10a0`). Branch at avatar+0xC38 (a vector of 32-byte records = name + index, looked up by joint/mesh name) is the by-name variant | [V] |
| `0x51945e0(avatar)` | 0x51945e0 (241 instr) | post-process: 0x5138920, 0x510aec0, 0x510b2e0, 0x5147440 x2, 0x5153290, 0x6245d90/da0 (skin/joint refresh) [I] | [V list] |
| `0x5146a40(avatar,1)` | 0x5146a40 (642 instr) | AvatarManager-level refresh: map<K,T> lookups (`invalid map<K, T> key`), 4 floats at .rdata 0x89135d0..dc (a rect/bounds), no deformation maths [I] | [V list] |
| model loader | 0x516b8f0 (3216 instr) and the profile-path loader at 0x516eaa0.. (listing in raw/w_fn_516bcf0.txt) | strings: `Version: %d.%d`, `Left_ankle/j_l_ankle/j_l_toe/...`, `PreSchool/ Girl/ Boy/ Female/ Male/`, `BaseMesh.obj`, `BaseMesh.be`, `range_list.rlist`, `symmetry_data.sym`, `IndexSet.txt`, `nearestIndices.txt`, `foot.bry`, `ReducedVertexData.bd`, `PCA_weight.bd`, `FeatureData.bd`, `Preset/Avatar/AvatarSwitch.json`, `displacementData`, and the optimiser banners `Optimization by Joint`, `Early termination`, `Summary` | [V strings, I flow] |

Per-profile state in the manager: path strings for `ReducedVertexData.bd`, `PCA_weight.bd`, `FeatureData.bd` are stored at `mgr + profile*0x18 + {0x86638, 0x866B0, 0x86728}` (loader at 0x14516F179..F55F). Five profiles (`Male, Female, Boy, Girl, PreSchool` path prefixes). [V addresses, I that these are the 5 profiles]

## 2. The deformation basis: the Preset/Avatar/Resizing files [V]

Directory `C:\Program Files\CLO Standalone OnlineAuth\Preset\Avatar\Resizing\<Profile>\`. All binary files are little-endian `int32 rows, int32 cols` header + packed float32 (sizes check exactly).

| File (Male) | Header | Size | Meaning |
|---|---|---|---|
| `PCA_weight.bd` | 142479 x 100 | 8 + 142479*100*4 = 56,991,608 B | **PCA basis**: 100 components, each a vector of 47,493 vertices x 3. Layout is `[component][142479]`: the first run has norm 0.757, the second 0.843, dot(run0,run1) = -0.024 (near-orthonormal rows); max |entry| of comp 0 is 0.018, times coefficient std 1343 = ~25 mm per-vertex swing. |
| `ReducedVertexData.bd` | 100 x 1882 | 752,808 B | **PCA coefficients of 1882 training subjects** `[coef][subject]` |
| `FeatureData.bd` | 58 x 1882 | 436,632 B | **58 body measurements (cm) of the same 1882 subjects** `[feature][subject]`; row 0 = height (181.6, 173.6, 182.2 ...), row 1 = ~10 (cm?) |
| `BaseMesh.obj` | 48,345 v / 84,518 f | 8.8 MB | template mesh (mean shape / topology) |
| `BaseMesh.be` | first int 279,678 | 1.1 MB | edge list |
| `range_list.rlist`, `symmetry_data.sym`, `IndexSet.txt`, `nearestIndices.txt` (header `HEIGHT_Total 20`: lists of vertex indices per measurement landmark), `foot.bry` (Male/Female only) | text/binary | | measurement-loop vertex sets (so the model can *measure* a generated mesh), L/R symmetry, foot data |

Other profiles: Female 121,395 x 100 basis, 58 x 2161 features; Boy/Girl 72,363 x 100, 58 x 470/485; PreSchool 72,363 x 100, 58 x 397. [V]

So CLO's resizing is the classic "measurements -> PCA shape" statistical body model: shape = mean + sum_k c_k * B_k, with c derived from the user's measurements. [I for the formula, V for the data]

## 3. How the 67 feature values map to PCA coefficients

- The model has **58** measurement rows, the avatar stores **67** floats; the extra 9 (index 58-66: Hand, Head circumference, cup-size extension, 0.0/50.0 entries; finding 13) are not in `FeatureData.bd` and drive other parts (hand/head: files `hand data`, `head data` in the loader messages). [I]
- Test whether a single linear map `features(58) -> coefficients(100)` reproduces the 1882 training coefficients (ordinary least squares, ridge 1e-6, in-sample, `scripts/w_pca_reg.py`): R^2 per component = 0.975, 0.743, 0.805, 0.582, 0.898, 0.610, 0.068, 0.492 ... ; mean R^2 over components 20-99 = 0.24; **variance-weighted R^2 = 0.935**. [V computed]
  - Consequence: a plain linear regression gets the dominant (size) modes but misses the rest; 58 constraints cannot determine 100 coefficients, so CLO uses an additional **iterative optimisation** (banner strings `Optimization by Joint`, `Early termination`, `Summary`, "fail to generate avatar") rather than a single matrix. The regression matrix itself is **not stored** anywhere on disk; only the training table (features and coefficients) is. [V no matrix file, I that the solve is regression/nearest-neighbour + optimisation]
- The driver calls the set-values loop and `0x51449e0` **twice** (mode 1 then `enLastUpdateMode`); the second pass re-imposes the user-set values after the first pass re-derived the dependent ones (finding 19). This is consistent with an alternating "fit coefficients, re-measure, correct" loop. [I]

## 4. From model mesh to the avatar mesh

- The model mesh has 47,493 vertices (Male). The `.dan` avatar mesh has 90,634 physical vertices in the main body skin controller (`listSkinController[2]/baInitPosition` 1,087,608 B) plus 8 more controllers (hands/head/eyes etc.). baPosition lengths in floats are 14643, 14643, 271902, 107217, 894, 894, 5370, 5370, 13791, i.e. 4,881 / 4,881 / 90,634 / 35,739 / 298 / 298 / 1,790 / 1,790 / 4,597 vertices (from `w_extract.py`). So the avatar is a **different, higher-resolution mesh**, and the positions are **transferred** from the model mesh (this is the avatar+0xB88 "transfer helper" and `nearestIndices.txt` / `displacementData` / `baABGList`). [V counts, I mechanism]
- `.dan` arrays that look like the transfer data (no morph deltas): `baABGList` (3 controllers, 1,204,752 B total), `baLocalPosition` (3, 1,204,752 B), `baPossibleTri` (9, 716,320 B), `baTriangleIndexList` (3, 401,584 B), `fDemarcationLine` and `fSkinOffset` (one float per controller), `fSkinInwardOffset`. Together these are consistent with "barycentric / ABG coordinates of each avatar vertex w.r.t. the model mesh + a normal offset". [I from names and sizes; contents not decoded]
- Everything else big in the .dan is geometry, skinning or render data: `baArray` (listSource, 27 arrays, 6.4 MB), `baPositionIndex` (16, 2.1 MB), `baIndex` (9, 2.1 MB), `baPosition`/`baInitPosition` (9 each, 1.74 MB each), `baRenderToNormalIndex`/`baRenderToPhysicalPos` (9 each, 0.8 MB), `listJointWeight` with `arrJointIndex`/`arrWeight` (144,908 entries each, 12.4 MB), `baItoL` (joint matrices), `arrayIndexLength`. **No** `Morph`, `Blend`, `Delta`, `PCA`, `Regress`, `Cage`, `FFD`, `Landmark` leaf exists (full name list: `raw/w_allnames_base1.txt`, 482 distinct leaf names). The only sizing-related struct is `mapResizingAvatar` (2,787 B: `iResizingDataVersion`, `BaseFeature`, `WidthBaseFeature`, `ProportionBaseFeature`, `DetailFeature`, `fBaseFeatureBustCircum`, `listFeatureValues`, `listMeasureMode`, `enLastUpdateMode`, ...). [V]
- The skeleton/skinning follows the mesh: finding 13 shows `baItoL` and joint-related matrices also change on the .avs route (the mesh apply `0x51945e0` refreshes joints). [V from finding 13, I mechanism]

## 5. Reproducibility and linearity check on stored avatars [V computed]

Data: base-1.avt (187.96 cm) and four distinct .avs-route results (`u_001-092` 178.5, `g_e5c37...` 137.0, `u_003-004` 175.0, `u_dcabc...-009` 179.5); `u_003-005` is an exact repeat of `u_003-004`. Positions = `mapMesh/baPosition` of `listSkinController[2]` (90,634 vertices), 1 vertex in 97 sampled. Inputs vary in height (idx 0), bust (2), waist (6), low hip (8) and the 51 ridge-predicted values.

| Test | Result |
|---|---|
| Determinism: two runs with identical .avs | max |Δposition| = **0.00098 mm**, features identical (0.0) |
| Displacement from base | mean |d| 29 - 170 mm, max 88 - 522 mm per coordinate |
| Model A: `y = a + b*height` per coordinate | in-sample rms **1.03 mm**, max 4.0 mm; leave-one-out rms 0.87 / 0.89 / 1.50 / 2.44 / 2.66 mm (max 13.3 mm for the extrapolated 137 cm sample) |
| Model B: height + bust | LOO rms 0.95 - 5.1 mm (not better: bust is collinear with height in these 5 samples) |
| Model C: height + bust + waist (4 params, 4 training points) | blows up (rms up to 399 mm): under-determined, shows the data cannot separate more than ~1 axis |
| Feature response vs height: slope of other features per cm of height (`dh` fits within <= 2 cm for most) | chest 0.25, waist 0.35, hip 0.16, heights (18-25) 0.8 - 0.9, 57 = 1.0 ... |

Reading: **the map height -> vertex position is smooth and near-linear in the 137 - 188 cm span** (a tall-vs-short body mostly scales along the principal PCA directions with a linear-looking response), and CLO is numerically deterministic. But with 5 samples whose bust/waist/hip co-vary with height (ridge-predicted rest), no statement can be made about independent girth axes. A proper test needs a designed set (one input varied at a time), which can only be produced by running CLO. [limit of evidence]

Note the GLB point (memory: exported GLBs identical across users) is separate: that concerns the route that does not call 0x511a1b0.

## 6. Feasibility verdict for offline re-deformation

| Option | Verdict |
|---|---|
| A. Patch .dan `listFeatureValues` only | does nothing (findings 19) |
| B. Re-implement CLO's solver offline from the Preset files (features -> PCA coefficients -> model mesh -> transfer to avatar -> joints) | **Not feasible short-term.** Missing: the solver (0x51449e0 + 0x518ed00/0x5191e10, thousands of instructions, includes the optimisation loop), the transfer (0x5140250/0x513c3d0, mapping data in `baABGList`/`nearestIndices`), and the 9 extra features. The regression is only 93.5% variance-explained linear, so a naive reimplementation would not hit measurements exactly (in-sample R^2 for the minor components 0.07 - 0.5). Also the Preset data is licensed CLO content (redistribution concern) and the pipeline already has CLO available. |
| C. **Anchor interpolation**: pre-render N avatars with CLO via the .avs route on a design of experiments (height x bust x waist x hip, e.g. a 2-3 level grid or Latin hypercube of 15 - 30 points), store only `baPosition`/`baInitPosition`/`baItoL`/render arrays per anchor, then at request time compute a linear (or low-order polynomial / PCA-compressed) combination and **write the result directly into a template .dan**. | **Feasible and cheap, with accuracy ~1 - 3 mm on the height axis (measured), unverified on the girth axes.** Because topology, UV, weights are identical across sizes (finding 13: 0 bytes diff outside position-like arrays), only position arrays need to be patched (listSource[0] positions, normals listSource[1] derived, baPosition, baInitPosition, render positions, `baItoL`/joint matrices, `m4LtoW`). CLO would still compute the true skeleton on import, but the .avt/.dan route does NOT re-run the driver (finding 19), so every changed array must be consistent by construction. Needs: a verification that CLO accepts an edited .dan (lane F found stored arrays are loaded as saved, so it should), and checking the normals/bounds. |
| D. Bypass CLO sizing for garment fitting entirely (use a PCA body model of our own) | possible in principle (the same statistical-model idea), but outside this lane and would not match CLO's avatar for try-on. |

Recommendation: keep the `.avs` route (which runs the true solver) for exact results; if per-request latency or CLO licence usage is a problem, build option C from a CLO-generated anchor set; do not try to port the solver. Open items below would raise confidence.

## 7. Open items / not done

- `0x51449e0` internals (878 instr) and its children `0x518ed00` (2,975 instr; joint `updateDataType`, eye joints), `0x5191e10` (3,269 instr; ankle/foot handling), `0x5190a40`, `0x5146420` were only classified by call/string/FP-op counts, not read. The exact mapping features -> coefficients (regression vs nearest-neighbour vs optimisation) is [I].
- `PCA_weight.bd` is `[component][dim]` by near-orthogonality only; the mean shape is assumed to be `BaseMesh.obj` (48,345 vertices vs 47,493 in the PCA dimension: `ReducedVertexData`'s "reduced" vertex subset index is probably `IndexSet.txt`/`nearestIndices.txt`; not verified).
- The linear test used 5 distinct samples (4 free inputs but strongly correlated); girth-only variation, cross terms and the female model were not tested. A designed experiment needs CLO runs (not done).
- The transfer helper object at avatar+0xB88 (0x513c3d0, 0x5140250) and what `baABGList` holds were not decoded.
- Whether feature indices 58-66 use separate head/hand models (loader mentions `hand data`, `head data`) not checked.
