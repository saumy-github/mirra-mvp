# 31 - CLO container header, writer and the 64-hex digest (lane Z)

*Status: complete for the writer and the digest; reader/validator not located. Date: 2026-10-29. CLO 2026.1.336, exe base 0x140000000. Tags: [V] verified (disassembly or byte-exact offline test), [I] inferred.*

## 0. Headline

- [V] The 64-hex string at `zip_off-64` is **lower-case hex of SHA-256( file[0 : zip_off-68] + ASCII "scrampling&$%!@#mvfileheader" )**. It covers the whole header (magic, all fields at 0x10-0x3C, strings, offset table, all four PNGs, the JSON blob) and **not the ZIP**.
- [V] Offline test: matches on every one of 80+ container files in the repo (AVT v11 and v12, ZPRJ, ZPAC, CLO-written exports and pipeline-patched files). Script: `scripts/z_verify_digest.py`.
- [V] Consequence: `avt_patch` keeps the prefix verbatim and swaps only the ZIP, so the digest of a patched `.avt` is **still valid** (not stale). The only stale header field is **0x24 (ZIP length)**, off by -600..-610 bytes in every patched file, and CLO loads those files anyway.
- [I] Trap: 0x24 lives inside the digested region. Anyone who "fixes" 0x24 (or the 0x28/0x34 timestamps, or the JSON) must recompute the digest, or they turn a valid file into one with a wrong digest.
- Not found: the code that reads the header and (maybe) compares the digest on load. No evidence either way that load checks the digest (section 5).

## 1. Digest algorithm

### 1.1 Offline proof  [V]

```python
import hashlib, struct
b = open(path,'rb').read()
zo = struct.unpack_from('<I', b, 0x20)[0]
SALT = b"scrampling&$%!@#mvfileheader"
assert b[zo-68:zo-64] == b'\x40\x00\x00\x00'            # u32 length = 64
assert b[zo-64:zo].decode() == hashlib.sha256(b[:zo-68] + SALT).hexdigest()
```

Hypotheses rejected first (no hit): md5/sha1/sha256/sha512/sha3/blake2 of the ZIP bytes, of each member, of the concatenated members, of the PNG, of `b[0x40:zo-68]`, of the JSON blob alone, hash-of-hash (`scripts/z_digest_test2.py`, `z_digest_test3.py`). Only "header prefix + salt, SHA-256" hits (4 equivalent variants in test3 are the same hit).

Results (`z_verify_digest.py`): digest_ok=True for base-1.avt, clo_test.avt, first.avt/.zprj/.zpac, MV2.1_*/FV2.1_*/KV1.1_* presets (version 11), Sample.zprj, autosave.zprj, all `*.exported.avt`, all `result_avatar*.avt`, all `result_project.zprj`, and every `*.patched.avt` / `clo_payload.patched.avt`.

### 1.2 Code path  [V]

