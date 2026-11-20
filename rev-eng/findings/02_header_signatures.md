# Header declarations (SDK 336) for plugin-used functions


## AddGradingSizeGroup

`PatternAPIInterface.h:1853`
```cpp
		/// @ingroup PATTERN_API
		/// @fn AddGradingSizeGroup(bool _bAssignToAllPatterns)
		/// @brief Create a new grading rule group (rule table) holding a single default size — the API equivalent of the GUI 'Add (And Assign) Grading Rule Table' button in Object Browser - Grading. Use it to start grading on a garment that has none, then append sizes with AddGradingSize or load a .rul file with ImportGradeRuleToSizeGroup.
		/// @param _bAssignToAllPatterns: when true, assign every pattern piece to the new group (the headless equivalent of selecting all patterns before the GUI 'Add And Assign'); when false, only create the table
		/// @note In a GUI session the grading-related widgets (Object Browser - Grading, property panels) are not refreshed automatically by this API.
		/// @note Unlike the GUI, which auto-pairs the first visible scene avatar into the empty avatar slots of a new rule table, the table created here starts with all avatar slots empty (intentional — pair explicitly via SetGradingPairedAvatar / SetGradingPairedAvatarFromFile).
		/// @return the new grading size group index (0-based); -1 on failure (no pattern editor)
		virtual int AddGradingSizeGroup(bool _bAssignToAllPatterns) { return -1; }
```

## AddSeamlinePairGroup

`PatternAPIInterface.h:1317`
```cpp
		/// @ingroup PATTERN_API
		/// @fn AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _lineBIndex, bool _bReverse)
		/// @brief Add Pattern and Sewing between Pattern
		/// @return name of sewing group(wide string)
		/// @param _patternAIndex : A pattern index
		/// @param _lineAIndex : The index of the line that belongs to the A pattern.
		/// @param _patternBIndex : B pattern index
		/// @param _lineBIndex : The index of the line that belongs to the B pattern.
		/// @param _directionA : The direction of the stitching, true : forward, false : backward
		/// @param _directionB : The direction of the stitching, true : forward, false : backward
		virtual bool AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _lineBIndex, bool _directionA, bool _directionB) { return false; }
```
`PatternAPIInterface.h:1330`
```cpp
		/// @ingroup PATTERN_API
		/// @fn AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _lineBIndex, bool _directionA, bool _directionB)
		/// @brief Add Patterns and Sewing between InnerShape
		/// @return name of sewing group(wide string)
		/// @param _patternAIndex : A pattern index
		/// @param _lineAIndex : The index of the line that belongs to the A pattern.
		/// @param _patternBIndex : B pattern index
		/// @param _childIndex : The index of the innershape that belongs to the B pattern.
		/// @param _lineBIndex : The index of the line that belongs to the innerShape.
		/// @param _directionA : The direction of the stitching, true : forward, false : backward
		/// @param _directionB : The direction of the stitching, true : forward, false : backward
		virtual bool AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _childIndex, int _lineBIndex, bool _directionA, bool _directionB) { return false; }
```
`PatternAPIInterface.h:1344`
```cpp
		/// @ingroup PATTERN_API
		/// @fn AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _lineBIndex, bool _directionA, bool _directionB)
		/// @brief Add InnerShape and Sewing between InnerShape
		/// @return name of sewing group(wide string)
		/// @param _patternAIndex : A pattern index
		/// @param _childAIndex : The index of the innershape that belongs to the A pattern.
		/// @param _lineAIndex : The index of the line that belongs to the innerShape.
		/// @param _patternBIndex : B pattern index
		/// @param _childBIndex : The index of the innershape that belongs to the B pattern.
		/// @param _lineBIndex : The index of the line that belongs to the innerShape.
		/// @param _directionA : The direction of the stitching, true : forward, false : backward
		/// @param _directionB : The direction of the stitching, true : forward, false : backward
		virtual bool AddSeamlinePairGroup(int _patternAIndex, int _childAIndex, int _lineAIndex, int _patternBIndex, int _childBIndex, int _lineBIndex, bool _directionA, bool _directionB) { return false; }
```

