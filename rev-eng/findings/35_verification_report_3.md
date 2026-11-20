# 35 - Verification report 3 (lane M3)

*Date: 2026-10-29. Method: raw re-derivation with dumpbin /disasm, PE byte scans and file stats. Scripts: scripts/m3_dispscan.py, scripts/m3_ctx.py (plus disasm_fn.py). Addresses are VA (base 0x140000000) unless marked RVA.*

## Verdict table

| # | Claim | Verdict | Key evidence |
|---|-------|---------|--------------|
| 1a | `[ctx+0x2AC09C]` (DXF unit code) comes from header var `$INSUNITS`, not the `UNITS:` text parser | VERIFIED (with refinement) | One store (0x143941579) and one read (0x144098D88) of disp 0x2AC09C; stored value = atoi of the `$INSUNITS` value |
| 1b | Builder 0x40988e0 scale branches (inch 25.4, cm 10, m 1000, else 1) | VERIFIED | 0x144098D75-0x144098DB5, gated on `[ctx+0x2AC098]==1` |
| 2a | 0x70d98d8 / 0x70d986c are `_Init_thread_header` / `_Init_thread_footer` | VERIFIED | SRW lock + condvar + TLS epoch 0xB8B8 |
| 2b | 0x5cbfda0 Folding 0-9 / Draping to 50 (40), fields +0x34/+0x38 | VERIFIED (mechanics); trigger predicate UNVERIFIED | edi = 10 or 0, r12d = edi+0x28 |
| 3 | Male preset sizes/layout | VERIFIED with correction | file = 8-byte (rows, cols) header + rows*cols*4 |
| 4 | .avt loader range: no direct path to resize driver; count indirect calls | VERIFIED: exactly 3 indirect calls remain | vtable disp 0x308, 0xC8, 0x238 |
| 5 | AddSeamlinePairGroupPartial: -5/-6 before -1 | VERIFIED | 0x145F94E6B / 0x145F94E90 precede 0x145F94E9D |

## 1. DXF unit code
* Byte scan of all .text for disp32 0x002AC09C (`9c c0 2a 00`): exactly two hits.
  * WRITE 0x143941579: `mov dword ptr [rdi+2AC09Ch],eax` inside DXF loader 0x3940ec0 (RVA), HEADER-section branch at 0x143941550: `call 0x39423d0` then `test eax,eax; jns 0x143941579`. eax is the return of 0x39423d0.
  * READ 0x144098D88: `mov eax,[rax+2AC09Ch]` in builder 0x40988e0 (RVA).
* 0x39423d0 (RVA): strcmp(line, "$INSUNITS") (string at 0x148834D70; IAT 0x1482377B0 resolves to `strcmp` via hint/name table). On match it reads the next value line and calls IAT 0x148236FE8 = `atoi`, returning the integer. On mismatch it compares with "ENDSEC" (sets `[rbx+0xB0]=0`) and returns -1. The loop at 0x143941550 repeats while the return is negative, until ENDSEC.
* 0x14394157F `mov dword ptr [rdi+2AC098h],1` writes a different field (a "units valid" flag), not the unit code.
* Other writers of the unit code: none by explicit displacement. The qword store `mov [rbx+2AC098h],rdi` at 0x14393F199 (constructor/reset, rdi=0) zeroes both 2AC098 and 2AC09C. No other instruction addresses 0x2AC09C.
* The `UNITS:` text parser 0x40a1dc0 (RVA): no reference to 0x2AC098/0x2AC09C. All hits in 0x2AC098..0x2AC0A0 byte scan: 0x14393B755/75E/77A, 0x14393F19C, 0x143941579/57F (b/581 offsets in scan), 0x144098D77/D8A, 0x1440BB3AC/3C2. None lies in 0x1440A1DC0. So `UNITS: METRIC` does not feed the field: lane AA is right, lane P wrong on this point.
* Refinement: the flag `[ctx+0x2AC098]` is also written elsewhere: 0x14393B75C/778 set it to 2 or 3 (entity parser, 3 when a char code is in 0x54..0x57), and 0x1440BB3C0 overwrites it from a user option `[this+0x104]` when nonzero. The scale branch is taken only when flag == 1, i.e. when `$INSUNITS` was parsed and not overridden. With flag != 1, +0x88 is not set at this site (default set elsewhere, not traced).
* Builder scale (0x144098D7E..): `[rbx+0x88]` = 1.0 (0x3F800000) default; code 1 -> 0x41CB3333 (25.4f); code 5 -> 0x41200000 (10.0f); code 6 -> 0x447A0000 (1000.0f); anything else (including 4 = mm and 0) stays 1.0. Applied per piece via 0x40a1590 (xmm1 = scale), pieces stride 0x250. Matches the claim exactly.

