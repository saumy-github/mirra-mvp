# ImportDXF internals (lane P)

*Status: static analysis, partial (time-boxed ~25 min)*
*Date: 2026-10-29*
*Target: CLO_Standalone_OnlineAuth_x64.exe 2026.1.336, base 0x140000000. All addresses are RVAs unless prefixed 0x14.*
*Tags: [V] verified in disassembly or bytes, [I] inference.*
*Scripts: scripts/disasm_fn5.py (cache raw/disasm5/), scripts/pdata_fn.py, scripts/callers5.py, scripts/revgraph5.py, scripts/dxf_strscan.py, scripts/rdata_dump.py. Raw dumps: raw/disasm5/ (1d97e00, 1d93a00, 57354f0_full, 476bfd0, 40972c0, dxf_region_4086000), raw/aama_rdata.txt.*

## 1. Call chain

| Step | RVA | What | Tag |
|---|---|---|---|
| ImportAPI::ImportDXF (vtbl 0x8989348 slot 21) | 0x6021f40 | `[app+0x30]==0` -> false. Lower-cases ext, accepts only `dxf` or `aama` (0x825e29c, 0x8290e9c; `.aam` is NOT accepted here although the GUI filter lists `*.dxf *.aam *.aama`, string 0x83829c0). Passes the caller's `ImportDxfOption*` through untouched to `App->[0x38]->vtbl[37]`. | V |
| `App->[0x38]` class | RTTI `CLOFileIOImpl`, vtable 0x8294390 | slot 37 = **0x1d97e00** | V (slot 37 body matches the option copy below; slot 67 -> 0x57354f0 chain confirmed) |
| CLOFileIOImpl::ImportDXF | 0x1d97e00 | Builds an internal option struct (ctor 0x5c2c1f0) from the SDK struct, converts path to wstring, calls `this->vtbl[0x218/8 = 67]`, returns **true unconditionally** | V |
| slot 67 | 0x1d93a00 | Common DXF/AMX import. Logs progress "Importing DXF" (0x8291168) or "Importing AMX" (0x8291158) depending on internal byte +0xB. If internal `bAppend` (+8)==0 calls 0x5d79c30 (clear/new document, inference) first. Calls 0x57354f0(docEditor, 0, 0x3E9, opt). | V (call), I (clear semantics) |
| 0x57354f0 | 0x57354f0 | Big file-type switch (PatternEditor.cpp, string 0x8933cf0). For mode `[opt+0x14]==1` (DXF): constructs reader 0x407ec10 (vtable 0x88685e0), load = 0x40972c0, then pattern build 0x40988e0, then finalize 0x4741590. | V |
| Reader class | vtable 0x88685e0, ctor 0x407ec10 | Copies the internal option struct into reader+0x70 (copy-assign 0x5c2d850). Reader fields: autoscale `reader+0x7E` (getter 0x40958b0), scale `reader+0x88` (getter 0x4092ab0), angle `reader+0x8C`. | V |
| Pattern/annotation parser | 0x4096c80 | Parses text annotations: PIECE NAME, UNITS, SAMPLE SIZE, GRADE RULE TABLE, NUMBER OF SIZES, SIZE LIST, RULE:, QUANTITY, CATEGORY, MATERIAL, STYLE NAME, PRODUCT, VERSION, AUTHOR (strings at 0x88685f0..0x8868a90). | V (string xrefs) |
| Post-processing | 0x4741590 -> 0x476bfd0 (+0x476af10 "all lines converted to baselines" warning) | Applies user scale when autoscale is off, rotates by angle, notch handling, etc. | V (see 3) |

Source file names embedded in the exe: `Compatibility\DXF\DXFPiece.cpp`, `Compatibility\DXF\DXFWriter.cpp` (0x88688e0, 0x8868950), `Interface\Editor\PatternEditor.cpp` (0x8933cf0). The reader is a separate class from the writer.

## 2. Option struct (ImportDxfOption, SDK 336) and what is read

SDK layout, derived from the header declaration order (natural alignment; size 0x1C) [I for the exact padding, V that the reads below land on these offsets]:

| Off | Field | Read by 0x1d97e00 | Internal-struct slot (rsp+0x20 base) |
|---|---|---|---|
| 0x00 | m_bAppend | yes | +0x08 |
| 0x01 | m_bAutoScale | yes | +0x0E (reader+0x7E) |
| 0x04 | m_Scale (float) | yes | +0x18 (reader+0x88) |
| 0x08 | m_Angle (float) | yes | +0x1C (reader+0x8C) |
| 0x0C | m_bImportPatternAnnotation | yes | +0x0F |
| 0x0D | m_bAutoTraceAsInternalLines | yes | +0x09 |
| 0x0E | m_SwapCuttingLineAndSewingLine | yes | +0x0A |
| 0x0F | m_bIncludeNotchs | yes | +0x74 |
| 0x10 | m_bAutoDistribute | yes | +0x0C |
| 0x11 | m_bOptimizeAllCurvePoints | yes | +0x0D |
| 0x12 | m_bImportAllDrawCurvePoint | yes | +0x11 |
| 0x13 | m_bRemoveNonGradingPoints | yes | +0x75 |
| 0x14 | m_bConvertToSeamAllowance | **NOT read** (confirms "deprecated") | - |
| 0x15 | m_bImportNotchTo | yes | +0x83 |
| 0x18 | m_eNotchImportPlacement (int) | yes, clamped: `min(value, 2)` unsigned (`cmp 2; cmovbe`), so -1 or >2 becomes 2 (Both) | +0x84 |

Fixed by the wrapper (not user controllable): internal +0x14 = 1 (mode DXF), internal +0x0B = 0 (not AMX).
Defaults: m_bIncludeNotchs=false means notch points are NOT imported unless set. Note a second gate: m_bImportNotchTo (default true) and placement.

## 3. Auto-scale vs m_Scale precedence

- [V] 0x476bfd0 (post-process, non-".rul" branch): `0x40958b0` returns autoscale. The code calls the annotation parser 0x4096c80 with autoscale as 3rd arg, then `if (!autoscale) { s = reader.scale (0x4092ab0); pieces.scale(s) via 0x40a1ac0 }` (0x14476C31D..0x14476C338). Therefore **m_Scale is applied only when m_bAutoScale is false.** With the default m_bAutoScale=true, `m_Scale` is ignored at this stage; there is no multiply of both here.
- [V] In the build step 0x40988e0 (0x144098D6E..0x144098DB5) the reader overrides `reader+0x88` (the same scale float) from file/document unit data: `if ([ctx+0x2AC098]==1) { scale=1.0; switch([ctx+0x2AC09C]) { 1 -> 25.4 (inch->mm); 5 -> 10.0 (cm->mm); 6 -> 1000.0 (m->mm); else stay 1.0 } }`, then each piece is scaled by that factor via 0x40a1590 (loop at 0x144098E20). So the file-unit conversion to mm is always applied when the unit info is present, independent of m_Scale.
- [I] Net effect: autoscale=true means "use file units (UNITS: METRIC/ENGLISH from the AAMA annotation, converted to mm), ignore m_Scale". autoscale=false means "apply file-unit conversion AND then user m_Scale" (possible double scaling only on that branch, since ctx+0x2AC09C may be derived from the same units; not fully traced). Which unit code a file without `UNITS:` text yields is not determined (see 4).
- [I] FINDINGS.md item "m_Scale set while m_bAutoScale stays true (possible double scaling)" is therefore refined: the plugin's m_Scale is silently **ignored** (not doubled) while autoscale is true. The plugin only ever passes m_Scale=1.0 by default (RestPlugin_windows.cpp l.1858), so today there is no visible effect either way, but a caller-supplied scale will NOT work unless `m_bAutoScale=false` is also set. Recommendation below.

## 4. Format / units handling