## DeleteAvatar

`UtilityAPIInterface.h:1998`
```cpp
		/// @ingroup UTILITY_API
		/// @fn DeleteAvatar(std::vector<int> _avatarIndexList)
		/// @brief Delete Avatars
		/// @param _avatarIndexList: List of indices for avatars to delete
		virtual bool DeleteAvatar(std::vector<int> _avatarIndexList) { return 0; }
```

## DisplayMessageBox

`UtilityAPIInterface.h:34`
```cpp
		/// @ingroup UTILITY_API
		/// @fn DisplayMessageBox(string str)
		/// @brief Show a message with using the DialogBox implemented in CLO software
		/// @param str: message
		/// @return Display a message box to show input string on CLO. This can be used for debugging.
		virtual void DisplayMessageBox(std::string str) {}
```

## ExportAVT

`ExportAPIInterface.h:936`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportAVT(const string& _filePath)
		/// @brief Export AVT
		/// @param _filePath: output file path
		/// @return Output file path. If an error occurs, return empty string. 
		virtual std::string ExportAVT(const std::string& _filePath) { return ""; }
```

## ExportGLB

`ExportAPIInterface.h:715`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportGLB(const string& _filePath, const Marvelous::ImportExportOption& _options)
		///	@brief Export GLB
		///	@param options: If "options" is given, it exports GLB according to options, not allowing user for selecting options in Export Dialog.
		///	@return Output file paths. 
		virtual std::vector<std::string> ExportGLB(const std::string& _filePath, const Marvelous::ImportExportOption& _options)
```

## ExportGLTF

`ExportAPIInterface.h:134`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportGLTF(const string& _filePath, const Marvelous::ImportExportOption& _options, bool _bGLBinary)
		///	@brief Export GLTF. The export can be restricted to specific components through the component selection lists
		///	       on _options (patternList / buttonList / graphicList / zipperList): when at least one of them is set,
		///	       ONLY the listed components are written, so a project holding several garments can be exported one file
		///	       per garment. With every list empty (the default) the whole scene is exported, as before.
		///	@param options: If "options" is given, it exports GLTF according to options, not allowing user for selecting options in Export Dialog.
		///	@param _bGLBinary: if true, export binary glTF (.glb); otherwise text glTF.
		///	@return Output file paths.
		virtual std::vector<std::string> ExportGLTF(const std::string& _filePath, const Marvelous::ImportExportOption& _options, bool _bGLBinary)
```

## ExportZPrj

`ExportAPIInterface.h:43`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportZPrj()
		/// @brief Export ZPrj file 
		/// @return Output file path; output files will be created in CLO temporary folder.
		virtual std::string ExportZPrj() { return ""; }
```
`ExportAPIInterface.h:50`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportZPrj(const string& _filePath)
		/// @brief Export ZPrj file 
		/// @param _filePath: output file path
		/// @return Output file path. If an error occurs, return empty string.
		virtual std::string ExportZPrj(const std::string& _filePath) { return ""; }
```
`ExportAPIInterface.h:58`
```cpp
		/// @ingroup EXPORT_API
		/// @fn ExportZPrj(const string& _filePath, bool _bCreateThumbnail)
		/// @brief Export ZPrj file 
		/// @param _filePath: output file path
		/// @param _bCreateThumbnail: if _bCreateThumbnail is true, 'png' file will be created along 'zprj' file.
		/// @return Output file path. If an error occurs, return empty string.
		virtual std::string ExportZPrj(const std::string& _filePath, bool _bCreateThumbnail) { return ""; }
```

## GetArrangementList

`PatternAPIInterface.h:321`
```cpp
		virtual std::vector<std::map<std::string, std::string>> GetArrangementList()
```

## GetArrangementOfPattern

`PatternAPIInterface.h:333`
```cpp
		virtual std::vector<std::map<std::string, std::string>> GetArrangementOfPattern()
