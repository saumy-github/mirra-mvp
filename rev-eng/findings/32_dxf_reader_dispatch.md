# AAMA/ASTM DXF reader dispatch (lane AA)

*Status: static analysis, time-boxed (about 40 min), partial where marked*
*Date: 2026-10-29*
*Target: CLO_Standalone_OnlineAuth_x64.exe 2026.1.336, base 0x140000000. Addresses are RVAs unless prefixed 0x14.*
*Tags: [V] verified in disassembly/bytes, [I] inference.*
*Scripts: scripts/disasm_fn11.py (cache raw/disasm11/), scripts/aa_region.py, scripts/aa_brief.py. Raw: raw/aa_region_fns.txt, raw/aa_4093e90.txt. Region dump reused: raw/disasm5/4086000_1d000.txt.*

## 0. Correction to lane P (units)

[V] The unit code at `[ctx+0x2AC09C]` is the DXF header variable **`$INSUNITS`**, not the `UNITS:` text. Writer: 0x3940ec0 section type 1 (HEADER) calls 0x39423d0 (which looks up the string `$INSUNITS`, 0x8834d70); if the result is >= 0 it stores `[ctx+0x2AC09C]=value` and `[ctx+0x2AC098]=1` (0x143941579 / 0x14394157F). `ctx` is the loaded-DXF document object (`reader+0x110`). The builder 0x40988e0 then (0x144098D6E..DB5) multiplies every piece by a factor: `$INSUNITS` 1 (inch) -> 25.4, 5 (cm) -> 10, 6 (m) -> 1000, anything else (including 4 = mm, 0, 2 feet, 3 miles...) -> 1.0. This scale call (0x40a1590, per 0x250-byte piece) is applied only when `[ctx+0x2AC098]==1`, i.e. only if `$INSUNITS` is present in the HEADER section.
[V] CLO's own reference DXFs (product_ingestion/clo_block/reference_dxf/*.dxf) have NO `$INSUNITS` in the header (header = `$ACADVER AC1009`, `$DWGCODEPAGE ANSI_1252`, `$EXTMIN/$EXTMAX 1e20`, `$LIMMIN/$LIMMAX 0..420x297`); they carry `UNITS: METRIC` as a TEXT entity (front_panel.dxf line 14152). So the two mechanisms are independent: `$INSUNITS` (this scale) and the `UNITS:` text (parsed in 0x4096c80, header-style annotation handling; exact effect on reader+0x88 not traced, [I] it sets the same mm-conversion for ENGLISH).
[I] The repo writer emits `$INSUNITS 4` (mm): safe, factor stays 1.0. It also emits no `UNITS:` text. Whether a DXF with no `UNITS:` text defaults to METRIC was not decoded (see section 8).

## 1. Layer 1: generic DXF loader (group codes, sections, entities)

- [V] Reader call chain: 0x40972c0 (thin wrapper) -> 0x4086a50 (clear lists) -> **0x3940ec0** (generic DXF file loader, size 0x6f3, uses a vendored typed DXF library; opens file 0x39419c0; prints "Failed to load DXF." 0x8834d80 if the document pointer is null).
- [V] Group-code/value pair parsing is **inside the vendored library**, not in a function in the Mirra namespace: 0x3941690 returns the next section id, 0x39420b0 returns the next typed entity record (a ~0x200-byte-field record with a 16-bit entity-type tag at +0). The reader never sees raw group code/value pairs; only typed records. Group-code level decoding was not traced (library internals).
- [V] Section ids dispatched in 0x3940ec0 (0x143940FD0..): 1 = HEADER (only `$INSUNITS` is read), 4 = TABLES (sub-tables LTYPE/LAYER/STYLE/DIMSTYLE are copied into 0x248-byte records), 8 = BLOCKS (block records at `ctx+0x63840`, stride 0x248, name at +0x63844, count at `ctx+0x2AB840`), 0x10 = ENTITIES. Each BLOCKS/ENTITIES entity goes to 0x393afe0.
- [V] 0x393afe0 (size 0x9c0) switches on the 16-bit entity-type tag with a jump table at 0x393b944 (23 entries, types 1..23). Types **with a handler**: 1, 2, 3, 7, 8, 11, 14, 19, 23. All other type tags (4,5,6,9,10,12,13,15-18,20-22) jump to 0x393b8ec = silently skipped. Dedicated cases: type 7 (0x393b298) copies a 0x868-byte record with a 0x800-char string, so it is TEXT/MTEXT; type 19 (0x393b6ed) looks up a block by name via 0x393f9c0, so it is INSERT. [I] Mapping of the other tags to LINE/POINT/ARC/CIRCLE/POLYLINE: types 1 and 8 end in the same line/polyline builder 0x409fe40; type 2 in the point handler 0x40a0a70; type 3 in the arc/circle handler 0x409e2e0. Exact tag-to-DXF-name mapping is [I] only.
- [V] Entity strings present in the vendored library region (0x8834c80..0x8834d58): BLOCK, ENDBLK, ENDSEC, VERTEX, CIRCLE, ELLIPSE, ARC, INSERT, LWPOLYLINE, SPLINE, DIMENSION, LAYER, LTYPE, STYLE, DIMSTYLE, TABLE, ENDTAB, SECTION, HEADER, TABLES, BLOCKS, ENTITIES, EOF. The pattern reader only acts on the nine handled type tags above, so SPLINE/ELLIPSE/DIMENSION entities are [I] ignored (no handler path found), TEXT/INSERT/POINT/LINE/POLYLINE/ARC/CIRCLE are consumed.
- [V] Block loop vs entity loop in the builder 0x40988e0: first loop iterates **BLOCKS** (0x393f9b0 / 0x393fbb0 with iterator), calling 0x407e6c0 (new piece), then per entity 0x4099550 (block-level dispatcher, switch on tag: 1 -> 0x409fe40, 2 -> 0x40a0a70, 3 -> 0x409e2e0, 7 -> TEXT 0x40a1dc0, 19 -> 0x40a0c80); second loop iterates the **ENTITIES** section calling 0x4099700 (top-level dispatcher: jump table 0x4099928, tags 1,3,7,8,14,19 handled; type 7 TEXT looks up the matching block with 0x393f9b0 and calls 0x40a1dc0; INSERT of a block resolves the block as the piece geometry).

