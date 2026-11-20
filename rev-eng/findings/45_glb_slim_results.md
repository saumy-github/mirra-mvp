# 45 - glb_slim.py results (lane AU)

*Status: tool written and tested offline, 2026-10-29. No CLO run. Tool: `scripts/glb_slim.py` (stdlib only, run with `python -I`). Test outputs: `out/glb_slim/*.glb`.*

## Caveat
No external glTF validator (gltf-validator, Khronos) was available, and nothing was installed. Validity of every output was checked **only with glb_slim.py's own validator** (accessor bounds, index range, 4-byte alignment of bufferViews and accessors, bufferView within buffer, skin joint nodes exist, JOINTS index < skin joint count, all attribute counts == POSITION count, JOINTS/WEIGHTS set counts equal, weight sum within 1e-3, triangle index count % 3). A viewer load test (three.js, Blender, CLO import) was NOT done. Treat outputs as "self-consistent", not "certified".

## Tool summary
`python -I scripts/glb_slim.py IN [-o OUT.glb] [--drop-mesh Hair,shoes_r,shoes_l] [--weld] [--u16-indices] [--weights-u8] [--joints-u8] [--recompress-images] [--report]`
- Input: binary GLB, or CLO text glTF + external `.bin` + external jpg/png. Output: always a single binary GLB; external images are embedded as bufferViews; BIN is rebuilt from scratch (garbage collected, compacted, every bufferView 4-aligned, one tightly packed bufferView per accessor).
- `--drop-mesh`: name match is exact or `NAME_*` prefix (CLO names are `shoes_r_Shape`, `shoes_l_Shape`, `Hair`). Removes mesh, its now-empty node, unused skins, materials, textures, samplers, images, accessors, bufferViews.
- `--weld`: merges vertices whose bytes are identical across ALL attributes of a primitive group (primitives sharing one attribute set are welded together, indices remapped). Skipped if morph targets exist.
- `--u16-indices`: uint16 when vertex count < 65535 (65535 is the restart value). `--weights-u8`: normalised UNSIGNED_BYTE, per-vertex sum exactly 255 (largest-remainder rounding). `--joints-u8`: only if all joint indices < 256.
- `--recompress-images`: **skipped**, stdlib cannot re-encode JPEG/PNG; the flag only prints image sizes (26 images, 12,797,751 B total in the text-glTF sample, ~half the file).
- Does not touch normals/UV precision, no quantisation of POSITION/NORMAL/UV (KHR_mesh_quantization would be needed; not implemented).

## Inputs
- A: `clo_avatar_generation/output/u_001-065/result_avatar.glb` (text glTF 81,257 B + `result_avatar.bin` 13,409,456 B + 26 image files 12,797,751 B). Whole payload = **26,288,464 B**.
- B: `clo_avatar_generation/output/g_e5c37ff7a450d060-001/result_avatar.glb` (binary GLB, **39,648,556 B**, images embedded).
Both: 9 meshes, 200,134 distinct vertices, 179,080 triangles.

## Sizes (bytes). "all" = drop Hair,shoes_r,shoes_l + weld + u16 + weights-u8 + joints-u8
| Operation | A out | A vs payload | B out | B vs input |
|---|---|---|---|---|
| none (repack only: single GLB, GC, align) | 26,252,360 | -0.1% | 39,649,536 | +0.0% (B had 18 unaligned image views, now aligned) |
| --weld | 23,362,164 | -11.1% | 36,759,340 | -7.3% |
| --u16-indices | 25,629,388 | -2.5% | 39,026,564 | -1.6% |
| --weights-u8 | 23,850,904 | -9.3% | 37,248,080 | -6.1% |
| --joints-u8 | 25,451,820 | -3.2% | 38,848,996 | -2.0% |
| --drop-mesh Hair,shoes_r,shoes_l | 14,768,984 | -43.8% | 23,997,988 | -39.5% |
| weld+u16+w8+j8 (no drop) | 20,362,936 | -22.5% | 33,760,120 | -14.9% |
| **all five** | **13,510,968** | **-48.6%** | **22,739,968** | **-42.6%** |

Note A's "-x%" is vs the whole text-glTF payload (json+bin+images) since the single-file result must carry them; vs the 81 KB .glb file alone it is meaningless.

## Geometry effects
- Weld result (vertex counts, triangles unchanged at 179,080): shoes 5,885 -> 5,452 each, Hair 141,426 -> 90,682, body 37,301 (no change), eyes/eyelash/tooth unchanged. Total 200,134 -> 148,524 vertices (-25.8%). Matches finding 25's (position, UV) unique counts (shoes 5,452 / Hair 90,682), so CLO had already welded everything except shoes and Hair duplicates.
- After drop of Hair + shoes the remaining content: body 37,301 v / 71,410 t, eyes, eyelashes, tooth = 46,938 vertices, 84,518 triangles.
- Remaining size after "all" is dominated by textures (embedded images 12.8 MB of A's 13.5 MB; body textures `MV2_Jinho_01_*` are big PNG roughness maps of 2.4-2.7 MB each). Next big win needs image recompression/resizing (not possible stdlib-only; use external tool) or dropping the ROUGHNESS PNGs.

## Validation
- Outputs of all 16 runs (8 per input): 0 errors, 0 warnings, max weight-sum deviation 0.000000 (u8 weights sum exactly 255/255).
- Input A: 0 errors. Input B (real CLO 2026.1.224 binary GLB): **18 errors, all "bufferView N offset not 4-aligned"** (image bufferViews, e.g. 71, 72, 75, 76, 77, 80-86, 89, 91-95). CLO's own export violates the glTF alignment rule (spec: bufferView offsets should be multiples of the component size; images need none strictly, our check is stricter at 4), the rewritten output has none.
- Per-mesh vertex/triangle counts re-read from each output with the report pass; triangle counts unchanged in every run (except the dropped meshes).
- No semantic comparison of positions/weights after weld was done beyond these structural checks.