| RVA | Role |
|---|---|
| 0x3bcdbd0 | `digest(this_out, QByteArray in)`: builds a QCryptographicHash with **algorithm id 4 (Qt5 = Sha256)** via 0x667c0d0, `addData(in)` (0x667c1a0), `addData(QByteArray("scrampling&$%!@#mvfileheader"))` (0x667c1a0, string at rdata 0x884cb30), `result()` (0x667c4c0), `toHex()` (0x6669810), returns it. Qt's own SHA-256 is at 0x6e46ae0 (H0 0x6a09e667 at rdata 0x8c28a90), reached through the Qt wrapper; no MD5/SHA code in the app itself is involved (MD5 transform 0x3936bc0 and Qt MD5 0x6e4a5c0 are unrelated). |
| 0x3bf4f10 | `MVFile::SaveFile()` (strings "SaveFile() file(%1) open fail", ...). Builds the header buffer `[rbp-60h]` with helpers 0x3bf54f0, 0x3bf6720, 0x3bf6690, 0x3bf4d80 (fixed block, strings, preview images, size table), then calls **0x3bcdbd0 on exactly that buffer** (call at 0x3bf516f), stores the hex in the object (+0x2D0), then 0x3bf5460 appends `u32 64` + hex and 0x3bf4e10 appends the rest, then opens the file and writes buffer, then the ZIP body. This is why the digest input equals `file[0:zip_off-68]`. |
| 0x3c37fa0 | Second (FILE*-based, "wb"/"r+b") save variant; writes the same fields one by one: 16 magic bytes, then obj+0x1C, +0x20, +0x24, +0x28, +0x2C, +0x30 (u32 each), +0x38 (u64), +0x40 (u32), +0x48 (u64), +0x50 (u32), five length-prefixed strings (+0x58 .. +0xF8), +0x140 etc. It also calls 0x3bcdbd0. |
| 0x3ba2250 / 0x3ba2490 | MVFile constructors (0x3ba2490 is the 54-byte wrapper `new(0x3A8)`). 0x3ba2250 sets obj+0x2F0 = file kind (the `r9` argument, 2 in the AVT saver), +0x34C = flags. Magic strings table (" AVT        CLO ", " ZPRJ       CLO ", ... ~50 kinds) at rdata 0x884c128..0x884c5f8 is referenced from 0x3ba1a70. |
| 0x3c27860 | MVFile base init; sets obj+0x350 = 0x18 (24, size of the fixed prefix 0x00-0x17) and zeroes +0x1C..+0x50. |
| 0x3a1aca0 | `MVAvatarSaver.cpp` "Header Creation": creates the MVFile (kind 2), sets avatar name (0x3bf7ab0), template/compatibility (0x3bf7c50), calls 0x3bcda70 (builds a "scrambled" info string into obj+0x2B0, kind-dependent) and 0x3bc80c0 (compresses the two QByteArrays at saver+0x28/+0x38, "Failed to Compression"), then `SaveFile` via 0x3bf4f10 with flag 1; failure text "Failed to save AVT file on Header Creation :" (log id W14012). |
| 0x3a03bf0 -> 0x3a03740 | AVT save driver (stream object 0x39f6170, "Save Avatar ... %s [%0.2f]"): extension check ("avac", "avte"), then 0x3a19fe0 (writes the `.dan`, "Failed to save AVT file."), 0x3a1ac40, 0x3a1d2f0, 0x3a1a5b0, 0x3a1f540 (member writers), **0x3a1aca0 (header)**, 0x3a18a40, 0x3a221d0 ("`.dan`" cleanup). |
| 0x511f4f0 / 0x60a42f0 | AVT serializer and the `ExportAVT` worker (see findings/15 section 7); they only wrap the above. |

Other users of 0x3bcdbd0 (callers at 0x3be33d3, 0x3be3e8b, 0x3c2415d, 0x3c386f2) reuse the same salted-SHA-256 helper for other file kinds / in-memory keys (0x3c23fe0 first feeds a 6-algorithm hash). Not decoded; not container related for AVT.

## 2. Header layout, revised  [V unless noted]

