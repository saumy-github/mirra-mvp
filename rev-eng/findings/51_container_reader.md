# 51 - CLO container READER: header parse, digest, ZIP locate (lane BC)

*Status: complete for the reader; one open item (who consumes the v13 64-bit length). Date: 2026-10-30. CLO 2026.1.336, exe base 0x140000000, all addresses are RVAs. Tags: [V] verified in disassembly, [I] inferred.*

## 0. Headline

- [V] **Reader = `MVFile::ReadHeader` 0x3c277a0**, which dispatches on obj+0x34C: 0 -> **0x3be2970** (QFile/stream variant), 1 -> **0x3be3460** (FILE* "rb" variant, opened via 0x3c29f50). Both are called from the MVFile constructor chain (0x3ba17a0 -> 0x3c277a0, constructor invoked from `0x6260840`, the import entry with strings "[Not exist=%1]", "[isOpen fail=%1]", "[old version file]").
- [V] **Load does NOT verify the SHA-256 digest.** The reader reads the stored 64-hex string into obj+0x2D0, recomputes the digest of `file[0:obj+0x1B8]` with 0x3bcdbd0 and stores the result in obj+0x358, and never compares them. The only compare is `0x3bbcb10` (see 3), called only from the UtilityAPI "isValid" JSON builders 0x60857e0 and 0x6086300. The load path 0x6260840 never calls it.
- [V] **The ZIP length field 0x24 is not validated, but it IS used** as the byte count of the ZIP copy in the content-extract path (0x3bd1220). A header 0x24 larger than the real ZIP is tolerated (short read, return value ignored, tail zero-filled). A 0x24 **smaller** than the real ZIP truncates the ZIP. See 4.
- [V] Mismatch of the 16-byte magic -> reader returns false, obj+0x318 (valid flag) stays 0, and 0x6260840 logs "[old version file]" and fails the import.

## 1. Magic check - 0x3be13c0  [V]

`IdentifyKind(obj)`: loop i = 0..0x36 (55 kinds). Each pass calls 0x3ba1a70 (builds the kind -> magic table, strings at rdata 0x884c128, step 0x18, e.g. " AVT        CLO "), takes the 16-byte magic of kind i (0x3bd1490), compares with the 16 bytes read into obj+8 (0x3bf9610). On the first hit it stores **i into obj+0x2F0 (the kind is derived from the file, not checked against what the caller expected)** and returns true; no hit -> false. The read of the 16 bytes is the `fread(obj+8, 1, 16)` loop at 0x3be34a8-0x3be34d0 (and its twin in 0x3be2970); IdentifyKind is called at 0x3be34d5 / 0x3be2a0e. On false: `mov [obj+0x318], 0; return 0` (0x3be34de).

## 2. Header field reads (0x3be3460 = FILE* variant, 0x3be2970 identical layout)  [V]

Each u32 is read with 0x2e87b90 (u32 reader on the FILE/QFile), u64 with 0x3b76ad0, length-prefixed string with 0x4b74ae0.

| File offset | obj field | Reader | Use |
|---|---|---|---|
| 0x00-0x0F | obj+8..+0x17 | 16-byte read | magic -> kind (0x3be13c0) |
| 0x10 | +0x1C | u32 | format version; gates every later block (`cmp [obj+1Ch],2/3/8/9/0xA/0xB/0xD`) |
| 0x14 | +0x20 | u32 | variable-header size (writer: 0x3c0b160 result); not used further by the reader |
| 0x18 | +0x24 | u32 | PNG #1 offset |
| 0x1C | +0x28 | u32 | PNG #1 length |
| **0x20** | **+0x2C** | u32 | **ZIP offset** - consumed by 0x3bd1220 and 0x3bcc0e0 as the seek target |
| **0x24** | **+0x30** | u32 | **ZIP length** - consumed as copy/read length (section 4) |
| 0x28 / 0x30 / 0x34 / 0x3C | +0x38 (u64), +0x40, +0x48 (u64), +0x50 | | timestamps / epoch constants |
| 0x40.. | +0x58, +0x80, +0xA8, +0xD0, +0xF8 | 5 strings, each XOR-decoded with a per-string key (u32 after the string: +0x78, +0xA0, +0xC8, +0xF0, +0x118) | |
| ver >= 2/3/8/9/10/11 | +0x120.., +0x138.., +0x184, +0x18C/0x190, +0x198, **+0x1B8, +0x1BC** | | preview offset/length table; for v>=11 **+0x1B8 = digest record offset (= zip_off-68)** and **+0x1BC = its size (0x44)**; the digest string is at that offset |
| ver >= 13 (0xD) | +0x1C0 (byte, via 0x3a23cb0), +0x1C8 (u64) | | 64-bit "large content" mode, see 4 |

[V] The reader runs the same `ver >= 11` block as the writer: `fseek(f, obj+0x1B8)`, read the length-prefixed digest string into **obj+0x2D0** (0x3be3d9d-0x3be3dd3; QFile twin: 0x3be334d), then read `obj+0x1B8` bytes from the file start (0x3be3e44-0x3be3e7c), call **0x3bcdbd0 at 0x3be3e8b** (FILE* variant) / **0x3be33d3** (QFile variant) and store the result in **obj+0x358**. Then the file is re-opened, positioned at `obj+0x1BC + obj+0x1B8` (= zip_off), and `obj+0x318 = 1` (valid) at 0x3be3f1d. No compare, no branch on the result. (`bl = 1` returned.)