```
`PatternAPIInterface.h:345`
```cpp
		virtual std::map<std::string, std::string> GetArrangementOfPattern(int _patternIndex)
```
`PatternAPIInterface.h:357`
```cpp
		virtual std::map<std::string, std::string> GetArrangementOfPattern(const std::string& _patternName)
```

## GetAvatarCount

`ExportAPIInterface.h:637`
```cpp
		/// @ingroup EXPORT_API
		/// @fn GetAvatarCount()
		/// @brief Get the number of avatars loaded in CLO
		/// @return total count of avatars		
		virtual unsigned int GetAvatarCount() { return 0; }
```

## GetAvatarGenderList

`ExportAPIInterface.h:663`
```cpp
		/// @ingroup EXPORT_API
		/// @fn GetAvatarGenderList()
		/// @brief Get all the genders of avatars loaded in CLO repectively
		/// @return the list of gender of all avatars. 0 : male, 1 : female, -1: unknown
		virtual std::vector<int> GetAvatarGenderList()
```

## GetAvatarNameList

`ExportAPIInterface.h:643`
```cpp
		/// @ingroup EXPORT_API
		/// @fn GetAvatarNameList()
		/// @brief Get all the names of avatars loaded in CLO
		/// @return the list of name of all avatars
		virtual std::vector<std::string> GetAvatarNameList()
```

## GetAvatarProperties

`UtilityAPIInterface.h:2745`
```cpp
		/// @ingroup UTILITY_API
		/// @fn GetAvatarProperties(unsigned int _avatarIndex)
		/// @brief Get multiple properties for the avatar at the specified index.
		/// @param _avatarIndex: The index of the avatar to get properties for.
		/// @return A map containing property names and their corresponding values for the avatar. Such as {'DivideMesh': 'true/false', 'KineticFriction': '0.050000', 'SkinOffsetMM': '3.000000', 'SoftBodySimulation': 'true/false', 'StaticFriction': '0.800000'}
		virtual std::map<std::string, std::string> GetAvatarProperties(unsigned int _avatarIndex) = 0;
```

## GetBoundingBoxOfPattern

`PatternAPIInterface.h:225`
```cpp
		virtual std::vector<std::map<std::string, std::string>> GetBoundingBoxOfPattern()
```
`PatternAPIInterface.h:237`
```cpp
		virtual std::map<std::string, std::string> GetBoundingBoxOfPattern(int _patternIndex)
```
`PatternAPIInterface.h:249`
```cpp
		virtual std::map<std::string, std::string> GetBoundingBoxOfPattern(const std::string& _patternName)
```

## GetFabricIndexForPattern

`FabricAPIInterface.h:418`
```cpp
		/// @ingroup FABRIC_API
		/// @fn GetFabricIndexForPattern(int patternIndex)
		/// @brief Get the fabric index which is assigned on the pattern with the pattern index
		/// @param patternIndex: the input pattern index to get the fabric index
		/// @return fabric index on the object browser for the pattern with the pattern index
		virtual int GetFabricIndexForPattern(int patternIndex) { return 0; }
```
`FabricAPIInterface.h:426`
```cpp
		/// @ingroup FABRIC_API
		/// @fn GetFabricIndexForPattern(int _patternIndex, int _colorwayIndex)
		/// @brief Get the fabric index which is assigned on the pattern with the pattern index
		/// @param	_patternIndex: the input pattern index to get the fabric index
		///			_colorwayIndex: the colorway index to get the fabric index
		/// @return fabric index on the object browser for the pattern with the pattern index and colorway index
		virtual int GetFabricIndexForPattern(int _patternIndex, int _colorwayIndex) { return 0; }
```

## GetLineLength

`PatternAPIInterface.h:108`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetLineLength()
		/// @brief Get the pattern line length which is using for pattern index and line index
		///	@return return line length
		virtual float GetLineLength(int _patternIndex, int _lineIndex) { return 0.0f; }
```
`PatternAPIInterface.h:114`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetLineLengthForInnerShape()
		/// @brief Get the pattern line length which is using for pattern index and children shape index and line index
		///	@return return line length
		virtual float GetLineLength(int _patternIndex, int _childrenIndex, int _lineIndex) { return 0.0f; }