## 2. Layer-number semantics actually coded

The layer name in the DXF is parsed to an integer (copied through 0x393e4c0, converted via 0x393fdc0 with flags 8/0x10/0x20 as int). Object layer field is `[obj+0x24]` (or word at +0x67 for POINT) .

[V] Layer-class predicates:
- 0x4096580: layer is "piece outline-ish" when `layer <= 0xE and bit set in mask 0x4902` (bits 1, 8, 11, 14) **or** `84 <= layer <= 86` **or** `layer == 87`. So layers {1, 8, 11, 14, 84, 85, 86, 87}.
- 0x40965B0: `layer == 14 || layer == 1`.
- 0x4097310 (geometry collection): copies polylines out of the layer map (`std::map` at `reader+0x208`, key at node+0x20) only for layers in mask 0x4913 = bits {0, 1, 4, 8, 11, 14}; vector at node+0x28..0x30, stride 0x50.
- 0x4097D44: `cmp eax,54h` (84) in 0x40979d8 (post-pass; seam-allowance / cutting-line handling, not fully decoded).

[V] POINT handler 0x40a0a70 (layer = `word [point+...]`, sign-extended):
- layer 3: curve point, appended to the piece's curve-point list via 0x407eed0 -> 0x4084fb0 with index `[piece+0x14C]`.
- layer 4, or layers 0x50..0x53 (80..83): notch (`lea eax,[r8-50h]; cmp ax,3`), shared branch at 0x40a0bd1. These are the notch point handlers (80-83 are notch variants/types).
- layer 13 (0xD): drill hole / internal point (0x407ee50 + 0x40851e0, tag 0xD).
- layer 2: turn point; special vendor flag: compares `reader+8` string to "Lectra" (0x88687fc) and branches into 0x4085fc0 (turn-point insert, with or without Lectra handling).
- other layers on POINT: ignored.

[V] LINE/POLYLINE-ish handler 0x409fe40 (layer in DX): layer 7 = grainline (computes angle from the two end points with 0x3bcea40 atan2, stores via 0x409ea30); layers 5 and 6 get dedicated branches (0x4085e50 / 0x40a1c90; [I] grade-reference line 5, mirror line 6); any other layer becomes a two-point internal line appended to the piece's line list (stride 0x48 vertices). The `0x108` byte arg selects the first branch.
[V] ARC handler 0x409dec0: normalises start/end (adds 2*pi when start>end), tessellates through 0x4b6a790 with 10 segments, then pushes vertices; used for internal curves.
[V] TEXT handler 0x40a1dc0 (annotation key table at 0x4096890): see section 3.
[I] Layers 11/14 predicates: 14 = text/annotation layer in AAMA (layer 14 text, layer 1 outline), 11 = buttonhole/internal shape layer. Layer 15, 84/85/87 semantics beyond "belongs to the outline predicate" were not individually decoded.

## 3. Text annotation parser