- [V] The pattern reader is an **AAMA/ASTM-D13 DXF reader** (strings: "ASTM/D13 Proposal 1 Version: D 6673-04", "ANSI/AAMA VERSION: 1.0.0", "UNITS: METRIC", "UNITS: ENGLISH", Gerber/AccuMark/Lectra/OptiTex/assyst/Boke/PAD/FK Group vendor tags at 0x88687b0..0x88688d0). Units come from the **`UNITS:` annotation text entity** (METRIC / ENGLISH), not from `$INSUNITS`/`$MEASUREMENT`.
- [V] `$INSUNITS` (0x8834d70) and `LWPOLYLINE/SPLINE/ELLIPSE/ARC/CIRCLE/INSERT/DIMENSION` (0x8834c80..0x8834d58) strings are referenced only from generic-DXF code (writer 0x408afd0 and a graphic importer around 0x3940ec0/0x39423d0 "Failed to load DXF." 0x8834d80), **not** from the pattern reader chain. [I] `$INSUNITS`/`$MEASUREMENT` in a pattern DXF are most likely ignored by ImportDXF.
- [V] If the loaded file is not recognised as AAMA/ASTM, CLO shows the message at 0x8892080: "This software supports DXF-AAMA or DXF-ASTM file formats only. As the loaded Pattern file is not in DXF-AAMA or DXF-ASTM format, all lines will be converted to Baselines." (called from 0x476af10 via 0x4741590). So a non-AAMA DXF imports as loose baselines/lines, not as pieces. [I] This is likely a modal message box.
- [I] Entity types actually used by the AAMA reader (from the reference export in product_ingestion/clo_block/reference_dxf/*.dxf): POLYLINE (layers 1, 8, 84, 87), POINT (layers 2/3/4 incl. notch Z=7 + angle), LINE (layer 7 grain), TEXT (annotation, layer 1), INSERT of a BLOCK in ENTITIES. Not independently traced to the layer-dispatch code (time limit): the layer-number semantics below are taken from CLO's own export plus the writer docstring, not from decoded reader branches.

Layer semantics (CLO's own AAMA export, ground truth for what the reader accepts) [I]:

| Layer | Content |
|---|---|
| 1 | closed POLYLINE sewing/boundary line; TEXT annotations (PIECE NAME, UNITS ...) |
| 2 | POINT turn points |
| 3 | POINT curve points |
| 4 | POINT notch (Z=7, code 50 angle) |
| 7 | LINE grainline |
| 8 | POLYLINE internal lines |
| 84 / 87 | cutting-line / seam-allowance duplicates (161 entities each in front_panel.dxf) |
| 85 | small count (8) auxiliary |

## 5. Return value and failure behavior

- [V] `ImportAPI::ImportDXF` returns `false` only for: no document (`[app+0x30]==0`), extension not dxf/aama, or the inner call returning false. The inner `CLOFileIOImpl::ImportDXF` (0x1d97e00) returns false only if the global at 0x14A2ABF10 is null; otherwise it ignores the result of `vtbl[67]` and returns **true** (`mov al,1` at 0x141D97EF6).
- [V] Consequently an empty, truncated, non-DXF, or non-AAMA file returns **true** when it exists with a .dxf/.aama extension. 0x57354f0 reports failure via GUI messages: "This file is not a DXF format." (0x8383488), "Failed to load the DXF file." (0x8934470); progress "Loading DXF file" (0x8934490). [I] These are modal boxes (call through 0x4b78600 / 0x2d78110), which can block the plugin's GUI thread.
- [V] Same-path partial import also returns true (no counting of pieces created). The plugin's own `g_patternsLoaded` is therefore the only trustworthy success signal.
- [I] A missing file path: the wstring is passed to 0x40972c0 which returns false -> error box -> still `true`.

## 6. Comparison with the repo DXF writer (product_ingestion/clo_block/step_05_3_clo_dxf_writer.py)

The writer is a good mirror of CLO's AAMA export (R12, AC1009, numeric layers 1/2/3/4/7/8/84, closed POLYLINE boundary, grainline LINE, notch POINT with Z=7). Mismatches/risks:

1. **Missing AAMA annotation TEXT entities** [V by reading both files]. CLO's reference has TEXT entries `PIECE NAME: 1`, `SAMPLE SIZE: M`, `UNITS: METRIC`, `QUANTITY: 1`, `SIZE: M`, `STYLE NAME:`, `ANSI/AAMA VERSION`, `AUTHOR`, `VERSION: 3`, etc. (parsed by 0x4096c80). The writer emits only one TEXT `"{piece} {label}"` and relies on `$INSUNITS=4`/`$MEASUREMENT=1` which the pattern reader does not read. Risk: units default/unknown (could import 25.4x or 1x off), piece names are the label string rather than `PIECE NAME:`, and the file may be classified as non-AAMA ("all lines converted to Baselines"). **Highest-priority fix: add `UNITS: METRIC` and `PIECE NAME: <n>` (and `SAMPLE SIZE:`) TEXT entities on layer 1, following CLO's reference encoding.**
2. The reference header has `$DWGCODEPAGE ANSI_1252`, `$LIMMIN/$LIMMAX`, `$EXTMIN/$EXTMAX = 1e20 / -1e20`; the writer writes real extents and no codepage. Low risk. [I]
3. Layers 84/87 duplication: reference has the cutting line on both 84 and 87 (161 vertices each); writer only emits 84 when `seam_allowance_mm>0`, as an offset polygon, and never 87. CLO's auto seam-allowance detection (m_bConvertToSeamAllowance is deprecated, "automatic when a seam allowance is detected") may need 84+87 or may misclassify the offset as a second piece/internal line. [I]
4. Notches are dropped by default: plugin leaves `m_bIncludeNotchs=false` ([V] field 0x0F read at 0x141D97E71 and copied). Writer's layer 4 notches are therefore ignored at import. Set `m_bIncludeNotchs=true`, keep `m_bImportNotchTo=true` and placement (0/1/2).
5. Winding: the reader code path for orientation was not decoded. CLO reference polyline direction was not measured here. [I] unknown; verify via output DXF vs reference (sign of shoelace area).
6. Closed polylines: writer drops a duplicate closing vertex and sets the closed flag (70=1): consistent with CLO R12 POLYLINE. [I]
7. Grainline: writer emits LINE on layer 7 (matches). The reference grain is also layer 7 per docstring. [I]
8. Existing output files (product_ingestion/output/c_001/s_001/001/panels/dxf/*.dxf, dated Sep 12) predate the new step_05_3 writer in some respects (they have `$INSUNITS 4`, `$MEASUREMENT 1`, layers 1..8) but are 12-20 KB vs the reference 70-88 KB; no `UNITS:` text was verified in them.
9. The plugin passes `cmd.param1` as `std::string`, converted internally; non-ASCII paths are risky [I]; extension must be exactly `.dxf`/`.aama` ([V]).

## 7. Recommendations

1. In the plugin, set `options.m_bAutoScale = true` (default) and rely on file units, **or** set `m_bAutoScale=false` together with `m_Scale` if an explicit scale is wanted. Do not set m_Scale alone: ignored while autoscale is true [V].
2. Add `UNITS: METRIC`, `PIECE NAME: <n>`, `SAMPLE SIZE: <label>` TEXT annotations to the DXF writer (layer 1, height 0.25/2.5 as in reference). Verify in CLO that sizes match flat-pattern dimensions (a 1 mm vs 25.4 mm error is the observable symptom).
3. Set `m_bIncludeNotchs = true` in the import-pattern command if notches are needed for seams; keep `m_bAppend=true`.
4. Do not trust `ImportDXF`'s return: it is `true` for empty/invalid files. Verify via `GetPatternCount()` before and after (already `g_patternsLoaded` in the plugin).
5. Validate DXF files before import (extension .dxf/.aama, at least one closed POLYLINE on layer 1, `UNITS:` text present, no zero-length file) to avoid modal "not a DXF format" / "Failed to load" dialogs that block the GUI thread.
6. Open items (not done): decode layer-number dispatch in 0x40a1dc0/0x4093e90/0x4099550 (SAMPLE SIZE and piece assembly); confirm what `[ctx+0x2AC098/0x2AC09C]` is (file unit vs display unit); determine winding handling; test with the real exe is out of scope (no execution allowed).