```

## GetPatternCount

`PatternAPIInterface.h:18`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternSize()
		/// @brief Get the number of patterns
		///	@return return the number of patterns on the pattern editor and avatar window
		virtual int GetPatternSize() { return 0; } // deprecated. please use 'GetPatternCount()' function
```
`PatternAPIInterface.h:68`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternCount()
		/// @brief Get the number of patterns
		///	@return return the number of patterns on the pattern editor and avatar window
		virtual int GetPatternCount() { return 0; }
```

## GetPatternInformation

`PatternAPIInterface.h:55`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternInformation(int patternIndex)
		/// @brief Get the pattern information which is using for pattern index
		/// @param patternIndex: the pattern index to get the pattern information
		/// @return json string for pattern information
		virtual std::string GetPatternInformation(int patternIndex) { return ""; }
```

## GetPatternInputInformation

`PatternAPIInterface.h:75`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternInputInformation(int patternIndex)
		/// @brief Get the pattern input information which is using for pattern index
		/// @param patternIndex: the pattern index to get the pattern input information
		/// @return json string for pattern input information
		virtual std::string GetPatternInputInformation(int _patternIndex) { return ""; }
```
`PatternAPIInterface.h:89`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternInputInformation()
		/// @brief Get the pattern input information which is using for pattern index
		/// @param patternIndex: the pattern index to get the pattern input information
		/// @return json string for pattern input information
		virtual std::string GetPatternInputInformation() { return ""; }
```

## GetPatternPieceArea

`PatternAPIInterface.h:102`
```cpp
		/// @ingroup PATTERN_API
		/// @fn GetPatternPieceArea()
		/// @brief Get the pattern piece area which is using for pattern index
		///	@return return pattern piece
		virtual float GetPatternPieceArea(int _patternIndex) { return 0.0f; }
```

## ImportAvatar

`ImportAPIInterface.h:348`
```cpp
		/// @ingroup IMPORT_API
		///	@fn ImportAvatar(std::string _avtPath, ImportExportOption _opt)
		/// @brief Import Avatar 
		/// @param _avtPath : input Avatar file path, _opt : input load options
		virtual bool ImportAvatar(std::string _avtPath, Marvelous::ImportExportOption _opt)
```

## ImportAvatarMeasurement

`ImportAPIInterface.h:339`
```cpp
		/// @ingroup IMPORT_API
		///	@fn ImportAvatarMeasurement(std::string _csvPath, std::string _avtPath, ImportExportOption _opt)
		/// @brief Import Avatar Measurement CSV file
		/// @param _csvPath: input CSV file path, _avtPath : input Avatar file path, _opt : input load options
		virtual bool ImportAvatarMeasurement(std::string _csvPath, std::string _avtPath, Marvelous::ImportExportOption _opt)
```

## ImportDXF

`ImportAPIInterface.h:188`
```cpp
		/// @ingroup IMPORT_API
		///	@fn ImportDXF(const string& _filePath, const Marvelous::ImportDxfOption& loadOption)
		/// @brief Import DXF file
		/// @param _filePath: input file path
		/// @param loadOption: the options to load the file
		/// @return if it succeeds, return true.
		virtual bool ImportDXF(const std::string& _filePath, const Marvelous::ImportDxfOption& loadOption) { return true; }
```

## ImportFile

`ImportAPIInterface.h:27`
```cpp
		/// @ingroup IMPORT_API
		/// @fn ImportFile(const string& filePath)
		/// @brief Load File (zprj, zpac, avt, obj, fbx, zcmr). This function will show up the dialog per the file type.
		/// @param filePath: the input file path to load
		/// @return if it succeeds, return true.
		virtual bool ImportFile(const std::string& filePath) { return true; }
```
`ImportAPIInterface.h:235`
```cpp
		/// @ingroup IMPORT_API
		/// @fn ImportFile(const string& filePath, const Marvelous::ImportExportOption& _options)
		/// @brief Load File(obj, fbx, gltf) by obj type . This function will show up the dialog per the file type.
		/// @param filePath: the input file path to load, ImportExportOption - loadObjectType 0 : avater, 1 : trim
		/// @return if it succeeds, return true.
		virtual bool ImportFile(const std::string& filePath, const Marvelous::ImportExportOption& _options) { return true; }
```