## 3. Where the digest IS compared - 0x3bbcb10  [V]

`int VerifyDigest(obj)`: IdentifyKind; 2 if that fails; for ver >= 11 returns `!(obj+0x358 == obj+0x2D0)` (std::string equality at 0x6665250 -> 0x1bcb7f0), i.e. **0 = digest matches, 1 = mismatch**; for ver < 11 it uses 0x3bdd530 / 0x3bdcf00 (separate legacy key check; returns 1 or 3). Only callers: **0x6085c37** (inside UtilityAPI fn 0x60857e0, string `UsePlugInFromList` area) and **0x6086581** (fn 0x6086300). They build a JSON-like result with fields `isValid` (0x89a5090) and the strings "true"/"false" (rdata 0x82665f8/0x8266600): true when the header read succeeded and the code is 0 or 3. [I] This is a metadata/"is this file genuine" query for the plugin/UtilityAPI side, not a gate on loading.

Other users of the salted-hash helper: callers of 0x3bcdbd0 are exactly 0x3be33d3 (reader, QFile), 0x3be3e8b (reader, FILE*), 0x3bf516f (SaveFile writer), 0x3c2415d (fn 0x3c23fe0, key building), 0x3c386f2 (second writer 0x3c37fa0). The salt string (rdata 0x884cb30) has a single xref: 0x3bcdbf3 inside the helper itself. So the verify side = reader computes, 0x3bbcb10 compares.

## 4. How the ZIP is located and what 0x20/0x24 do  [V]

Import flow in 0x6260840: construct MVFile (0x3ba17a0, which runs ReadHeader), `valid = [obj+0x318]` (getter 0x3bde140; false -> "[old version file]"), then branch on **obj+0x1C0**:

- **obj+0x1C0 == 0 (all files we have seen, v11/v12):** `0x3bd1220(obj, &QByteArray)`. Requires `obj+0x2C > 0 or obj+0x30 > 0`; opens the container (QFile mode 1), **seeks to obj+0x2C (header 0x20)**, takes `len = obj+0x30 (header 0x24)`; **if len == 0 it uses filesize - zip_off and writes it back to obj+0x30**; reads exactly `len` bytes into the cache buffer (obj+0x320) via 0x6676600; **the read's return value is not checked**. The buffer is then written (0x6676cc0) to a temp file and unzipped by the ZIP code. Alternative whole-file route: 0x3bd0d90 -> 0x4b6e390 opens the container path itself as a ZIP (used by ~34 other callers and by the 0x3bcc250 loader); it takes no offsets and relies on the ZIP library finding the end-of-central-directory record from the end of the file.
- **obj+0x1C0 != 0 (v>=13 files):** `0x3bcc0e0` (MVFile::ExtractContentToFile): requires obj+0x34C != 1, valid, obj+0x2C > 0; `len = [obj+0x1C8]` (u64), if len <= 0 then `size - obj+0x2C`; **seek to obj+0x2C**; copy `len` bytes in 64 MiB chunks with 0x3c448e0, which **returns false on any short read** ("[ExtractContentToFile fail=%1]").

Consequences:
- [V] 0x20 (ZIP offset) is trusted blindly: a wrong value shifts the ZIP.
- [V] 0x24 (ZIP length) is trusted as a read length in the v12 path. **Larger than real: loads fine** (explains the -600..-610 B stale 0x24 in every `avt_patch` output: the buffer just carries zero padding after the EOCD, which ZIP end-of-central-directory scanning tolerates [I]). **Smaller than real: the ZIP is truncated and the EOCD is lost -> broken load.** So if a patched ZIP ever grows beyond the base ZIP, 0x24 must be raised (and, per finding 31, any header edit is not needed for load because the digest is not checked on load; recompute it only to keep the file "genuine" for the isValid query).
- [V] 0x24 == 0 is explicitly supported (auto-fill from file size).
- [I] Digest mismatch cannot reject a load, warn the user, or log anything on this path; only the isValid query reports false.

## 5. Open items

- [I] Who sets obj+0x1C0 (ver >= 13 branch 0x3be3cb8: `0x3a23cb0` byte reader into +0x1C0 and `0x3b76ad0` u64 into +0x1C8). Finding 31 says the writer emits 12; the reader already supports 13. Not needed for our v12 files.
- [I] The ZIP library's tolerance of trailing zeros after the EOCD (explains stale-0x24 loads) was not disassembled (4b6e390 internals); it matches the empirical result.
- Not examined: the UtilityAPI entry names behind 0x60857e0 / 0x6086300.

## 6. Address cheat sheet

| RVA | Role |
|---|---|
| 0x3c277a0 | MVFile::ReadHeader, picks reader by obj+0x34C |
| 0x3be2970 / 0x3be3460 | header reader (QFile / FILE*), digest read + recompute, sets valid flag obj+0x318 |
| 0x3be13c0 | IdentifyKind: 16-byte magic vs 55-entry table |
| 0x3ba1a70 | builds kind -> magic table (rdata 0x884c128) |
| 0x3bbcb10 | VerifyDigest (the only digest compare) |
| 0x3bd1220 | read ZIP bytes: seek [+0x2C], length [+0x30] (v12 path) |
| 0x3bcc0e0 | ExtractContentToFile: seek [+0x2C], length [+0x1C8] (v13 path) |
| 0x3c448e0 | chunked copy, fails on short read |
| 0x6260840 | import entry that drives the above |
| 0x3bde140 | getter of valid flag obj+0x318 |
