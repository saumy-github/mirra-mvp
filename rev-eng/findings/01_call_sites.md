# Call sites in clo_workspace/windows/RestPlugin_windows.cpp

```
269:    try { count = PATTERN_API->GetPatternCount(); }
298:            FABRIC_API->SetFabricPBRMaterialBaseColor(
319:            FABRIC_API->SetBaseTextureMapImageGivenFilePath(p->path, p->fabric_idx);
400:            FABRIC_API->SetFabricPBRMaterialBaseColor(
416:            FABRIC_API->SetBaseTextureMapImageGivenFilePath(path, fabric_idx);
472:    auto list = PATTERN_API->GetArrangementList();
482:    try { count = PATTERN_API->GetPatternCount(); } catch (...) {}
485:        auto info = PATTERN_API->GetArrangementOfPattern(i);
618:    return !EXPORT_API->ExportAVT(*pathIn).empty();
1718:                asyncResult.success  = IMPORT_API->ImportOBJ(cmd.param1, options);
1757:                    asyncResult.success = IMPORT_API->ImportFile(cmd.param1);
1759:                    asyncResult.success = IMPORT_API->ImportFile(cmd.param1, options);
1761:                    asyncResult.success = IMPORT_API->ImportAvatar(cmd.param1, options);
1782:                    measurementOk = IMPORT_API->ImportAvatarMeasurement(cmd.param1, cmd.param2, options);
1785:                    measurementOk = IMPORT_API->ImportMeasurement(cmd.param1);
1809:                        debugState.properties_before = UTILITY_API->GetAvatarProperties(debugState.avatar_index);
1813:                    UTILITY_API->SetAvatarProperties(debugState.avatar_index, cmd.stringMapParam1);
1816:                        debugState.properties_after = UTILITY_API->GetAvatarProperties(debugState.avatar_index);
1861:                asyncResult.success = IMPORT_API->ImportDXF(cmd.param1, options);
1888:                try { patternCountNow = PATTERN_API->GetPatternCount(); } catch (...) {}
1899:                asyncResult.success = PATTERN_API->AddSeamlinePairGroup(
1914:                asyncResult.success = UTILITY_API->Simulate((unsigned int)cmd.param3);
1943:                    ? EXPORT_API->ExportGLB(cmd.param1, options)
1944:                    : EXPORT_API->ExportGLTF(cmd.param1, options, false);
1956:                int group = PATTERN_API->AddGradingSizeGroup(cmd.boolParam1);
1961:                    paired = PATTERN_API->SetGradingPairedAvatarFromFile(0, cmd.param1);
1965:                bool sized = PATTERN_API->SetGradingPairedAvatarSizing(0, cmd.param2);
1973:                UTILITY_API->NewProject();
2009:                    deleted = UTILITY_API->DeleteAvatar(indices);
2027:                    PATTERN_API->SetArrangement(cmd.param3, cmd.param4);
2028:                PATTERN_API->SetArrangementPosition(
2035:                    PATTERN_API->SetArrangementOrientation(cmd.param3, cmd.param5);
2045:                PATTERN_API->SetPatternPieceFabricIndex(cmd.param3, cmd.param4);
2065:                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
2093:                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
2116:                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
2129:                std::string out = EXPORT_API->ExportZPrj(cmd.param1, thumb);
2150:                try { cnt = PATTERN_API->GetPatternCount(); ok = true; } catch (...) {}
2156:                try { total = PATTERN_API->GetPatternCount(); } catch (...) {}
2168:                    try { raw = PATTERN_API->GetPatternInformation(idx); cloOk = true; } catch (...) {}
2185:                    auto raw = PATTERN_API->GetBoundingBoxOfPattern(patternIndex);
2190:                try { area = PATTERN_API->GetPatternPieceArea(patternIndex); } catch (...) {}
2202:                try { inputInfo = PATTERN_API->GetPatternInputInformation(patternIndex); cloOk = true; } catch (...) {}
2227:                    try { len = PATTERN_API->GetLineLength(patternIndex, i); }
2249:                    auto list = PATTERN_API->GetArrangementList();
2267:                try { count = PATTERN_API->GetPatternCount(); } catch (...) {}
2271:                        auto info = PATTERN_API->GetArrangementOfPattern(i);
2294:                try { patternCount = PATTERN_API->GetPatternCount(); } catch (...) {}
2297:                    auto slotList = PATTERN_API->GetArrangementList();
2303:                        auto rec = PATTERN_API->GetArrangementOfPattern(i);
2345:                try { patternCount = PATTERN_API->GetPatternCount(); } catch (...) {}
2347:                    auto list = PATTERN_API->GetArrangementList();
2360:                        auto rec = PATTERN_API->GetArrangementOfPattern(i);
2378:                try { avatarCount   = EXPORT_API->GetAvatarCount();    } catch (...) {}
2379:                try { avatarNames   = EXPORT_API->GetAvatarNameList();  } catch (...) {}
2380:                try { avatarGenders = EXPORT_API->GetAvatarGenderList(); } catch (...) {}
2384:                    try { properties = UTILITY_API->GetAvatarProperties(i); } catch (...) {}
2489:        UTILITY_API->DisplayMessageBox("Starting REST server on http://localhost:50505\n\nQueue drains automatically every 200 ms — no further menu clicks needed.");
2569:            UTILITY_API->DisplayMessageBox("REST server is running on http://localhost:50505\n\nNo commands in queue.\n\nQueue commands via REST API, then click this menu item again to execute th
2576:        UTILITY_API->DisplayMessageBox(msg.c_str());
2580:        UTILITY_API->DisplayMessageBox("Unknown error occurred");
```