## ImportMeasurement

`ImportAPIInterface.h:357`
```cpp
		/// @ingroup IMPORT_API
		///	@fn ImportMeasurement(std::string _csvPath)
		/// @brief Import Avatar Measurement CSV file
		/// @param _csvPath: input CSV file path
		virtual bool ImportMeasurement(std::string _csvPath)
```

## ImportOBJ

`ImportAPIInterface.h:86`
```cpp
		/// @ingroup IMPORT_API
		///	@fn ImportOBJ(const string& _filePath, const Marvelous::ImportExportOption& _options)
		/// @brief Import OBJ file
		/// @param _filePath: input file path
		/// @param options: If "options" is given, it imports OBJ according to options, not allowing user for selecting options in Import Dialog.
		/// @return if it succeeds, return true.
		virtual bool ImportOBJ(const std::string& _filePath, const Marvelous::ImportExportOption& _options)
```

## NewProject

`UtilityAPIInterface.h:451`
```cpp
		/// @ingroup UTILITY_API
		/// @fn NewProject()
		/// @brief Clear the current garment and begin a new garment
		virtual void NewProject() {}
```

## SetArrangement

`PatternAPIInterface.h:413`
```cpp
		virtual void SetArrangement(int _patternIndex, int _arrangementIndex) {}
```

## SetArrangementOrientation

`PatternAPIInterface.h:405`
```cpp
		virtual void SetArrangementOrientation(int _patternIndex, int _orientation) {}
```

## SetArrangementPosition

`PatternAPIInterface.h:397`
```cpp
		virtual void SetArrangementPosition(int _patternIndex, int _positionX, int _positionY, int _offset) {}
```

## SetAvatarProperties

`UtilityAPIInterface.h:2738`
```cpp
		/// @ingroup UTILITY_API
		/// @fn SetAvatarProperties(unsigned int _avatarIndex, const std::map<std::string, std::string>& avatarPropertyMap)
		/// @brief Set multiple properties for the avatar at the specified index.	
		/// @param _avatarIndex: The index of the avatar to set properties for.
		/// @param avatarPropertyMap: A map containing property names and their corresponding values to set for the avatar. Such as {'KineticFriction': '0.050000', 'SkinOffsetMM': '3.000000', 'StaticFriction': '0.800000'}
		virtual void SetAvatarProperties(unsigned int _avatarIndex, const std::map<std::string, std::string>& avatarPropertyMap) = 0;
```

## SetBaseTextureMapImageGivenFilePath