- [V] Keyword table 0x4096890 (size 0x3e0): builds a bitmask by `contains/starts-with` matching (0x6666660) of the TEXT string against: `PIECE NAME` (bit 0), 0x836AEB0 (bit 1; likely "Style Name"), 0x846800C (bit 2; likely "Units"), 0x82CBBD0 (bit 3; likely "Tolerance"), `SIZE`, `AUTHOR`, `VERSION`, `QUANTITY`, `CATEGORY`, `MATERIAL`, `Creation`, `ASTM`, `Grade Rule Table`. A TEXT whose content hits one of these is a header/piece annotation; all other TEXT is generic text.
- [V] 0x40a1dc0 per-TEXT parser (size 0xb29), compares with `PIECE NAME` (0x88685f0), `SAMPLE SIZE` (0x8868640), `SIZE` (0x8868804), `ANNOTATION` (0x8868810), `AUTHOR` (0x886881c), `Marvelous` (0x88687b0) / `CLO` (0x82631a0) (vendor check), `VERSION`, `QUANTITY`, `CATEGORY`, `MATERIAL`. `PIECE NAME:` sets the current piece's name (0x40a0a40 after 0x6668780 value extraction). `SIZE:` goes to 0x40a1c60 (per-piece size). `ANNOTATION` text is treated as piece annotation text (used when `m_bImportPatternAnnotation`).
- [V] 0x4096c80 (header text parser, size 0x635): `UNITS` (0x88685fc), `GRADE RULE TABLE`, `NUMBER OF SIZES`, `SIZE LIST`, `SAMPLE SIZE`, `RULE:`/`RULE :`. `UNITS: METRIC` / `UNITS: ENGLISH` are the literal strings the writer 0x409c490 emits (0x8868740/0x8868750).
- [V] Strings emitted by the CLO writer (0x409c490), i.e. the grammar CLO itself produces: `PIECE NAME: `, `SIZE: `, `QUANTITY: %1,%2`, `QUANTITY: %1`, `CATEGORY: `, `MATERIAL: `, `STYLE NAME: %1`, `PRODUCT: `, `VERSION: `, `SAMPLE SIZE: %1`, `Grade Rule Table: %1`, `Curve Tolerance: %1`, `ANSI/AAMA VERSION: 1.0.0`, `AUTHOR: CLO Virtual Fashion Inc.`, `CREATION DATE: `, `CREATION TIME: `.
- [I] Mandatory for a piece: the piece builder only needs a closed outline plus a block context; a `PIECE NAME:` TEXT supplies the name. A piece without `PIECE NAME` is not rejected in the code found; the name falls back to the block name / default (`pattern`+`_%1` seen at 0x4093cb0) [I]. Not verified with a run.
- [V] A piece without a closed boundary: 0x4095E40 checks that the piece has more than one outline polyline; 0x4095A10 returns "empty piece" when `[piece+0x14]==0`, no lines and no layer-1 outline; empty pieces are not added to the document ([I] they are dropped silently, no GUI message found).
- [V] Non-AAMA file (no recognised AAMA structure): GUI text at 0x8892080 and everything is converted to baselines (0x476af10).

## 4. Closed polylines and winding

- [V] Auto-close: 0x4095920 (and 0x409512c): if the polyline has >= 3 vertices, is not flagged closed (`[poly+0x20]==0`) and `distance(first, last) < tolerance` (global float at 0x82703D8) it sets the closed flag (`[poly+0x20]=1`); 0x409512c additionally pops the duplicate last vertex. So a DXF polyline that repeats the first point is accepted as closed; a polyline whose endpoints are farther apart than the tolerance stays open ([I] later treated as internal line, not as a piece outline).
- [V] Point-in-segment/collinearity helper 0x4096060 uses the absolute value (`andps` with mask 0x82704A0) of the 2D cross product, so it is orientation independent.
- [I] No signed-area (shoelace with sign test) computation was found in the reader functions 0x4093e90 / 0x4095xxx / 0x40988e0. The reader therefore appears **not** winding-sensitive; CLO flips orientation, if needed, at creation of the 2D piece later. Not proven; the final step 0x4741590 / 0x476bfd0 was not rescanned for area sign.

## 5. Curve points and bulge

- [V] Curve interpretation is by **layer 3 POINTs**, not by polyline bulge (code 42) or a `$curve` flag in the reader. A closed boundary polyline (layer 1) holds the corner and sample vertices; layer 3 POINTs mark which vertices are curve points (index list `[piece+0x14C]`); 0x4097310 re-runs a curve tessellator `0x4b6afb0(list, pts_out, idx_out, tolerance)` (tolerance float at `[item+0x10]`) and rebuilds vertices (0x48 stride, vtable 0x882e808) when more than 2 points result. `Curve Tolerance:` annotation sets that tolerance.
- [V] Option effects (cf. lane P table): `m_bOptimizeAllCurvePoints` (+0x0D) and `m_bImportAllDrawCurvePoint` (+0x11) feed this stage.
- [I] POLYLINE bulge (group 42) is [I] not interpreted by the pattern reader (the vendored library may expand bulges; ARC entities are tessellated with 10 segments by 0x409dec0).

## 6. Units summary