| Offset | Size | Meaning |
|---|---|---|
| 0x00 | 16 | magic: 4-char kind padded to 12, then `CLO `. Kind table at rdata 0x884c128 (ZPAC, ZPRJ, AVT, POS, AVS, MEA, ANM, ... ~50). |
| 0x10 | u32 | format version (obj+0x1C). Per-version blocks in the writer are gated `if (ver >= 2..11)`. Current writer emits 12; older presets are 11. |
| 0x14 | u32 | **size of the variable header after the 24-byte fixed prefix** (obj+0x20 = result of 0x3c0b160, + obj+0x350 (=0x18) gives the PNG offset). Verified `f14 + 24 == png_off` in all files (237+24=261; 222+24=246; 206+24=230; ZPRJ 218+24=242, Sample.zprj 203). It is **not** unresolved any more. |
| 0x18 | u32 | offset of PNG #1 (the front preview) = f14+24. |
| 0x1C | u32 | PNG #1 length. |
| 0x20 | u32 | ZIP offset = file offset of the body (obj+0x2C). |
| 0x24 | u32 | ZIP/body length = content size (obj+0x30). The writer checks `obj+0x30 + header_size > 0x7FFFFFFF` -> "total size exceeds 2GB" (so the whole file must be < 2 GiB). |
| 0x28 | u64 | ms timestamp (obj+0x38). |
| 0x30 | u32 | obj+0x40, **2010** in v12 files, **2008** in v11 files. Zeroed by the constructor, set by the caller. |
| 0x34 | u64 | second ms timestamp (obj+0x48). Equal to 0x28 in freshly saved files (base-1, v12); differs in some presets (MV2.1_Leo: created != modified). |
| 0x3C | u32 | obj+0x50, always equal to 0x30 in every file checked. |
| 0x40 | 5 x (u32 len + bytes) | strings obj+0x58, +0x80, +0xA8, +0xD0, +0xF8: id/author (`ce79e2364d4404e9798a`, `yelimclo`, `lucycha`), three empty strings, product string (`CLO Standalone OnlineAuth`; presets: `CLO Network OnlineAuth`). The next block starts at 0x81 in base-1 (earlier docs said 0x7D; corrected). |
| 0x81 | u32 x 4 | software version: major 2025, minor 2, patch 368, revision 54927 (same numbers as `compatibility.sw` in the JSON blob). v11 presets carry a differently shaped version block (small numbers like 2,5,9999). [I] |
| 0x91.. | u32 pairs | offset/length table of the extra preview slots (SaveFile lists: `m_PreviewFrontImage`, `m_PreviewLeftImage`, `m_PreviewBackImage`, `m_FabricThumbnailImage`, `m_PreviewTopstitchFront/BackThumbnailImage`, `m_CustomThumbnailImage`). base-1: (72086, 68064), (140150, 39747), (179897, 63290) are the three extra PNGs, then four empty slots `(243187, 0)`. 243187 = end of the last PNG = start of the JSON blob record. [I for the slot-name mapping, V for the offsets] |
| ~0xE0.. | | record count (7), JSON blob `(offset 243194 = 0x3B5FA, size 948 = 0x3B4)`, then `u32 len 19` + template name `5.1_MaleTemplate_07`. |
| **0x101** | u32 | **offset of the digest record = zip_off-68** (244142 = 0x3B9AE in base-1; verified `== zo-68` in every file). Followed by `u32 0x44` = size of that record (4-byte length + 64 hex chars). So "0x101" is the pointer to the digest record, not an unresolved value. |
| 0x105 | | PNG #1 data (for base-1; = 0x18 value 261). |
| 261+71825.. | | PNG #2, #3, #4, then a small JSON blob (`{"accessoryList", "closetIdList", "compatibility": {...sw...}, "listClothFileInfo"...}`, plain JSON, 944-951 bytes in base-1, `sEncKey2` field inside), then the digest record (`40 00 00 00` + 64 hex), then the ZIP at 0x20. |

The ~172 KB gap noted in findings/10 is therefore: three PNG previews (68 KB + 40 KB + 63 KB) + a ~1 KB JSON manifest + the 68-byte digest record.

## 3. What the digest covers / does not cover  [V]

Covered (anything in `file[0:zo-68]`): magic, version, **0x14, 0x18, 0x1C, 0x20, 0x24**, timestamps, 0x30/0x3C, id/product strings, version block, preview table, all four PNGs, JSON manifest, template name, the pointer at 0x101.
Not covered: the digest record itself and the entire ZIP (all `.dan`, textures, `clofiles.json`).

Hence two kinds of edit:
- Editing only ZIP members (what `avt_patch` / feature-float patching does): digest stays valid. 0x24 goes stale unless updated; 0x24 *is* covered, so updating it requires recomputing the digest.
- Editing any header byte (including timestamps, PNG thumbnail, JSON): digest must be recomputed with the formula in 1.1.

