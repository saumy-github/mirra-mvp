# 46 - avt_patch_tool results (lane AV)

*Status: tool complete and offline-verified; CLO behaviour untested. Date: 2026-10-29.*

Tool: `scripts/avt_patch_tool.py` (stdlib, run with `python -I`). Commands: `list`, `meshes`, `features`, `patch` (dry-run unless `--write`).

## What it does
1. Parses the single `.dan` in the container ZIP via `avs_grammar.leaf_map`.
2. In-place same-length edits: `/mapResizingAvatar/listFeatureValues` float by index (value at `off+5+4*count+4*i`), and `mapElement/bVisible` (1 byte) of every `/mapTransformer3D` node whose sibling `mapElement/qsName` equals the name (Hair, shoes_r, shoes_l). Hair hits two leaves (transformer 934,878 and shape 7,798,614), shoes one transformer each (157,983 / 541,020). `/listSkinController[2]` also has qsName "Hair"; it is deliberately NOT patched (restricted to `/mapTransformer3D`).
3. Rebuilds the ZIP (same member order/names, original compression type per member, deflate level 6, date/attrs/extra copied). Other members keep identical decompressed content (their compressed bytes may differ from the original deflate stream; not byte-identical at the compressed level).
4. Header: prefix kept verbatim; only 0x24 (ZIP length) set to the real length, 0x20 unchanged (header region length unchanged, tool aborts otherwise), digest = SHA-256(file[0:zo-68] + salt) rewritten (findings/31).
5. Refuses to write unless: .dan re-encodes byte-identically before and after; zip_off unchanged; 0x24 == real ZIP length; digest verifies; no header byte changed other than 0x24 and digest; `testzip()` clean; member names/order equal; non-.dan members content-equal; .dan length equal and differing bytes are a subset of the intended edit bytes.

## Test runs (copies of `clo_avatar_generation/input/base-1.avt`, outputs in `rev-eng/out/avt_patch/`)
| Output | Patch | .dan bytes changed | Verify |
|---|---|---|---|
| base1_h_chest.avt | feature[0] 187.96 -> 180.5, feature[2] 96.52 -> 100.0 | 6 (two floats share bytes with old values) | VERIFY OK |
| base1_nohair.avt | hide Hair (2 bVisible bytes) | 2 | VERIFY OK |
| base1_noshoes.avt | hide shoes_r, shoes_l | 2 | VERIFY OK |

`z_verify_digest.py` on all outputs: `digest_ok=True`, `ZLEN_OK` (0x24 now equals real ZIP length, unlike pipeline-patched files that are stale by ~600 B), PK at offset. `zipfile.testzip()` returns None for all. Re-reading `features` from the output shows 180.5 / 100.0. (The very first nohair run, before the `/mapTransformer3D` restriction, also patched the skin controller; superseded, file regenerated.)

## Limits (explicit)
- This tool does NOT make CLO re-deform the mesh from the floats: findings 13/19 say `.avt` load stores listFeatureValues only. Changing them changes stored numbers, not geometry.
- Whether CLO honours a patched Hair/shoes `bVisible` on load (and on `ImportAvatar`, and in GLB export) is UNTESTED. It needs a live CLO run (experiment e08 style: load patched avatar, count meshes in exported GLB). Not run here.
- Only edits that keep leaf byte length are supported; no list insert/delete.
- Whether CLO verifies digest or 0x24 on load is still unknown (findings/31 section 5); the tool keeps both self-consistent, which is stricter than the existing pipeline-patched files.
- Not tested on .zprj/.zpac (header logic is shared; digest formula was verified on them in finding 31). Loads exactly one `.dan` member; fails otherwise.
