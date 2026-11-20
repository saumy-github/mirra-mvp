# 25 - GLB exporter vertex rule (lane T)

*Status: static + data analysis, 2026-10-29. Disassembly of 0x60a5090 not extended (time limit); rule derived from GLB data vs .dan.*

## Result: the 606,659 figure is a counting artefact, not vertex expansion
[V] The exporter does NOT unweld per triangle. The GLB has 16 primitives in 9 meshes, and **primitives of the same mesh share one set of vertex accessors** (POSITION/NORMAL/UV/JOINTS/WEIGHTS), each primitive only has its own index accessor. `glb_probe.py` sums POSITION.count per primitive, so a mesh with 4 primitives is counted 4 times.
- Distinct POSITION accessors = 9; their counts sum to **200,134 = exactly the .dan render-vertex total** (finding 13). Ratio 1.000, not 3.03.
- Per mesh: shoes_r 5,885 (2 prims), shoes_l 5,885 (2), Hair 141,426 (3), body 37,301 (4), eye_L/R 298, eyelash_L/R 1,790, tooth 5,461 -> .dan shape vertex counts match one-to-one. [V]
- Overcount: 606,659 = 2x5,885x2 + 141,426x3 + 37,301x4 + 298x2 + 1,790x2 + 5,461 (check: 23,540 + 424,278 + 149,204 + 596 + 3,580 + 5,461 = 606,659). [V]
- Triangles 179,080 are unaffected (index accessors are per primitive). The "3.03 ratio" and the 537,240 (tris x 3) hypothesis are both wrong; 606,659 only coincidentally sits near 3x. [V]
- Correction to findings/13 and FINDINGS.md lane F ("exporter expands vertices, rule unknown"): there is no expansion. Also lane C's "606,659 vertices" should read "200,134 distinct vertices (606,659 summed per primitive)".

## Vertex identity rule (what a render vertex is)
Measured on `output/u_001-065/result_avatar.glb` (text glTF + .bin, generator "CLO Standalone OnlineAuth 2026.1.188"; the Aug-20 copy in g_241f... has identical bin hash 3dd45a78cb):
| mesh | GLB verts | unique positions | unique (pos,normal) | unique (pos,uv) |
|---|---|---|---|---|
| shoe (each) | 5,885 | 4,881 | 4,881 | 5,452 |
| Hair | 141,426 | 90,634 | 90,634 | 90,682 |
| body | 37,301 | 35,739 | 35,739 | 37,301 |
| eye/eyelash/tooth | 298 / 1,790 / 5,461 | = verts (tooth 4,590) | tooth 4,597 | 5,461 |
[V] Unique positions per mesh equal the .dan skin-controller physical vertex counts (4,881 / 90,634 / 35,739 / 298 / 1,790 / 4,597). So the rule is: **1 glTF vertex = 1 CLO render vertex = (physical vertex, UV) pair**; a physical vertex is duplicated only where the UV differs (seams). Normals are per physical vertex (unique(pos,n) == unique pos), i.e. smooth, no hard-edge splitting. Duplication overall: 200,134 / 144,908 physical = 1.38x, almost all from Hair (+50,792) and body UV seams (+1,562). [V]
- Hair is the outlier: 141,426 render vs 90,634 physical, but unique (pos,uv) is only 90,682, so ~50,700 hair vertices are exact duplicates (same pos, same normal, same UV) that a weld would merge. [V]

## Flags
- ImportExportOption `weldType` default is FULLY_UNWELDED (0), and the plugin only sets `scale=0.001, bExportGarment, bExportAvatar` for export (finding 08). Yet the output is not triangle-unwelded, so for the avatar mesh `weldType` has no visible effect or is ignored by the glTF writer. [I] (not tested: no CLO run allowed; changing it is the first experiment). Hair duplicates and the tooth/shoe duplicates are weldable candidates under FULLY_WELDED (2). [I]
- `scale` 0.001 gives metres (verified earlier: heights 1.4-1.9 m). `bThin` (default true) affects cloth thickness, not avatar vertex count. [I]
- `bExportAvatar=false`/`bExportGarment=false` and the four component lists (pattern 0xC8, button 0xE0, graphic 0xF8, zipper 0x110 per worker 0x60a5090) select what is exported; empty lists = whole scene via App->[0x38] vtbl[0x98]. [V from finding 11]. The avatar itself is not a component-list item; only the avatar flag controls it. [I]
- Other options relevant to size: `bEmbedded` (images in glb), `bSaveInZip`, `bSaveColorWays` (+`bSaveColorWaysSingleFile` -> KHR_materials_variants), `bExportFabric`, `bExportLight`. [I]
- Extension KHR_materials_specular is used (16 materials, 26 images). Option-name strings for ThinMesh/Weld were not found in exe strings; the option names are SDK-header fields, not exe strings. [V that grep found none]

## Where the bytes are (13,409,456 B .bin) [V]
Distinct attribute data: POSITION 2.40 MB, NORMAL 2.40 MB, TEXCOORD_0 1.60 MB, JOINTS_0 (u16x4) 1.60 MB, WEIGHTS_0 (f32x4) 3.20 MB = 11.2 MB; indices (u32, 179,080 tris) 2.15 MB. Skinning (JOINTS+WEIGHTS) = 4.8 MB (36%). Packed GLB = 30.52 MB: 17.1 MB is 26 embedded images. Hair is 70.7% of all vertices (141,426 / 200,134).

## What Mirra could do to shrink it
1. Drop Hair from the avatar scene before export (or export hair-free avatar): -141,426 vertices (-71%), ~ -9 MB of attributes. [I] Needs a CLO-side hide/delete; `bIncludeHiddenObject=false` default suggests hidden objects are skipped, so hiding the hair shape before export may suffice. [I, untested]
2. Try `weldType=2` (FULLY_WELDED) in the plugin's export options: should merge Hair exact duplicates (~50.7k) and UV-seam copies if the writer honours it. Untested; verify by recounting distinct POSITION accessors. [I]
3. Post-process the GLB offline (stdlib): dedupe identical (pos,normal,uv,joints,weights) tuples, convert indices to u16 per primitive where <65,536 (all non-hair meshes, shoes, eyes...), WEIGHTS_0 f32 -> u8 normalized (KHR_mesh_quantization-free option: u8 normalized weights are valid core glTF), drop eyelashes/teeth if unseen. Estimated: weights 3.2 -> 0.8 MB, indices ~ -1 MB. [I]
4. Skin-free export: no option found to omit skin (skins are present because CLO exports the avatar with its 92-joint skeleton, 9 skins); for garment-only GLB use `bExportAvatar=false` and the component lists for one file per garment. [I]
5. Prefer `.glb` with `bEmbedded` off? Textures (17 MB) dominate packed size; avatar textures could be stripped/recompressed offline. [I]
6. Scene with N avatars exports N copies (lane C); keep exactly one avatar loaded (DeleteAvatar/NewProject between runs). [V from lane C]

## Reproduce
`python -I rev-eng/scripts/glb_dups.py <glb>` (new, per-primitive unique position/normal/uv counts). Distinct-accessor sum: collect set of `POSITION` accessor indices over all primitives.