| Source | Effect | Tag |
|---|---|---|
| `$INSUNITS` header var present (-> `[ctx+0x2AC098]=1`, `[ctx+0x2AC09C]=v`) | scale pieces: v=1 -> 25.4, 5 -> 10, 6 -> 1000, other -> 1.0 | V |
| `UNITS: METRIC/ENGLISH` TEXT | parsed in 0x4096c80; CLO writes METRIC | V (strings), I (exact effect) |
| `ImportDxfOption.m_bAutoScale=false` | then user `m_Scale` applied at 0x476bfd0 | V (lane P) |

[I] Default for a file with `$INSUNITS 4` and no `UNITS:` text: factor 1.0, mm. This is the repo writer's current state, so no 25.4x error is expected from `$INSUNITS`; the risk is only the missing `UNITS:` text.

## 7. Comparison with the repo writer and a clean-import checklist

Repo writer: `product_ingestion/clo_block/step_05_3_clo_dxf_writer.py` (R12 AC1009, numeric layers 1/2/3/4/7/8, optional 84, closed POLYLINE on layer 1, one TEXT label). Reference DXFs: `product_ingestion/clo_block/reference_dxf/*.dxf` and identical copies at `C:\Users\Saumy\Downloads\{front,back}_panel.dxf, sleeve_left.dxf, sleeve_right.dxf`.

Differences: reference has `PIECE NAME: 1`, `UNITS: METRIC` and the other annotation TEXT entities; header without `$INSUNITS`, with `$DWGCODEPAGE ANSI_1252`, `$LIMMIN/$LIMMAX`, `$EXTMIN/$EXTMAX 1e20`; writer has `$INSUNITS 4`, `$MEASUREMENT 1`, real extents, only one TEXT label.

Checklist (what a DXF must contain to import cleanly):
1. Extension `.dxf` or `.aama`, non-empty, readable ASCII DXF with SECTION/ENDSEC structure, ending in `EOF` ([V] ImportAPI::ImportDXF; empty/bad files still return true).
2. HEADER: `$ACADVER AC1009` (R12 as CLO exports; AC1015 also exists in the writer) and either no `$INSUNITS` or `$INSUNITS 4` (mm). Do not write 1, 5 or 6 unless the coordinates really are inch/cm/m ([V] 0x40988e0 scaling).
3. Annotation TEXT entities in the grammar CLO writes: at minimum `PIECE NAME: <name>`, `UNITS: METRIC`, `SAMPLE SIZE: <label>`, `SIZE: <label>`, `QUANTITY: 1`; recommended: `ANSI/AAMA VERSION: 1.0.0`, `AUTHOR:`, `VERSION:` (0x40a1dc0 / 0x4096c80 key table) [V strings, I which are strictly required].
4. One closed POLYLINE per piece on layer `1` (numeric layer name, not "CutLine"), or a repeated first vertex within tolerance (0x82703D8) so it auto-closes; at least 3 vertices ([V]).
5. Pieces are grouped per BLOCK (INSERT in ENTITIES) as in the reference, or as top-level entities; block name `<index>_<label>` as in the writer ([V] both loops exist; the CLO layout is the only tested form).
6. Layer 2 POINT = turn points, layer 3 POINT = curve points (vertices that must be smooth), layer 4 (or 80..83) POINT = notch (Z=7, angle in group 50 [I]), layer 13 POINT = drill hole, layer 7 LINE = grainline (two points; angle computed from them), layers 5/6 LINE = grade-reference/mirror, layer 8 POLYLINE/LINE = internal lines, layers 84/87 = cutting/seam allowance copies ([V] predicates, I for exact meaning of 5/6/84/85/87).
7. Notches additionally need `ImportDxfOption::m_bIncludeNotchs = true` and `m_bImportNotchTo = true` ([V] lane P).
8. Use only entity kinds the loader handles (tags 1,2,3,7,8,11,14,19,23: LINE, POINT, ARC, CIRCLE-like, TEXT, POLYLINE, INSERT); SPLINE, ELLIPSE, DIMENSION, SOLID and others are dropped ([V] jump table default).
9. Winding: none required found ([I]); keep the reference orientation to be safe.

## 8. Open items (not done)

- Exact tag-to-entity-name mapping of the vendored library's entity type enum (1..23), and which tag POLYLINE uses; 0x393afe0 case bodies for types 8, 11, 14, 23 were not read.
- Whether absence of `UNITS:` text defaults to METRIC (0x4096c80 not fully traced), what `UNITS: ENGLISH` does, and whether `PIECE NAME` absence yields a default name or a skipped piece.
- Layer 11/14/15/84/85/87 individual roles; 0x40979d8 (seam-allowance/cut-line post-pass) body.
- Signed area / winding in the post stage 0x476bfd0 / 0x4741590.
- Group-code pair decoding is inside the vendored DXF library and was not traced.
