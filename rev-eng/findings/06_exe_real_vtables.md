# Real (derived) vtables in the CLO exe

*Status: static analysis, CLO_Standalone_OnlineAuth_x64.exe 2026.1.336*
*Date: 2026-10-29*

RTTI found `Marvelous::{Utility,Pattern,Fabric,Import,Export,Gui,Rest}API` deriving from `CLOAPI::*APIInterface`. Slot numbers from `findings/04` apply 1:1 (slot == declaration index in the SDK header, verified on every named base slot). RVA = image offset (VA = 0x140000000 + RVA). `jmp` = slot is an E9 thunk to the shown RVA. Derived vtables of Utility/Pattern/Gui carry one extra trailing slot (the derived scalar-deleting dtor).

| Derived class | vtable RVA | slots |
|---|---|---|
| ExportAPI@Marvelous | 0x89687b8 | 124 |
| UtilityAPI@Marvelous | 0x8968ba0 | 409 |
| FabricAPI@Marvelous | 0x89770d8 | 285 |
| GuiAPI@Marvelous | 0x89866a0 | 40 |
| ImportAPI@Marvelous | 0x8989348 | 45 |
| PatternAPI@Marvelous | 0x898ba50 | 234 |
| RestAPI@Marvelous | 0x899ae98 | 11 |