## 2. CRT statics and frame constants
* 0x70d98d8 (header): AcquireSRWLockExclusive (lock 0x14A35EA18, IAT 0x14822BA10); loop: `*guard==0` -> `*guard=-1` (in progress) and go to release; `*guard==-1` -> SleepConditionVariableSRW (IAT 0x14822BA28) and retry; otherwise (already initialised) copies global epoch `[0x14A172D8C]` into the TLS slot (`gs:[0x58]`, `[0x14A35EA20]` tls_index*8, offset 0xB8B8 = `_Init_thread_epoch`); ReleaseSRWLockExclusive (IAT 0x14822BA08).
* 0x70d986c (footer): acquire lock; `++[0x14A172D8C]` (`_Init_global_epoch`); `*guard = epoch`; TLS epoch = epoch; release; tail `jmp WakeAllConditionVariable` (IAT 0x14822BB10). Names resolved from the import hint/name table. VERIFIED. (The `jmp [0x14822BB10]` at 0x70d9863 is the tail of the preceding function, a different one.)
* 0x5cbfda0 (RVA; function is long, tail at 0x145CC0A40-0x145CC0AC3):
  * Arm: 0x145CBFF44 `mov byte [r15+34h],1`; 0x145CBFF49 `mov dword [r15+38h],0`, executed only if `r14b` is set at 0x145CBFF3F.
  * 0x145CC0059 `mov edi,0Ah`, or 0x145CC0131-0x145CC0136 `neg r14b; sbb edi,edi; and edi,0Ah` -> edi = 10 or 0; 0x145CC0139 `lea r12d,[rdi+28h]` -> r12d = 50 or 40.
  * Frame `[r15+38h] < edi` -> Folding branch (label "Folding" at 0x14895F5A0; percent = frame*100/r12d at 0x145CC0565); `edi <= frame < r12d` -> Draping (label "Draping" at 0x14895F5A8, 0x145CC09DB-0x145CC09ED); each branch does `inc [r15+38h]` (0x145CC05CA / 0x145CC0A40); `frame >= r12d` (0x145CC05FE cmp/jae to 0x145CC0A6D) ends the phase and sets `[r15+34h]=0` (0x145CC0ABE).
  * UNVERIFIED: the predicate behind r14b / edi (the claimed "foldable item exists" and the conditions that re-arm) was not traced.
  * Literal immediates 9 and 50 do not occur: frames 0-9 is `< 10`; 50 is 10 + 0x28 computed.

## 3. Male preset files (`Preset\Avatar\Resizing\Male\`)
| file | bytes | header (LE int32 x2) | 8 + rows*cols*4 |
|---|---|---|---|
| PCA_weight.bd | 56,991,608 | 142479, 100 | 8 + 56,991,600 exact |
| ReducedVertexData.bd | 752,808 | 100, 1882 | 8 + 752,800 exact |
| FeatureData.bd | 436,632 | 58, 1882 | 8 + 436,624 exact |
* The files are not exactly rows*cols*4: each has an 8-byte header (int32 rows, int32 cols) that self-describes the shape and confirms the claimed dimensions. 142479 = 3 x 47,493. Float32 payload is size-consistent (not decoded further here).

## 4. Indirect calls in the .avt loader range 0x50f5c00-0x50f8e71 (RVA)
2794 instructions scanned (no indirect `jmp` in the range). 47 non-direct `call` operands:
* 44 are `call qword ptr [IAT]`: 0x148230078 (`QObject::tr`), 0x1482300E8 (`QString` copy ctor), 0x1482300E0 (`~QString`), 0x148237590 (`_invalid_parameter_noinfo_noreturn`). None virtual.
* 3 genuine indirect (virtual) calls:
  1. 0x1450F5FD1 `call r10`, r10 = `[vptr+0x308]` of the object at `[rbp-78h]` (loaded at 0x1450F5FA8).
  2. 0x1450F6613 `call qword ptr [rax+0C8h]` (rax = vptr of r14).
  3. 0x1450F668E `call qword ptr [rax+238h]` (same r14 object).
* Suggested wording: "no direct call path; 3 virtual calls (vtable offsets 0x308, 0xC8, 0x238) remain unresolved, so an indirect path cannot be excluded". Targets were not resolved here.

## 5. AddSeamlinePairGroupPartial (0x5f94e20, RVA)
Early-exit order:
1. 0x145F94E6B `call 0x60fdf00(xmm0=param4, xmm1=[rbp+70h])`; `test eax,eax; jne` to epilogue returning eax (0x145F94E72 -> 0x145F951CE).
2. 0x145F94E90 same validator on ([rbp+90h],[rbp+98h]) (jne at 0x145F94E97).
3. Only then 0x145F94E9D `call 0x1bf5e20`, 0x5cfe9f0, 0x1d68be0(0,..); `test al,al; je` continue, else `edi=esi=-1` and return -1 (0x145F94EBE-0x145F94EC5).
* Validator 0x60fdf00 (0x1460FDF00): returns -5 (0xFFFFFFFB) if either float is NaN/Inf, <0, or >1.0 (constant 0x1482703F8 = 1.0f); returns -6 (0xFFFFFFFA) if a >= b (comiss/cmovae); else 0.
* VERIFIED: -5/-6 precede the -1 check. Also -2 (0xFFFFFFFE) is set at 0x145F95121, after the -1 check, when the 0x3e72d80 tests fail.

## Corrections list
1. Lane P is wrong that the `UNITS:` annotation sets the unit code; lane AA is right (`$INSUNITS` via atoi in 0x39423d0).
2. Store at 0x14394157F is the "valid" flag `[ctx+0x2AC098]=1`, not part of the unit code. The scale applies only if that flag == 1; the flag is also set 2/3 at 0x14393B75C/778, overridden by a user option at 0x1440BB3C0, and the constructor zeroes both fields.
3. Lane X: "frames 0-9" and "50/40" are derived (edi = 10/0; r12d = edi + 40), not literal immediates; the foldable predicate is not verified.
4. Lane W: sizes include an 8-byte (rows, cols) header; rows*cols*4 is 8 bytes short for each file.
5. Lane K/M2: wording should be "3 indirect calls remain (vtable +0x308, +0xC8, +0x238)".
6. Lane I: confirmed; add that -5/-6 come from validator 0x60fdf00 (range [0,1], NaN/Inf rejected, a < b required).