`FabricAPIInterface.h:1692`
```cpp
		/// @ingroup FABRIC_API
		/// @fn SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath)
		/// @brief Set base texture map image for current selected fabric
		/// @param _imageFilePath: image file path to set
		/// @return void
		virtual void SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath) = 0;
```
`FabricAPIInterface.h:1777`
```cpp
		/// @ingroup FABRIC_API
		/// @fn SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath, int _fabricIndex)
		/// @brief Set base texture map image for specified fabric
		/// @param _imageFilePath: image file path to set
		/// @param _fabricIndex: the target fabric index in the object browser
		/// @return void
		virtual void SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath, int _fabricIndex) = 0;
```
`FabricAPIInterface.h:1786`
```cpp
		/// @ingroup FABRIC_API
		/// @fn SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath, int _colorwayIndex, int _fabricIndex)
		/// @brief Set base texture map image for specified fabric in colorway
		/// @param _imageFilePath: image file path to set
		/// @param _colorwayIndex: target colorway index in the Colorway Editor
		/// @param _fabricIndex: the target fabric index in the Colorway Editor
		/// @return void
		virtual void SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath, int _colorwayIndex, int _fabricIndex) = 0;
```
`FabricAPIInterface.h:2044`
```cpp
		/// @ingroup FABRIC_API
		/// @fn SetBaseTextureMapImageGivenFilePath(const std::string& _imageFilePath, int _colorwayIndex, int _fabricIndex, int _styleChipIndex, int _materialFace)
		/// @brief Set base texture map image for specified fabric and material face in colorway. If an empty string is passed, the existing texture will be removed.
		/// @param _imageFilePath: image file path to set. If empty, the applied texture map will be removed from the material face.
		/// @param _colorwayIndex: target colorway index in the Colorway Editor
		/// @param _fabricIndex: the target fabric index in the Colorway Editor
		/// @param _styleChipIndex: the target style chip index in the Colorway Editor applicable if _colorwayIndex = -1, otherwise can be ignored
		/// @param _materialFace: target material face (0: Front, 1: Back, 2: Side)
		/// @return Names of other colorways that share this fabric, comma-separated. Empty string if none.
		virtual std::string SetBaseTextureMapImageGivenFilePath(const std::string& _imageFilePath, int _colorwayIndex, int _fabricIndex, int _styleChipIndex, int _materialFace) = 0;
```

## SetFabricPBRMaterialBaseColor

`FabricAPIInterface.h:942`
```cpp
		*/
		/// @ingroup FABRIC_API
		/// @fn SetFabricPBRMaterialBaseColor(unsigned int fabricIndex, unsigned int materialFace, float r, float g, float b, float a)
		/// @brief Set a base color of PBR material in a fabric using given RGBA values.
		/// @param fabricIndex: the target fabric index in the object browser to import substance file onto
		/// @param materialFace :"Front", "Back", "Side" 
		/// @param r : To be set as red value
		/// @param g : To be set as green value
		/// @param b : To be set as blue value
		/// @param a : To be set as alpha value
		/// @return if it succeeds, return true.
		virtual bool SetFabricPBRMaterialBaseColor(unsigned int fabricIndex, unsigned int materialFace, float r, float g, float b, float a) = 0;
```
`FabricAPIInterface.h:959`
```cpp
		*/
		/// @ingroup FABRIC_API
		/// @fn SetFabricPBRMaterialBaseColor(unsigned int _colorwayIndex, unsigned int _fabricIndex, unsigned int _materialFace, float _r, float _g, float _b, float _a)
		/// @brief Set a base color of PBR material in a fabric using given RGBA values.
		/// @param _colorwayIndex: the target colorway index
		/// @param _fabricIndex: the target fabric index in the object browser(Fabric index calculated assuming that the "Show All Colorways" option is turned off)
		/// @param _materialFace :“Front”, “Back”, “Side” 
		/// @param _r : To be set as red value
		/// @param _g : To be set as green value
		/// @param _b : To be set as blue value
		/// @param _a : To be set as alpha value
		/// @return if it succeeds, return true.
		virtual bool SetFabricPBRMaterialBaseColor(unsigned int _colorwayIndex, unsigned int _fabricIndex, unsigned int _materialFace, float _r, float _g, float _b, float _a) = 0;
```
`FabricAPIInterface.h:972`
```cpp
		*/
		/// @ingroup FABRIC_API
		/// @fn SetFabricPBRMaterialBaseColor(unsigned int fabricIndex, unsigned int materialFace, const std::string& _colorName)
		/// @brief Set a base color of PBR material in a fabric using given name of color.
		/// @param fabricIndex: the target fabric index in the object browser to import substance file onto
		/// @param materialFace :“Front”, “Back”, “Side” 
		/// @param _colorName: Name of color
		/// @return if it succeeds, return true.
		virtual bool SetFabricPBRMaterialBaseColor(unsigned int fabricIndex, unsigned int materialFace, const std::string& _colorName) = 0;
```
`FabricAPIInterface.h:986`
```cpp
		*/
		/// @ingroup FABRIC_API
		/// @fn SetFabricPBRMaterialBaseColor(unsigned int _colorwayIndex, unsigned int _fabricIndex, unsigned int _materialFace, const std::string& _colorName)
		/// @brief Set a base color of PBR material in a fabric using given name of color.
		/// @param _colorwayIndex: the target colorway index
		/// @param _fabricIndex: the target fabric index in the object browser(Fabric index calculated assuming that the "Show All Colorways" option is turned off)
		/// @param _materialFace :“Front”, “Back”, “Side” 
		/// @param _colorName: Name of color
		/// @return if it succeeds, return true.
		virtual bool SetFabricPBRMaterialBaseColor(unsigned int _colorwayIndex, unsigned int _fabricIndex, unsigned int _materialFace, const std::string& _colorName) = 0;
```