| API | Function | Slot | Exe RVA | Source | First instructions |
|---|---|---|---|---|---|
| EXPORT | ExportAVT | 102 | 0x5fb2740 | 04 | `48895c240855565741564157` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| EXPORT | ExportGLB | 78 | 0x5fb75d0 | 04 | `405553565741544156415748` push rbp; push rbx; push rsi; push rdi |
| EXPORT | ExportGLTF | 13 | 0x5fb7f50 | 04 | `48895c240855565741544155` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| EXPORT | ExportZPrj | 4 | 0x5fcb040 | 04 | `405553565741544156415748` push rbp; push rbx; push rsi; push rdi |
| EXPORT | ExportZPrj | 5 | 0x5fcae00 | 04 | `48895c240855565741564157` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| EXPORT | ExportZPrj | 6 | 0x5fcb290 | 04 | `48895c240848897424185557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; push rbp; push rdi |
| EXPORT | GetAvatarCount | 71 | 0x5fd3920 | 04 | `48895c240848897424104889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+10h],rsi; mov qword ptr [rsp+18h],rdi; push rbp |
| EXPORT | GetAvatarGenderList | 74 | 0x5fd3d20 | 04 | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| EXPORT | GetAvatarNameList | 72 | 0x5fd4880 | 04 | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| FABRIC | GetFabricIndexForPattern | 50 | 0x5fe4d90 | 04 | `48895c240855565741564157` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| FABRIC | GetFabricIndexForPattern | 51 | 0x5fe4a50 | 04 | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| IMPORT | ImportAvatar | 37 | 0x6021080 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| IMPORT | ImportAvatarMeasurement | 36 | 0x6021400 | 04 | `405553565741554156415748` push rbp; push rbx; push rsi; push rdi |
| IMPORT | ImportDXF | 21 | 0x6021f40 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| IMPORT | ImportFile | 1 | 0x6022e80 | 04 | `48895c2408555657488d6c24` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| IMPORT | ImportFile | 2 | 0x6022a80 | 04 | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| IMPORT | ImportMeasurement | 38 | 0x6025560 | 04 | `48895c240848897c24185548` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rdi; push rbp; lea rbp,[rsp-57h] |
| IMPORT | ImportOBJ | 11 | 0x6025820 | 04 | `48895c2408555657488d6c24` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| PATTERN | AddGradingSizeGroup | 202 | 0x648f127 | 04 | `ff25e3c3d901ff25d5c3d901` jmp qword ptr [000000014822B510h]; jmp qword ptr [000000014822B508h]; jmp qword ptr [000000014822B500h]; jmp qword ptr [000000014822B4F8h] |
| PATTERN | AddSeamlinePairGroup | 161 | 0x5f93d70 | 04 | `48895c240848897424104889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+10h],rsi; mov qword ptr [rsp+18h],rdi; push rbp |
| PATTERN | AddSeamlinePairGroup | 162 | 0x5f94000 | 04 | `48895c240848897424104889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+10h],rsi; mov qword ptr [rsp+18h],rdi; push rbp |
| PATTERN | AddSeamlinePairGroup | 163 | 0x5f942d0 | 04 | `488bc4488958084889701048` mov rax,rsp; mov qword ptr [rax+8],rbx; mov qword ptr [rax+10h],rsi; mov qword ptr [rax+18h],rdi |
| PATTERN | GetArrangementList | 34 | 0x5fd2880 | 04 | `48895c241855565741544155` mov qword ptr [rsp+18h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetArrangementOfPattern | 35 | 0x5fd2cc0 | 04 | `48895c242055565741564157` mov qword ptr [rsp+20h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetArrangementOfPattern | 36 | 0x5fd2ef0 | 04 | `405355565741564881eca000` push rbx; push rbp; push rsi; push rdi |
| PATTERN | GetArrangementOfPattern | 37 | 0x5fd3120 | 04 | `48895c241855565741544155` mov qword ptr [rsp+18h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetBoundingBoxOfPattern | 24 | 0x5fd9230 | 04 | `48895c242055565741564157` mov qword ptr [rsp+20h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetBoundingBoxOfPattern | 25 | 0x5fd9460 | 04 | `48895c240848896c24205657` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rbp; push rsi; push rdi |
| PATTERN | GetBoundingBoxOfPattern | 26 | 0x5fd96a0 | 04 | `48895c241855565741544155` mov qword ptr [rsp+18h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetLineLength | 13 | 0x5ff3750 | 04 | `488bc4555356574156415748` mov rax,rsp; push rbp; push rbx; push rsi |
| PATTERN | GetLineLength | 14 | 0x5ff3470 | 04 | `488bc4555356574156488d68` mov rax,rsp; push rbp; push rbx; push rsi |
| PATTERN | GetPatternCount | 7 | 0x6001e40 | 04 | `48895c2408574881ec900000` mov qword ptr [rsp+8],rbx; push rdi; sub rsp,90h; mov rax,qword ptr [000000014A172D40h] |
| PATTERN | GetPatternInformation | 5 | 0x6005520 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| PATTERN | GetPatternInputInformation | 8 | 0x6005cf0 | 04 | `48895c241848897424205557` mov qword ptr [rsp+18h],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| PATTERN | GetPatternInputInformation | 9 | 0x6005ad0 | 04 | `48895c242055565741564157` mov qword ptr [rsp+20h],rbx; push rbp; push rsi; push rdi |
| PATTERN | GetPatternPieceArea | 12 | 0x6008bb0 | 04 | `488bc4488958084889701848` mov rax,rsp; mov qword ptr [rax+8],rbx; mov qword ptr [rax+18h],rsi; mov qword ptr [rax+20h],rdi |
| PATTERN | SetArrangement | 43 | 0x603d060 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| PATTERN | SetArrangementOrientation | 42 | 0x603d4f0 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| PATTERN | SetArrangementPosition | 41 | 0x603d730 | 04 | `48895c240855565741544156` mov qword ptr [rsp+8],rbx; push rbp; push rsi; push rdi |
| PATTERN | SetGradingPairedAvatarFromFile | 205 | 0x648f139 | 04 | `ff25b9c3d901ff25abc3d901` jmp qword ptr [000000014822B4F8h]; jmp qword ptr [000000014822B4F0h]; jmp qword ptr [000000014822B4E8h]; jmp qword ptr [000000014822B4E0h] |
| PATTERN | SetGradingPairedAvatarSizing | 204 | 0x648f133 | 04 | `ff25c7c3d901ff25b9c3d901` jmp qword ptr [000000014822B500h]; jmp qword ptr [000000014822B4F8h]; jmp qword ptr [000000014822B4F0h]; jmp qword ptr [000000014822B4E8h] |
| PATTERN | SetPatternPieceFabricIndex | 62 | 0x6064db0 | 04 | `48895c240848897424205557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| UTILITY | DeleteAvatar | 264 | 0x5fad0e0 | 04 | `48895c240848897424185557` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; push rbp; push rdi |
| UTILITY | DisplayMessageBox | 2 | 0x5fb0260 | 04 | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| UTILITY | NewProject | 55 | 0x60342c0 | 04 | `48895c240855488d6c24a948` mov qword ptr [rsp+8],rbx; push rbp; lea rbp,[rsp-57h]; sub rsp,90h |
| UTILITY | Simulate | 85 | 0x607f070 | 04 | `48895c240848897424105748` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+10h],rsi; push rdi; sub rsp,0A0h |
| UTILITY | GetAvatarProperties | 350 | 0x5fd59f0 | header order | `48895c240848897424184889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+18h],rsi; mov qword ptr [rsp+20h],rdi; push rbp |
| UTILITY | SetAvatarProperties | 349 | 0x6041900 | header order | `48895c240848897424104889` mov qword ptr [rsp+8],rbx; mov qword ptr [rsp+10h],rsi; mov qword ptr [rsp+18h],rdi; push rbp |
| FABRIC | SetFabricPBRMaterialBaseColor | 113 | 0x604e000 | header order | `488bc4555356574154415641` mov rax,rsp; push rbp; push rbx; push rsi |
| FABRIC | SetFabricPBRMaterialBaseColor | 114 | 0x604dcb0 | header order | `488bc4555356574156415748` mov rax,rsp; push rbp; push rbx; push rsi |
| FABRIC | SetFabricPBRMaterialBaseColor | 115 | 0x604e350 | header order | `405553565741544156415748` push rbp; push rbx; push rsi; push rdi |
| FABRIC | SetFabricPBRMaterialBaseColor | 116 | 0x604e5e0 | header order | `405553565741564157488d6c` push rbp; push rbx; push rsi; push rdi |
| FABRIC | SetBaseTextureMapImageGivenFilePath | 205 | 0x60119b0 | header order | `405553565741544156415748` push rbp; push rbx; push rsi; push rdi |
| FABRIC | SetBaseTextureMapImageGivenFilePath | 217 | 0x605c2a0 | header order | `48895c242055565741564157` mov qword ptr [rsp+20h],rbx; push rbp; push rsi; push rdi |
| FABRIC | SetBaseTextureMapImageGivenFilePath | 218 | 0x605c020 | header order | `48895c241848897424205557` mov qword ptr [rsp+18h],rbx; mov qword ptr [rsp+20h],rsi; push rbp; push rdi |
| FABRIC | SetBaseTextureMapImageGivenFilePath | 247 | 0x606bca0 | header order | `405553565741564157488d6c` push rbp; push rbx; push rsi; push rdi |

Notes: slots resolved by header order = declaration index, confirmed by neighbours (Utility 346/352 named, Get/SetAvatarProperties are decl 349/350; Fabric overload groups are contiguous in declaration order, as for GetFabricIndexForPattern 50,51).