## 4. Do patched `.avt` files carry a stale digest?  [V]

**No.** All pipeline-patched files tested (`*.patched.avt`, `clo_payload.patched.avt`, ~30 files, ZIP shorter than base by 593-610 bytes) have `digest == sha256(prefix+salt)` because the prefix is byte-identical to `base-1.avt`. What *is* stale in them:

| Field | In patched file | Correct value | State |
|---|---|---|---|
| 0x24 ZIP length | 33,683,366 (copied from base) | `filesize - zip_off` = 33,682,756..33,682,766 | stale by -600..-610 |
| 0x28 / 0x34 timestamps | base timestamp (2026-03-31) | n/a | cosmetic |
| PNG thumbnails | base-1's | n/a | cosmetic |

Why CLO still loads them [I]: (a) the digest is valid; (b) the ZIP is located by 0x20 and parsed through the central directory at the end of the file, so the stale 0x24 is not needed for extraction; (c) the 0x24 is only compared to the 2 GiB limit on the write side. Whether the reader tolerates 0x24 mismatch by design or just never reads it is not proved (reader not found). Empirically it loads (findings/10 notes, lane F/M2 runs).

Recommendation: leave as is. If the patcher is ever changed to refresh 0x24 or timestamps, recompute the digest (one line, section 1.1); otherwise a "tidier" header would be the first file in the pipeline with a wrong digest.

## 5. Reader / validator - what is and is not known

- [V] The loading side contains `MVFileLoader.cpp` (0x3bcc250, "Failed to load the file. Invalid file." at rdata 0x884c100) but that function is a Zipper-extract helper: it opens the container as a ZIP (0x4b6e390, error "Failed to load the Zipper", log id E12013) and accepts the file if the ZIP contains a `.png` or `.obj` member. It does not check the digest.
- [V] The kind-magic table users: 0x3ba1a70 (size 0x6e4) maps kind <-> magic strings (the most likely magic validator/creator).
- Not decoded: the header parse (reading the u32 fields, mirror of SaveFile). The MVFile object has the same field offsets, so the reader is the converse of 0x3c37fa0/0x3bf4f10 but was not located in the time box. The salted hash helper's callers (0x3be33d3, 0x3be3e8b, 0x3c386f2) could contain a compare, but the ones inspected looked like other uses (key building). Verdict: **no evidence that load verifies the digest**; no evidence that it does not. The practical risk is nil while the prefix stays untouched.

## 6. Version 11 vs current (2008 vs 2010)

- [V] v11 files: f10=11, f30=f3c=2008, product string `CLO Network OnlineAuth` (these are CLO-asset presets saved by older CLO builds). v12 files: f10=12, f30=f3c=2010, product `CLO Standalone OnlineAuth`. 2008 appears with 11 and 2010 with 12 in every file checked (about 15 v11 and 60 v12 files).
- [I] The pair is a compile-time/format "epoch" constant stored twice, bumped with the container version (not the CLO release year: base-1 saved by CLO 2025.2.368 and a 2026.1 save both give 2010). I did not find an immediate 0x7DA/0x7D8 in the save path (searched .text 0x3a00000-0x3c50000 for 32-bit imm 2010: none; 2008 appears only in unrelated functions), so the value is probably loaded from a global or a constructor table. Impact for us: none; keep copying from the template.
- Digest algorithm is identical in both versions (v11 presets verify too).

## 7. Files added

- `scripts/z_verify_digest.py` - verifies digest + 0x24 vs actual size across files.
- `scripts/z_digest_test.py`, `z_digest_test2.py`, `z_digest_test3.py` - hypothesis search (kept for the record).
- `scripts/z_constscan.py` - crypto-constant scan of .text mapped to functions.
- `scripts/disasm_fn10.py` (cache `raw/disasm10/`), `raw/z_3a03740.txt`, `z_3a1aca0.txt`, `z_3bf4f10_savefile.txt`, `z_3bcc250_loader.txt`, `z_3c37fa0.txt`.