## SetGradingPairedAvatarFromFile

`PatternAPIInterface.h:1880`
```cpp
		/// @ingroup PATTERN_API
		/// @fn SetGradingPairedAvatarFromFile(unsigned int _gradingIndex, const std::string& _avtFilePath)
		/// @brief Load an avatar file (.avt) and pair it to a grading size — the exact API equivalent of the GUI 'Pair 3D Form' action. Unlike ImportAvatar (which replaces the scene avatar), the file is loaded additively, so calling this with different files per size builds a size set where each grading size has its own avatar; the paired avatar activates automatically on switching to its size. An existing pairing on the size is replaced.
		/// @param _gradingIndex: grading size index (0-based, order of GetGradingSizeNameList)
		/// @param _avtFilePath: path to the avatar file to load and pair
		/// @note In a GUI session the grading-related widgets (Object Browser - Grading, property panels) are not refreshed automatically by this API.
		/// @return true if the avatar was loaded and paired; false when no grading table exists, the index is out of range, or the file failed to load
		virtual bool SetGradingPairedAvatarFromFile(unsigned int _gradingIndex, const std::string& _avtFilePath) { return false; }
```

## SetGradingPairedAvatarSizing

`PatternAPIInterface.h:1871`
```cpp
		/// @ingroup PATTERN_API
		/// @fn SetGradingPairedAvatarSizing(unsigned int _gradingIndex, const std::string& _avsFilePath)
		/// @brief Load an Avatar Size (.avs) file and store it as the avatar sizing of a grading size — the API equivalent of the GUI 'Add Avatar Size' action in the Pair Avatar tab. Requires an avatar already paired to that size (SetGradingPairedAvatar) that is resizable; the .avs gender/avatar ID must match the paired avatar. When the target size is the currently selected grading size the sizing is applied to the avatar body immediately; otherwise it is stored and applied on the next switch to that size. 4.x-era .avs files (format v1/v2) are not supported.
		/// @param _gradingIndex: grading size index (0-based, order of GetGradingSizeNameList)
		/// @param _avsFilePath: path to the .avs file
		/// @note In a GUI session the grading-related widgets (Object Browser - Grading, property panels) are not refreshed automatically by this API.
		/// @return true if the sizing was loaded and stored; false when no grading table/paired avatar exists, the index is out of range, the avatar is not resizable, the file is missing/empty/unsupported, the gender/avatar ID does not match, or the table currently suppresses resizing-status updates (the sizing would be silently dropped)
		virtual bool SetGradingPairedAvatarSizing(unsigned int _gradingIndex, const std::string& _avsFilePath) { return false; }
```

## SetPatternPieceFabricIndex

`PatternAPIInterface.h:572`
```cpp
		virtual void SetPatternPieceFabricIndex(int _patternPieceIndex, int _fabricIndex) {}
```

## Simulate

`UtilityAPIInterface.h:737`
```cpp
		/// @ingroup UTILITY_API
		///	@fn Simulate(unsigned int _steps)
		/// @brief Simulate the garment in multi steps. All dynamics properties (time step, CG iteration count, ...) follow the current simulation properties
		/// @param _steps: how many steps(=frames) to simulate
		/// @return if it succeeds, return true.
		virtual bool Simulate(unsigned int _steps) { return false; }
```