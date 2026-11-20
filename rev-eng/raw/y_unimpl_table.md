| # | Class | Slot | Function (SDK 336 header signature) | Thunk RVA | IAT RVA | Base stub body |
|---|---|---|---|---|---|---|
| 1 | Pattern | 196 | `bool SetGradingPairedAvatar(unsigned int _gradingIndex, const std::string& _avatarName)` | 0x648f103 | 0x822b540 | xor al,al; ret -> false |
| 2 | Pattern | 197 | `std::vector<std::vector<float>> GetGraphicGradingScaleRatios(int _graphicStyleIndex, int _patternIndex)` | 0x648f109 | 0x822b538 | returns empty vector |
| 3 | Pattern | 198 | `std::vector<std::vector<float>> GetGraphicGradingPositionOffsets(int _graphicStyleIndex, int _patternIndex)` | 0x648f10f | 0x822b530 | returns empty vector |
| 4 | Pattern | 199 | `bool SetGraphicGradingScaleRatios(int _graphicStyleIndex, int _patternIndex, const std::vector<std::vector<float>>& _scaleRatios)` | 0x648f115 | 0x822b528 | xor al,al; ret -> false |
| 5 | Pattern | 200 | `bool SetGraphicGradingPositionOffsets(int _graphicStyleIndex, int _patternIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f11b | 0x822b520 | xor al,al; ret -> false |
| 6 | Pattern | 201 | `bool AddGradingSize(unsigned int _gradingSizeGroupIndex, const std::string& _newSizeName)` | 0x648f121 | 0x822b518 | xor al,al; ret -> false |
| 7 | Pattern | 202 | `int AddGradingSizeGroup(bool _bAssignToAllPatterns)` | 0x648f127 | 0x822b510 | mov eax,-1; ret -> -1 |
| 8 | Pattern | 203 | `bool ImportGradeRuleToSizeGroup(unsigned int _gradingSizeGroupIndex, const std::string& _rulFilePath)` | 0x648f12d | 0x822b508 | xor al,al; ret -> false |
| 9 | Pattern | 204 | `bool SetGradingPairedAvatarSizing(unsigned int _gradingIndex, const std::string& _avsFilePath)` | 0x648f133 | 0x822b500 | xor al,al; ret -> false |
| 10 | Pattern | 205 | `bool SetGradingPairedAvatarFromFile(unsigned int _gradingIndex, const std::string& _avtFilePath)` | 0x648f139 | 0x822b4f8 | xor al,al; ret -> false |
| 11 | Pattern | 206 | `bool CutPatternAlongInternalShapes(int _patternIndex, int _internalShapeIndex, bool _bCutAndSew)` | 0x648f13f | 0x822b4f0 | xor al,al; ret -> false |
| 12 | Pattern | 207 | `bool MergeSewnPatterns(int _patternIndexA, int _patternIndexB)` | 0x648f145 | 0x822b4e8 | xor al,al; ret -> false |
| 13 | Pattern | 208 | `std::vector<std::vector<float>> GetPatternInternalShapePoints(int _patternIndex, int _internalShapeIndex)` | 0x648f14b | 0x822b4e0 | returns empty vector |
| 14 | Pattern | 209 | `std::vector<std::vector<float>> GetPatternBaselinePoints(int _patternIndex, int _baselineIndex)` | 0x648f151 | 0x822b4d8 | returns empty vector |
| 15 | Pattern | 210 | `bool AddButtonToPattern(int _patternIndex, float _x, float _y, float _angleDegree)` | 0x648f157 | 0x822b4d0 | xor al,al; ret -> false |
| 16 | Pattern | 211 | `bool AddButtonHoleToPattern(int _patternIndex, float _x, float _y, float _angleDegree)` | 0x648f15d | 0x822b4c8 | xor al,al; ret -> false |
| 17 | Pattern | 212 | `bool TraceBaselineAsInternalShape(int _patternIndex, int _baselineIndex)` | 0x648f163 | 0x822b4c0 | xor al,al; ret -> false |
| 18 | Pattern | 213 | `std::vector<std::vector<float>> GetButtonGradingPositionOffsets(int _buttonIndex)` | 0x648f169 | 0x822b4b8 | returns empty vector |
| 19 | Pattern | 214 | `bool SetButtonGradingPositionOffsets(int _buttonIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f16f | 0x822b4b0 | xor al,al; ret -> false |
| 20 | Pattern | 215 | `std::vector<std::vector<float>> GetButtonHoleGradingPositionOffsets(int _buttonHoleIndex)` | 0x648f175 | 0x822b4a8 | returns empty vector |
| 21 | Pattern | 216 | `bool SetButtonHoleGradingPositionOffsets(int _buttonHoleIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f17b | 0x822b4a0 | xor al,al; ret -> false |
| 22 | Pattern | 217 | `bool ActivateAllPatterns(bool _bActivate, bool _bIncludeSewing)` | 0x648f181 | 0x822b498 | xor al,al; ret -> false |
| 23 | Pattern | 218 | `std::vector<std::vector<float>> GetPatternOutlinePoints(int _patternIndex)` | 0x648f187 | 0x822b490 | returns empty vector |
| 24 | Pattern | 219 | `std::vector<std::vector<float>> GetPatternPointGradingPositionOffsets(int _patternIndex, int _pointIndex)` | 0x648f18d | 0x822b488 | returns empty vector |
| 25 | Pattern | 220 | `bool SetPatternPointsGradingPositionOffsets(int _patternIndex, const std::vector<int>& _pointIndices, const std::vector<std::vector<float>>& _offsets)` | 0x648f193 | 0x822b480 | xor al,al; ret -> false |
| 26 | Utility | 388 | `std::string RemoveGraphicStyle(int _graphicIndex)` | 0x648f0e5 | 0x822b568 | NOT a dead stub: reads colorway via vslot 16 then virtual-calls slot 387 (see sect. 3) |
| 27 | Utility | 397 | `void SetAssetShareRoot(const std::string& _shareRoot)` | 0x648f0eb | 0x822b560 | ret (void no-op) |
| 28 | Utility | 398 | `std::string GetAssetShareRoot()` | 0x648f0f1 | 0x822b558 | returns empty string |
| 29 | Utility | 399 | `void SetBasePath(const std::string& _basePath)` | 0x648f0f7 | 0x822b550 | ret (void no-op) |
| 30 | Utility | 400 | `std::string GetBasePath()` | 0x648f0fd | 0x822b548 | returns empty string |
